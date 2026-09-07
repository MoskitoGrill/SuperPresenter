"""Recovery files never replace songs and never execute serialized input."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from superpresenter.domain.song import Song
from superpresenter.services.song_edit_session import SongEditSession
from superpresenter.services.song_recovery import SongRecovery
from superpresenter.services.song_repository import SongRepository


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.store = SongRecovery(self.directory / 'recovery')
        self.addCleanup(self.store.close)
        self.session = SongEditSession()
        self.original = self.directory / 'original.xml'
        self.session.reset(Song.from_texts('Saved', {'cs': {'v1': 'Text'}}))
        self.session.save(self.original)
        self.original_bytes = self.original.read_bytes()
        self.session.song.title = 'Unsaved'

    def test_recovery_roundtrip_keeps_clean_baseline_and_original(self):
        self.store.write(self.session)
        song, clean, path = self.store.read(self.store.path)
        self.assertEqual(song, self.session.song)
        self.assertEqual(clean, self.session.clean_song)
        self.assertEqual(Path(path), self.original)
        self.assertEqual(self.original.read_bytes(), self.original_bytes)
        recovered = SongEditSession()
        recovered.reset(clean, path)
        recovered.song = song
        self.assertTrue(recovered.dirty)

    def test_draft_and_xml_metadata_roundtrip(self):
        repository = SongRepository()
        self.session.reset(Song.from_texts())
        self.session.song = repository.loads('<slide name=""><info>x</info><variant name="cs">'
            '<section name="v1">\n  A\n\n</section><repetition name="default" main="1">v1</repetition>'
            '</variant></slide>')
        self.store.write(self.session)
        song, clean, path = self.store.read(self.store.path)
        self.assertIsNone(path)
        self.assertEqual(song.variants[0].sections[0].lines, ['', '  A', '', ''])
        self.assertEqual(song.repetition_locations, [(0, 1)])
        self.assertEqual(song.extra_elements[0][1].text, 'x')
        self.assertEqual(clean, Song.from_texts())

    def test_failed_recovery_write_preserves_previous_backup(self):
        self.store.write(self.session)
        previous = self.store.path.read_bytes()
        self.session.song.title = 'Later'
        with patch('superpresenter.services.song_recovery.os.replace', side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):
                self.store.write(self.session)
        self.assertEqual(self.store.path.read_bytes(), previous)
        self.assertEqual(self.original.read_bytes(), self.original_bytes)
        self.assertEqual(list(self.store.directory.glob('*.tmp')), [])

    def test_running_instance_is_not_offered_as_crashed(self):
        self.store.write(self.session)
        other = SongRecovery(self.store.directory)
        self.addCleanup(other.close)
        self.assertIsNone(other.claim(self.store.path))
        self.store.close()
        lease = other.claim(self.store.path)
        self.assertIsNotNone(lease)
        lease.close()

    def test_process_crash_releases_recovery_for_next_start(self):
        script = '''import os, sys
from superpresenter.domain.song import Song
from superpresenter.services.song_edit_session import SongEditSession
from superpresenter.services.song_recovery import SongRecovery
store = SongRecovery(sys.argv[1])
session = SongEditSession()
session.song = Song.from_texts('Crashed draft', {'cs': {'v1': 'Unsaved text'}})
store.write(session)
os._exit(0)
'''
        subprocess.run([sys.executable, '-B', '-c', script, str(self.store.directory)],
                       cwd=Path(__file__).resolve().parents[1], check=True)
        candidates = self.store.candidates()
        self.assertEqual(len(candidates), 1)
        lease = self.store.claim(candidates[0])
        self.assertIsNotNone(lease)
        try:
            self.assertEqual(self.store.read(candidates[0])[0].title, 'Crashed draft')
        finally:
            lease.close()

    def test_corrupt_record_remains_available_for_manual_repair(self):
        self.store.path.write_text('{broken', encoding='utf-8')
        with self.assertRaises(json.JSONDecodeError):
            self.store.read(self.store.path)
        self.assertEqual(self.store.path.read_text(encoding='utf-8'), '{broken')


if __name__ == '__main__':
    unittest.main()

import unittest
from copy import deepcopy
from pathlib import Path
import tempfile
from unittest.mock import patch
import xml.etree.ElementTree as ET

from superpresenter.domain.editable_song import EditableSong as Song
from superpresenter.services.song_editor_repository import SongEditorRepository as SongRepository
from superpresenter.services.song_edit_session import SongEditSession


class SongDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'song.xml'
        self.repo = SongRepository()
        self.song = Song('Píseň', {'čeština': {'v1': 'První\nDruhý'}, 'English': {'v1': 'First\nSecond'}}, {'default': 'v1', 'short': '(v1)*2'}, 'short')

    def test_roundtrip_languages_repetitions_and_main(self):
        self.repo.save(self.song, self.path)
        self.assertEqual(self.song, self.repo.load(self.path))

    def test_unknown_metadata_and_section_ids_are_preserved(self):
        self.path.write_text('<slide name="Test" custom="yes"><info>abc</info><variant name="cs" color="red"><section name="r" style="x">A &amp; B</section></variant><repetition name="only" custom="z">r</repetition></slide>', encoding='utf-8')
        song = self.repo.load(self.path)
        self.assertEqual(song.main_repetition, 'only')
        song.title = 'New'
        self.repo.save(song, self.path, overwrite=True)
        root = ET.parse(self.path).getroot()
        self.assertEqual(root.get('custom'), 'yes')
        self.assertEqual(root.find('info').text, 'abc')
        self.assertEqual(root.find('variant/section').get('style'), 'x')
        self.assertEqual(root.find('repetition').get('custom'), 'z')

    def test_collision_does_not_overwrite(self):
        self.repo.save(self.song, self.path)
        original = self.path.read_bytes()
        self.song.title = 'Other'
        with self.assertRaises(FileExistsError):
            self.repo.save(self.song, self.path)
        self.assertEqual(original, self.path.read_bytes())
        self.assertFalse(list(self.path.parent.glob('.song-*')))

    def test_atomic_failure_preserves_original_and_dirty_state(self):
        self.repo.save(self.song, self.path)
        original = self.path.read_bytes()
        session = SongEditSession(self.repo)
        session.load(self.path)
        session.song.title = 'Changed'
        with patch('superpresenter.services.song_editor_repository.os.replace', side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):
                session.save(self.path, overwrite=True)
        self.assertTrue(session.dirty)
        self.assertEqual(original, self.path.read_bytes())
        self.assertFalse(list(self.path.parent.glob('.song-*')))

    def test_dirty_all_model_fields_and_successful_save(self):
        session = SongEditSession(self.repo)
        session.reset(self.song)
        changes = [lambda s: setattr(s, 'title', 'Other'), lambda s: s.variants['čeština'].update(v1='Text'), lambda s: s.variants.update(de={'v1': 'Text'}), lambda s: s.variants['čeština'].update(v2='Text'), lambda s: s.repetitions.update(short='v1'), lambda s: setattr(s, 'main_repetition', 'default')]
        for change in changes:
            session.reset(self.song)
            self.assertFalse(session.dirty)
            change(session.song)
            self.assertTrue(session.dirty)
        session.save(self.path)
        self.assertFalse(session.dirty)

    def test_failed_load_keeps_session(self):
        session = SongEditSession(self.repo)
        session.reset(self.song)
        session.song.title = 'Unsaved'
        with self.assertRaises(FileNotFoundError):
            session.load(self.path)
        self.assertEqual(session.song.title, 'Unsaved')
        self.assertTrue(session.dirty)

    def test_copy_and_rename(self):
        session = SongEditSession(self.repo)
        session.reset(self.song)
        session.save(self.path)
        copy = self.path.with_name('copy.xml')
        session.save(copy)
        self.assertTrue(self.path.exists())
        renamed = self.path.with_name('renamed.xml')
        session.save(renamed, rename=True)
        self.assertFalse(copy.exists())
        self.assertTrue(renamed.exists())
        self.assertEqual(session.path, renamed)

    def test_failed_rename_deletion_keeps_both_copies_and_dirty_state(self):
        session = SongEditSession(self.repo)
        session.reset(self.song)
        session.save(self.path)
        session.song.title = 'New'
        target = self.path.with_name('new.xml')
        with patch.object(Path, 'unlink', side_effect=PermissionError('locked')):
            with self.assertRaisesRegex(OSError, 'Kopie byla uložena'):
                session.save(target, rename=True)
        self.assertTrue(self.path.exists())
        self.assertTrue(target.exists())
        self.assertTrue(session.dirty)
        self.assertEqual(session.path, self.path)

    def test_empty_title_and_unsafe_names(self):
        for title in ('', '   '):
            with self.assertRaises(ValueError):
                self.repo.save(Song(title), self.path)
        self.assertEqual(self.repo.filename('Příliš žluťoučký'), 'prilis_zlutoucky.xml')
        self.assertEqual(self.repo.filename('CON'), 'song_CON.xml'.lower())
        with self.assertRaises(ValueError):
            self.repo.filename('!!!')

    def test_section_removal_updates_all_languages_and_constructs(self):
        session = SongEditSession()
        session.reset(Song('Test', {'cs': {'v1': 'A', 'v2': 'B', 'v3': 'C'}, 'en': {'v1': 'a', 'v2': 'b', 'v3': 'c'}}, {'default': 'v1v2v3', 'other': '(v2.1)*3 v3.1:2'}, 'other'))
        session.remove_section('v2')
        self.assertEqual(session.song.variants['cs'], {'v1': 'A', 'v2': 'C'})
        self.assertEqual(session.song.variants['en'], {'v1': 'a', 'v2': 'c'})
        self.assertEqual(session.song.repetitions, {'default': 'v1v2', 'other': 'v2.1:2'})
        self.assertTrue(session.dirty)


if __name__ == '__main__':
    unittest.main()

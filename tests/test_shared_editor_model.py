"""Regression tests for one canonical model across editing and persistence."""
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from superpresenter.domain.song import Song
from superpresenter.services.song_edit_session import (
    SongEditSession, update_song_fields, validate_editor_fields,
)
from superpresenter.services.song_repository import SongRepository


class SharedEditorModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'song.xml'
        self.repo = SongRepository()

    def load(self, xml):
        self.path.write_text(xml, encoding='utf-8')
        return self.repo.load(self.path)

    def test_title_only_edit_preserves_raw_text_metadata_and_nested_repetition(self):
        original = self.load('<slide name="Old" author="abc"><info>keep me</info>'
            '<variant name="cs" custom="yes"><section name="v1">\n  A\n\nB  \n</section>tail'
            '<repetition name="band" main="yes" custom="z"> (v1.1)*2 </repetition></variant>'
            '<repetition name="default"> v1 </repetition><note>last</note></slide>')
        edited = update_song_fields(original, 'New', original.variant_texts,
                                    original.repetition_texts, original.main_repetition)
        self.assertIsInstance(edited, Song)
        self.assertEqual(edited.variants, original.variants)
        self.assertEqual(edited.repetitions, original.repetitions)
        self.repo.save(edited, self.path)
        root = ET.parse(self.path).getroot()
        self.assertEqual([child.tag for child in root], ['info', 'variant', 'repetition', 'note'])
        self.assertEqual(root.find('variant/section').text, '\n  A\n\nB  \n')
        self.assertEqual(root.find('variant/section').tail, 'tail')
        self.assertEqual(root.find('variant/repetition').text, ' (v1.1)*2 ')
        self.assertEqual(root.find('variant/repetition').get('custom'), 'z')
        self.assertEqual(root.find('note').text, 'last')
        self.assertEqual(self.repo.load(self.path), edited)

    def test_one_changed_section_preserves_other_raw_lines(self):
        original = self.load('<slide name="Test"><variant name="cs">'
            '<section name="v1">\n  A  \n</section><section name="v2">\n\tB\n\n</section>'
            '</variant></slide>')
        fields = original.variant_texts
        fields['cs']['v1'] = 'Changed\nline'
        edited = update_song_fields(original, original.title, fields, {}, '')
        self.assertEqual(edited.variants[0].sections[0].lines, ['Changed', 'line'])
        self.assertEqual(edited.variants[0].sections[1].lines, ['', '\tB', '', ''])
        self.assertEqual(original.variants[0].sections[0].lines, ['', '  A  ', ''])

    def test_nested_repetition_survives_renumber_and_save(self):
        song = self.load('<slide name="Test"><variant name="cs">'
            '<section name="v1">A</section><section name="v2" custom="keep">B</section>'
            '<repetition name="default">v1 v2</repetition></variant></slide>')
        session = SongEditSession()
        session.reset(song, self.path)
        session.remove_section('v1')
        session.save(self.path, overwrite=True)
        root = ET.parse(self.path).getroot()
        self.assertEqual(root.find('variant/section').get('name'), 'v1')
        self.assertEqual(root.find('variant/section').get('custom'), 'keep')
        self.assertEqual(root.find('variant/repetition').text, 'v1')
        self.assertFalse(session.dirty)

    def test_duplicate_nested_repetition_is_preserved_when_editing_root_field(self):
        song = self.load('<slide name="Test"><variant name="cs"><section name="v1">A</section>'
            '<repetition name="default">v1 v1</repetition></variant>'
            '<repetition name="default">v1</repetition></slide>')
        validate_editor_fields(song)
        unchanged = update_song_fields(song, song.title, song.variant_texts,
                                       song.repetition_texts, song.main_repetition)
        self.assertEqual(unchanged, song)
        changed = update_song_fields(song, song.title, song.variant_texts,
                                     {'default': '(v1)*3'}, song.main_repetition)
        self.repo.save(changed, self.path)
        root = ET.parse(self.path).getroot()
        self.assertEqual(root.find('variant/repetition').text, 'v1 v1')
        self.assertEqual(root.find('repetition').text, '(v1)*3')

    def test_duplicate_fields_fail_explicitly(self):
        song = self.load('<slide name="Test"><variant name="cs">'
            '<section name="v1">A</section><section name="v1">B</section></variant></slide>')
        with self.assertRaises(ValueError):
            validate_editor_fields(song)

    def test_saved_session_path_tracks_copy(self):
        session = SongEditSession()
        session.reset(Song.from_texts('Test', {'cs': {'v1': 'Text'}}))
        session.save(self.path)
        other = self.path.with_name('copy.xml')
        session.save(other)
        self.assertEqual(session.song.source_path, other)
        self.assertEqual(session.clean_song.source_path, other)
        self.assertIsInstance(session.repository, SongRepository)


if __name__ == '__main__':
    unittest.main()

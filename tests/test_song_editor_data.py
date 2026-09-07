import unittest
from copy import deepcopy
from pathlib import Path
import tempfile
from unittest.mock import patch
import xml.etree.ElementTree as ET

from superpresenter.domain.song import Song, SongSection, SongVariant
from superpresenter.services.song_repository import SongRepository, SongLoadError, SongSaveError
from superpresenter.services.song_edit_session import SongEditSession


class SongDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'song.xml'
        self.repo = SongRepository()
        self.song = Song.from_texts('Píseň', {'čeština': {'v1': 'První\nDruhý'}, 'English': {'v1': 'First\nSecond'}}, {'default': 'v1', 'short': '(v1)*2'}, 'short')

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
        with self.assertRaises(SongSaveError) as caught:
            self.repo.save(self.song, self.path, overwrite=False)
        self.assertIsInstance(caught.exception.cause, FileExistsError)
        self.assertEqual(original, self.path.read_bytes())
        self.assertFalse(list(self.path.parent.glob('.song-*')))

    def test_atomic_failure_preserves_original_and_dirty_state(self):
        self.repo.save(self.song, self.path)
        original = self.path.read_bytes()
        session = SongEditSession(self.repo)
        session.load(self.path)
        session.song.title = 'Changed'
        with patch('superpresenter.services.song_repository.os.replace', side_effect=PermissionError('locked')):
            with self.assertRaises(SongSaveError):
                session.save(self.path, overwrite=True)
        self.assertTrue(session.dirty)
        self.assertEqual(original, self.path.read_bytes())
        self.assertFalse(list(self.path.parent.glob('.song-*')))

    def test_dirty_all_model_fields_and_successful_save(self):
        session = SongEditSession(self.repo)
        session.reset(self.song)
        changes = [lambda s: setattr(s, 'title', 'Other'), lambda s: setattr(s.variants[0].sections[0], 'lines', ['Text']), lambda s: s.variants.append(SongVariant('de', [SongSection('v1', ['Text'])])), lambda s: s.variants[0].sections.append(SongSection('v2', ['Text'])), lambda s: setattr(s.repetitions[1], 'guide', 'v1'), lambda s: setattr(s.repetitions[0], 'is_main', True)]
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
        with self.assertRaises(SongLoadError):
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
                session = SongEditSession()
                session.reset(Song.from_texts(title))
                session.save(self.path)
        self.assertEqual(self.repo.filename('Příliš žluťoučký'), 'prilis_zlutoucky.xml')
        self.assertEqual(self.repo.filename('CON'), 'song_CON.xml'.lower())
        with self.assertRaises(ValueError):
            self.repo.filename('!!!')

    def test_section_removal_updates_all_languages_and_constructs(self):
        session = SongEditSession()
        session.reset(Song.from_texts('Test', {'cs': {'v1': 'A', 'v2': 'B', 'v3': 'C'}, 'en': {'v1': 'a', 'v2': 'b', 'v3': 'c'}}, {'default': 'v1v2v3', 'other': '(v2.1)*3 v3.1:2'}, 'other'))
        session.remove_section('v2')
        self.assertEqual(session.song.variant_texts['cs'], {'v1': 'A', 'v2': 'C'})
        self.assertEqual(session.song.variant_texts['en'], {'v1': 'a', 'v2': 'c'})
        self.assertEqual(session.song.repetition_texts, {'default': 'v1v2', 'other': 'v2.1:2'})
        self.assertTrue(session.dirty)


class RepetitionCoverageTests(unittest.TestCase):
    def test_missing_chorus_per_repetition_without_duplicate_languages(self):
        session = SongEditSession()
        session.reset(Song.from_texts('Test', {'cs': {'v1': 'A', 'v2': 'B', 'r1': 'C'},
                                   'en': {'v1': 'a', 'v2': 'b', 'r1': 'c'}},
                           {'band A': 'v1 v2 v1', 'band B': '(v1 v2 r1)*2'}, 'band A'))
        self.assertEqual(session.omitted_sections(), {'band A': ['r1']})
        self.assertFalse(session.dirty)

    def test_whole_ids_nested_groups_and_ranges(self):
        session = SongEditSession()
        session.reset(Song.from_texts('Test', {'cs': {'v1': 'A', 'v10': 'B', 'r': 'C'}},
                           {'default': '((v10.1:3)*2 r.1)*3'}))
        self.assertEqual(session.omitted_sections(), {'default': ['v1']})
        session.song.repetitions[0].guide += ' v1'
        self.assertEqual(session.omitted_sections(), {})

    def test_adjacent_section_references(self):
        session = SongEditSession()
        session.reset(Song.from_texts('Test', {'cs': {'v1': 'A', 'v2': 'B', 'r1': 'C'}},
                           {'default': 'v1v2(r1)*2'}))
        self.assertEqual(session.omitted_sections(), {})

    def test_pinned_references_count_as_used(self):
        session = SongEditSession()
        session.reset(Song.from_texts('Test', {'cs': {'v1': 'A', 'r1': 'B'}},
                                     {'default': '(@v1.1)*2 @r1.1'}))
        self.assertEqual(session.omitted_sections(), {})

    def test_remove_section_removes_pin_and_renumbers_surviving_pin(self):
        from superpresenter.services.construct_parser import parse_construct
        session = SongEditSession()
        session.reset(Song.from_texts('Test', {'cs': {'v1': 'A', 'v2': 'B'}},
                                     {'default': '(@v1.1)*2 @v2.1'}))
        session.remove_section('v1')
        self.assertEqual(session.song.guide, '@v1.1')
        parse_construct(session.song.guide, session.song.variant_texts['cs'])

    def test_empty_and_absent_repetition(self):
        session = SongEditSession()
        session.reset(Song.from_texts('Test', {'cs': {'v1': 'A'}}))
        self.assertEqual(session.omitted_sections(), {'default': ['v1']})
        session.song.repetitions = []
        self.assertEqual(list(session.omitted_sections().values()), [['v1']])
        session.reset(Song.from_texts())
        self.assertEqual(session.omitted_sections(), {})


if __name__ == '__main__':
    unittest.main()

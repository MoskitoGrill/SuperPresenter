"""Read-only corpus regression; serialization is tested in temporary files."""
from html import unescape
from pathlib import Path
import tempfile
import unittest

from super_presenter import WidgetSource, _LegacyWidgetSource
from superpresenter.services.song_editor_repository import SongEditorRepository as SongRepository


class ExistingSongsTests(unittest.TestCase):
    def test_existing_library_model_roundtrip_and_visible_lines(self):
        songs = list((Path(__file__).resolve().parents[1] / 'songs').rglob('*.xml'))
        self.assertTrue(songs, 'Song library not found')
        repo = SongRepository()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'roundtrip.xml'
            for path in songs:
                with self.subTest(song=path.name):
                    current = WidgetSource(str(path))
                    self.assertEqual(current.err, 0, current.load_warning)
                    repo.save(current.song, target, overwrite=True)
                    self.assertEqual(current.song, repo.load(target))
                    legacy = _LegacyWidgetSource(str(path))
                    variants = legacy.importVariants()
                    sections = legacy.importSections(variants)
                    before = legacy.importSlide(variants, sections)
                    after = current.importSlide(variants, sections)
                    for language in variants:
                        for section in sections:
                            if section in before.get(language, {}):
                                # XML entities now display their actual characters;
                                # surrounding whitespace is not visible song content.
                                expected = [unescape(line).strip() for line in before[language][section]['lines']]
                                actual = [line.strip() for line in after[language][section]['lines']]
                                self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()

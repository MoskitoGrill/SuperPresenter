"""Shared model regression tests; all writes stay in temporary directories."""
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from superpresenter.domain.song import Song, SongVariant, SongSection, SongRepetition
from superpresenter.services.song_repository import (
    SongRepository, SongLoadError, SongSaveError, SongValidationError,
)

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'píseň 日本語.xml'
        self.repo = SongRepository()

    def load(self, xml):
        self.path.write_text(xml, encoding='utf-8')
        return self.repo.load(self.path)

    def test_unicode_whitespace_order_and_main_roundtrip(self):
        song = self.load('''<slide name="Žalm &amp; mír" author="作者">
<variant name="čeština"><section name="v1">\n  Žluťoučký\n\n\třádek  \n</section><section name="r"/></variant>
<variant name="українська 日本語"><section name="b1">Слава 世界 😀&#160;\u2028konec</section></variant>
<repetition name="první"> v1\n r </repetition><repetition name="hlavní" main="1">(v1 r)*2</repetition>
</slide>''')
        self.assertEqual(song.variants[0].sections[0].lines, ['', '  Žluťoučký', '', '\třádek  ', ''])
        self.assertEqual(song.selected_repetition.name, 'hlavní')
        self.assertEqual(song.repetitions[0].guide, ' v1\n r ')
        self.assertEqual(song.attributes, {'author': '作者'})
        self.repo.save(song, self.path)
        self.assertEqual(self.repo.load(self.path), song)
        self.assertEqual(ET.parse(self.path).findall('repetition')[1].get('main'), '1')

    def test_constructed_model(self):
        song = Song('New', [SongVariant('English', [SongSection('v1', ['Text', '', '  end'])])],
                    [SongRepetition('default', 'v1')])
        self.repo.validate(song)
        self.repo.save(song, self.path)
        self.assertEqual(self.repo.load(self.path), song)

    def test_missing_and_multiple_main(self):
        song = self.load('<slide name=""><variant name="x"><section name="r"/></variant></slide>')
        self.assertIsNone(song.selected_repetition)
        self.repo.save(song, self.path)
        self.assertEqual(self.repo.load(self.path), song)
        song.repetitions = [SongRepetition('', '', True), SongRepetition('x', 'r', True)]
        self.repo.save(song, self.path)
        loaded = self.repo.load(self.path)
        self.assertEqual(loaded, song)
        self.assertIs(loaded.selected_repetition, loaded.repetitions[0])
        for rep in loaded.repetitions:
            rep.is_main = False
        self.assertIs(loaded.selected_repetition, loaded.repetitions[0])

    def test_errors_have_path_and_cause(self):
        for xml in ['<broken>', '<song/>', '<slide><unknown/></slide>',
                    '<slide><variant><section><b>text</b></section></variant></slide>',
                    '<!DOCTYPE slide [<!ENTITY x "text">]><slide name="&x;"/>']:
            with self.subTest(xml=xml), self.assertRaises(SongLoadError) as caught:
                self.load(xml)
            self.assertEqual(caught.exception.path, self.path)
            self.assertIsNotNone(caught.exception.__cause__)
            self.assertIn(str(self.path), str(caught.exception))
        with self.assertRaises(SongLoadError):
            self.repo.load(self.path.parent / 'missing.xml')

    def test_failed_save_does_not_change_target(self):
        self.path.write_text('original', encoding='utf-8')
        song = Song('bad\x00title', source_path=self.path)
        with self.assertRaises(SongValidationError):
            self.repo.validate(song)
        with self.assertRaises(SongSaveError) as caught:
            self.repo.save(song, self.path)
        self.assertEqual(caught.exception.path, self.path)
        self.assertEqual(self.path.read_text(encoding='utf-8'), 'original')
        with self.assertRaises(SongSaveError):
            self.repo.save(Song('ok'), self.path.parent / 'missing' / 'song.xml')

    def test_all_existing_songs_roundtrip(self):
        paths = list((ROOT / 'songs').rglob('*.xml'))
        self.assertGreater(len(paths), 0)
        for path in paths:
            with self.subTest(path=path):
                before = path.read_bytes()
                song = self.repo.load(path)
                self.repo.save(song, self.path)
                self.assertEqual(self.repo.load(self.path), song)
                self.assertEqual(path.read_bytes(), before)
                def content(element):
                    attrs = dict(element.attrib)
                    attrs.setdefault('name', '')
                    return (element.tag, attrs, element.text or '', element.tail or '',
                            [content(child) for child in element])
                self.assertEqual(content(ET.fromstring(before)),
                                 content(ET.parse(self.path).getroot()))

    def test_nested_repetition_and_tail_survive(self):
        song = self.load('<slide name="x"><variant name="a"><section name="v1">a</section>.'
                         '<repetition main="1">v1</repetition></variant>'
                         '<repetition name="other">v1 v1</repetition></slide>')
        self.assertEqual(len(song.repetitions), 2)
        self.repo.save(song, self.path)
        root = ET.parse(self.path).getroot()
        self.assertEqual(root.find('variant/section').tail, '.')
        self.assertEqual(root.find('variant/repetition').get('main'), '1')
        self.assertEqual(self.repo.load(self.path), song)

    def test_xml_carriage_return_reference(self):
        song = self.load('<slide name="x"><variant name="a"><section name="v1">a&#13;b</section>'
                         '</variant><repetition>v1&#13;v1</repetition></slide>')
        self.repo.save(song, self.path)
        self.assertEqual(self.repo.load(self.path), song)

    def test_failed_replace_preserves_existing_file(self):
        from unittest.mock import patch
        self.path.write_text('original', encoding='utf-8')
        with patch('superpresenter.services.song_repository.os.replace', side_effect=OSError('locked')):
            with self.assertRaises(SongSaveError):
                self.repo.save(Song('new'), self.path)
        self.assertEqual(self.path.read_text(encoding='utf-8'), 'original')
        self.assertEqual(list(self.path.parent.glob('*.tmp')), [])

    def test_widget_opt_in_does_not_change_legacy_results(self):
        from super_presenter import WidgetSource
        song = self.load('<slide name="Test">\n<variant name="English">\n<section name="v1">\n  Text\n\n</section>\n</variant>\n<repetition name="default" main="1">\nv1\n</repetition>\n</slide>')
        widget = WidgetSource(str(self.path))
        before = (widget.validate(), widget.importSlide(['English'], ['v1']),
                  widget.importRepetitions(), widget.sourceText)
        self.assertEqual(widget.loadSong(), song)
        after = (widget.validate(), widget.importSlide(['English'], ['v1']),
                 widget.importRepetitions(), widget.sourceText)
        self.assertEqual(after, before)
        self.assertEqual(before[1]['English']['v1']['lines'], ['Text'])
        self.load('<slide name="Changed"/>')
        self.assertEqual(widget.loadSong().title, 'Changed')


if __name__ == '__main__':
    unittest.main()

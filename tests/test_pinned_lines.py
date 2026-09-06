import tempfile
from pathlib import Path
import unittest

from superpresenter.domain.song import SongSection, SongVariant
from superpresenter.services.construct_parser import parse_construct, ConstructError, RepeatGroup
from superpresenter.services.stationary_pages import resolve_sections, generate_pages
from superpresenter.services.song_repository import SongRepository
from scripts.validate_songs import validate_song


class PinnedLinesTests(unittest.TestCase):
    def variant(self, following=6):
        return SongVariant('test', [SongSection('v1', ['a', 'b', 'c', 'd']),
                                    SongSection('v2', [str(i) for i in range(following)])])

    def plan(self, guide, following=6):
        variant = self.variant(following)
        sections = list(resolve_sections(parse_construct(guide, ['v1', 'v2']), variant))
        plan = generate_pages(sections)
        expected = tuple(row for section in sections for row in section.lines)
        self.assertEqual(expected, tuple(row for page in plan.hall_pages for row in page.lines))
        self.assertEqual(expected, tuple(row for page in plan.stream_pages for row in page.lines))
        self.assertTrue(all(len(page.lines) <= 8 for page in plan.hall_pages))
        self.assertTrue(all(len(page.lines) <= 4 for page in plan.stream_pages))
        self.assertEqual(len(plan.cues), len({cue.navigation_id for cue in plan.cues}))
        self.assertEqual(plan, generate_pages(sections))
        backwards = [plan.cues[i] for i in range(len(plan.cues) - 1, -1, -1)]
        self.assertEqual(list(plan.cues), list(reversed(backwards)))
        for cue in backwards:
            self.assertIs(cue.hall_page, plan.hall_pages[cue.stream_page.hall_page_index])
            self.assertEqual(cue.stream_page.lines, cue.hall_page.lines[
                cue.stream_page.hall_start:cue.stream_page.hall_start + len(cue.stream_page.lines)])
        return plan

    def test_one_and_two_pins(self):
        for guide, count in [('v1 @v1.4 v2', 7), ('v1 @v1.3:4 v2', 8)]:
            with self.subTest(guide=guide):
                plan = self.plan(guide)
                self.assertEqual([len(p.lines) for p in plan.hall_pages], [4, count])
                self.assertTrue(plan.hall_pages[1].lines[0].pinned)
                self.assertTrue(plan.hall_pages[1].lines[0].repeated)
                self.assertEqual(plan.hall_pages[1].lines[0].section_id, 'v1')

    def test_no_room(self):
        self.assertEqual([len(p.lines) for p in self.plan('v1 @v1.3:4 v2', 7).hall_pages], [4, 2, 7])

    def test_long_section(self):
        self.assertEqual([len(p.lines) for p in self.plan('v1 @v1.3:4 v2', 10).hall_pages], [4, 2, 8, 2])

    def test_end_and_adjacent_pins(self):
        self.assertEqual([len(p.lines) for p in self.plan('v1 @v1.4').hall_pages], [4, 1])
        self.assertEqual([len(p.lines) for p in self.plan('@v1.3 @v1.4 v2').hall_pages], [8])

    def test_groups_and_unmarked_selection(self):
        self.assertEqual([len(p.lines) for p in self.plan('(v1 @v1.4 v2)*2').hall_pages], [4, 7, 4, 7])
        self.assertEqual([len(p.lines) for p in self.plan('v1 v1.4 v2').hall_pages], [4, 1, 6])
        self.plan('((@v1.4)*2 v2)*2')
        self.assertEqual(self.plan('(@v1.4)*0').hall_pages, ())

    def test_invalid_markers(self):
        for guide in ['@v1', '@v1.0', '@v1.1:3', '@(v1.1)', '@@v1.1', '@v1.5']:
            with self.subTest(guide=guide), self.assertRaises(ConstructError):
                list(resolve_sections(parse_construct(guide, ['v1']), self.variant()))

    def test_legacy_translation_and_whitespace(self):
        marked = parse_construct('v1 (@ v1 . 3 : 4) * 2', ['v1'])
        plain = parse_construct('v1 (v1.3:4)*2', ['v1'])
        self.assertEqual(marked.to_legacy(), plain.to_legacy())
        self.assertIsInstance(marked.instructions[1], RepeatGroup)
        self.assertTrue(marked.instructions[1].children[0].pinned)

    def test_xml_roundtrip_and_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'song.xml'
            xml = ('<slide name="test"><variant name="test"><section name="v1">\n'
                   '  a\n  b\n</section></variant><repetition>v1 @v1.2</repetition></slide>')
            path.write_text(xml, encoding='utf-8')
            repository = SongRepository()
            song = repository.load(path)
            target = Path(tmp) / 'copy.xml'
            repository.save(song, target)
            self.assertEqual(song, repository.load(target))
            self.assertEqual(validate_song(path), [])
            sections = list(resolve_sections(parse_construct(song.repetitions[0].guide, ['v1']), song.variants[0]))
            self.assertEqual(sections[-1].lines[0].text, 'b')
            for guide in ['@v1', '@v1.0', '@v1.1:3', '@v1.3', '@missing.1', '(@v1.3)*0']:
                path.write_text(xml.replace('v1 @v1.2', guide), encoding='utf-8')
                self.assertIn('repetition_pin', [i.code for i in validate_song(path)])
            # A missing row in just one language must also fail.
            path.write_text(xml.replace('</variant>', '</variant><variant name="other"><section name="v1">a</section></variant>'), encoding='utf-8')
            self.assertIn('repetition_pin', [i.code for i in validate_song(path)])


if __name__ == '__main__':
    unittest.main()

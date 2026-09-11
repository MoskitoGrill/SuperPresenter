"""Pure parser tests and a frozen legacy oracle; no Tk window is needed."""
from pathlib import Path
from types import SimpleNamespace
from copy import copy
import importlib.util
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

from superpresenter.services.construct_parser import (
    parse_construct, SectionStep, RepeatGroup, ConstructError,
    ParenthesisError, UnknownSectionError, InvalidRangeError,
    ExpectedNumberError, EmptyConstructError,
)

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'legacy_construct', ROOT / 'tests/fixtures/legacy_construct_parser.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def old_parse(text, sections):
    source = SimpleNamespace(repetitions=text, legalSections=lambda: sections)
    error = legacy.readInstructions(source)
    return source, error


class ConstructParserTests(unittest.TestCase):
    def test_optional_spaces_preserve_section_order(self):
        compact = 'v1 v2 (r2.3)*3 b1.1:2 v1'
        expected = parse_construct(compact, ['v1', 'v2', 'r2', 'b1']).to_legacy()
        for text in (' v1   v2 ( r2 . 3 ) * 3 b1 . 1 : 2   v1 ',
                     'v1 v2(r2 .3)*3 b1. 1: 2 v1'):
            with self.subTest(text=text):
                result = parse_construct(text, ['v1', 'v2', 'r2', 'b1'])
                self.assertEqual(result.to_legacy(), expected)
                self.assertEqual([s.section for s in result.instructions[:2]], ['v1', 'v2'])

    def test_spaces_do_not_merge_identifiers_or_numbers(self):
        for text in ('v 1', '(v1)*1 2', 'v1.1 2'):
            with self.subTest(text=text), self.assertRaises(UnknownSectionError):
                parse_construct(text, ['v1'])

    def test_spaced_range_error_positions(self):
        for text, error, position in [('v1 . x', ExpectedNumberError, 5),
                                     ('v1 . 1 : ', ExpectedNumberError, 9),
                                     ('v1 . 3 : 2', InvalidRangeError, 9)]:
            with self.subTest(text=text), self.assertRaises(error) as raised:
                parse_construct(text, ['v1'])
            self.assertEqual(raised.exception.position, position)

    def test_spaces_around_group_multiplier(self):
        for text in ('(v1)*3', '(v1) *3', '(v1)* 3', '(v1) * 3',
                     '(v1)   *   3'):
            with self.subTest(text=text):
                self.assertEqual(parse_construct(text, ['v1']).to_legacy(),
                                 parse_construct('(v1)*3', ['v1']).to_legacy())
        text = '((v1) * 3 r2.3) * 2 b1'
        self.assertEqual(parse_construct(text, ['v1', 'r2', 'b1']).to_legacy(),
                         parse_construct('((v1)*3 r2.3)*2 b1', ['v1', 'r2', 'b1']).to_legacy())

    def test_refrain_line_repeated_three_times(self):
        from super_presenter import WidgetSource
        source = WidgetSource.__new__(WidgetSource)
        source.repetitions = '(r2.3) * 3'
        source.legalSections = lambda: ['r2']
        source.variants = ['cs']
        result = source.readInstructions()
        self.assertEqual(result.instructions[0].repeat, 3)
        self.assertEqual(result.instructions[0].children[0], SectionStep('r2', 1, 3))
        slide = {'cs': {'r2': {'lines': ['první', 'druhý', 'třetí', 'čtvrtý']}}}
        self.assertEqual(source.longText(slide)[0], [['třetí'] * 3])
        self.assertEqual(source.shortText(slide, '', ''), ([0, 0, 0], [['třetí×3']]))

    def test_spaced_multiplier_error_positions(self):
        for text in ('(v1) * ', '(v1) * x', '(v1) * -3'):
            with self.subTest(text=text):
                with self.assertRaises(ExpectedNumberError) as raised:
                    parse_construct(text, ['v1'])
                self.assertEqual(raised.exception.position, 7)

    def test_simple_order(self):
        result = parse_construct('v1 r1 v2 r1', ['v1', 'v2', 'r1'])
        self.assertEqual([s.section for s in result.instructions], ['v1', 'r1', 'v2', 'r1'])
        self.assertEqual(result.instructions[2].position, 6)

    def test_groups_and_nesting(self):
        result = parse_construct('((v1 v2)*3 r1)', ['v1', 'v2', 'r1'])
        outer = result.instructions[0]
        self.assertIsInstance(outer, RepeatGroup)
        self.assertEqual(outer.repeat, 2)
        self.assertTrue(outer.reuse_lines)
        self.assertEqual(outer.children[0].repeat, 3)
        self.assertEqual(outer.children[0].children[1].section, 'v2')

    def test_line_selection(self):
        result = parse_construct('v1.2:4 r1.9', ['v1', 'r1'])
        self.assertEqual(result.instructions, (SectionStep('v1', 0, 2, 4), SectionStep('r1', 7, 9)))

    def test_single_line_before_next_section(self):
        result = parse_construct('v1.2 r1.3 v1', ['v1', 'r1'])
        self.assertEqual([s.start_line for s in result.instructions], [2, 3, None])

    def test_large_repeat_is_not_expanded(self):
        result = parse_construct('(v1)*1000000000000', ['v1'])
        self.assertEqual(len(result.instructions), 1)
        self.assertEqual(result.instructions[0].repeat, 1000000000000)
        self.assertLess(len(result.to_legacy()[0]), 10)

    def test_deep_nesting(self):
        result = parse_construct('(' * 1500 + 'v1' + ')' * 1500, ['v1'])
        program, used = result.to_legacy()
        self.assertEqual(used, ['v1'])
        self.assertEqual(program.count('mult'), 1500)

    def test_pure_import_without_ui_dependencies(self):
        code = """
import sys
for name in ('tkinter', 'screeninfo', 'PIL', 'super_presenter'):
    sys.modules[name] = None
from superpresenter.services.construct_parser import parse_construct
assert parse_construct('(v1)*2', ['v1']).instructions[0].repeat == 2
"""
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_adapter_error_keeps_previous_state(self):
        from super_presenter import WidgetSource
        source = WidgetSource.__new__(WidgetSource)
        source.instructions = [0, 'all', 1, 'conn']
        source.usedSections = ['v1']
        source.legalSections = lambda: ['v1']
        source.repetitions = '(v1'
        with self.assertRaises(ParenthesisError):
            source.readInstructions()
        self.assertEqual(source.instructions, [0, 'all', 1, 'conn'])
        self.assertEqual(source.usedSections, ['v1'])

    def test_legacy_edge_cases(self):
        for text in ('v1.0', 'v1.0:2', '(v1)*0', '(v1)*1', '()', '(())',
                     '(v1)v1', 'v1.1:2v1', ' (v1)  ', '(v1)*0003'):
            with self.subTest(text=text):
                old, error = old_parse(text, ['v1'])
                self.assertEqual(error, [0])
                self.assertEqual(parse_construct(text, ['v1']).to_legacy(),
                                 (old.instructions, old.usedSections))

    def test_legacy_identifiers(self):
        names = ['r', 'b', 'r0', 'v1a', 'v1b', 'verse-one', 'česká']
        self.assertEqual([s.section for s in parse_construct(' '.join(names), names).instructions], names)

    def test_errors_and_original_positions(self):
        cases = [('', EmptyConstructError, 0), ('   ', EmptyConstructError, 0),
                 ('(v1', ParenthesisError, 0), ('v1)', ParenthesisError, 2),
                 ('((v1)', ParenthesisError, 0), ('v1 r2', UnknownSectionError, 3),
                 ('v1.', ExpectedNumberError, 3), ('v1.x', ExpectedNumberError, 3),
                 ('v1.1:', ExpectedNumberError, 5), ('(v1)*', ExpectedNumberError, 5),
                 ('(v1)*-1', ExpectedNumberError, 5), ('v1.3:2', InvalidRangeError, 5),
                 ('v1.2:2', InvalidRangeError, 5), ('v1*2', UnknownSectionError, 0),
                 ('v1\nv1', UnknownSectionError, 0), ('v1\tv1', UnknownSectionError, 0)]
        for text, error, position in cases:
            with self.subTest(text=text):
                with self.assertRaises(error) as raised:
                    parse_construct(text, ['v1'])
                self.assertEqual(raised.exception.position, position)
                self.assertIn(str(position), str(raised.exception))

    def test_stack_program_and_renderers(self):
        from super_presenter import WidgetSource
        sections = ['v1', 'v2', 'r1']
        slide = {'cs': {s: {'lines': [s + str(i) for i in range(1, 5)]} for s in sections}}
        for text in ('v1 r1 v2 r1', '(v1 v2)*3', '((v1) (r1)) (v1)',
                     'v1.1:3 (r1.2:4)*3 v2.2', '(v1)*1'):
            with self.subTest(text=text):
                old, error = old_parse(text, sections)
                self.assertEqual(error, [0])
                new = WidgetSource.__new__(WidgetSource)
                new.repetitions = text
                new.legalSections = lambda: sections
                new.readInstructions()
                self.assertEqual(new.instructions, old.instructions)
                self.assertEqual(new.usedSections, old.usedSections)
                for source in (new, old):
                    source.variants = ['cs']
                for method, args in ((WidgetSource.longText, (slide,)),
                                     (WidgetSource.shortText, (slide, '|:', ':|')),
                                     (WidgetSource._build_group_lengths, (slide,)),
                                     (WidgetSource._flatten_group_sequence, (slide,))):
                    self.assertEqual(method(new, *args), method(old, *args))

    def test_database_compatibility(self):
        checked = accepted = 0
        differences = []
        for path in sorted((ROOT / 'songs').rglob('*.xml')):
            root = ET.parse(path).getroot()
            sections = list(dict.fromkeys(s.get('name', '') for s in root.iter('section')))
            for rep in root.iter('repetition'):
                # importRepetitions joins nonempty physical lines with spaces.
                text = ' '.join(line.strip() for line in (rep.text or '').splitlines() if line.strip())
                checked += 1
                old, error = old_parse(text, sections)
                try:
                    new = parse_construct(text, sections)
                except ConstructError:
                    self.assertNotEqual(error, [0], (path, text))
                else:
                    if error != [0]:
                        differences.append((path.name, text, error))
                    else:
                        accepted += 1
                        self.assertEqual(new.to_legacy(), (old.instructions, old.usedSections), (path, text))
        self.assertGreater(checked, 800)
        self.assertGreater(accepted, 800)
        self.assertEqual(differences, [])

    def test_real_song_rendering_and_short2_navigation(self):
        from super_presenter import WidgetSource
        for filename in ('dobrorec_duse_ma_hospodinu.xml', 'at_pozehnan_je_buh.xml',
                         'hoden_je_beranek.xml', 'muj_svet.xml',
                         'at_srdce_me_tebe_vida.xml', 'vzyvam_jmeno_jezis.xml'):
            source = WidgetSource(str(ROOT / 'songs' / filename))
            root = ET.parse(ROOT / 'songs' / filename).getroot()
            for repetition in root.iter('repetition'):
                guide = ' '.join((repetition.text or '').split())
                with self.subTest(filename=filename, guide=guide):
                    source.variants = source.importVariants()
                    source.repetitions = guide
                    old = copy(source)
                    self.assertEqual(legacy.readInstructions(old), [0])
                    source.readInstructions()
                    slide = source.importSlide(source.variants, source.usedSections)
                    self.assertEqual(source.longText(slide), old.longText(slide))
                    self.assertEqual(source.shortText(slide, '|:', ':|'), old.shortText(slide, '|:', ':|'))
                    # short2 pairing operates on one selected language.
                    for instance in (source, old):
                        instance.variants = source.variants[:1]
                    styles = [{'type': kind, 'repeat_start': '|:', 'repeat_end': ':|'}
                              for kind in ('long', 'short', 'short2')]
                    try:
                        expected = old.constructLines(styles)
                    except IndexError as exc:
                        # Existing short2 repeats can exceed the stored lines.
                        # Extraction must preserve, not silently change navigation.
                        with self.assertRaises(IndexError) as raised:
                            source.constructLines(styles)
                        self.assertEqual(str(raised.exception), str(exc))
                    else:
                        self.assertEqual(source.constructLines(styles), expected)
                        self.assertEqual(source.lines, old.lines)

    def test_database_through_existing_import_and_variant_selection(self):
        from super_presenter import WidgetSource
        checked = 0
        for path in sorted((ROOT / 'songs').rglob('*.xml')):
            source = WidgetSource(str(path))
            variants = source.importVariants()
            for selection in [[v] for v in variants] + [variants]:
                if not selection:
                    continue
                source.variants = selection
                sections = source.legalSections()
                for repetition in source.importRepetitions().values():
                    text = repetition['guide']
                    if not text:
                        continue
                    checked += 1
                    with self.subTest(path=path, selection=selection, text=text):
                        old, error = old_parse(text, sections)
                        source.repetitions = text
                        if error != [0]:
                            with self.assertRaises(ConstructError):
                                source.readInstructions()
                        else:
                            source.readInstructions()
                            self.assertEqual(source.instructions, old.instructions)
                            self.assertEqual(source.usedSections, old.usedSections)
        self.assertGreater(checked, 1600)


if __name__ == '__main__':
    unittest.main()

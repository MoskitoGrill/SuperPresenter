import subprocess
import sys
import unittest

from superpresenter.services.stationary_pages import (
    LogicalSection, SourceLine, SourceRange, generate_pages, format_timeline,
)


def section(count, name='v1', occurrence=None):
    return LogicalSection(occurrence or name, tuple(
        SourceLine(f'row {i}', name, i) for i in range(count)))


class StationaryPagesTests(unittest.TestCase):
    def assert_synchronized(self, plan, inputs):
        expected = tuple(line for sec in inputs for line in sec.lines)
        self.assertEqual(tuple(line for p in plan.hall_pages for line in p.lines), expected)
        self.assertEqual(tuple(line for p in plan.stream_pages for line in p.lines), expected)
        self.assertEqual(len(plan.cues), len(plan.stream_pages))
        self.assertEqual(len({c.navigation_id for c in plan.cues}), len(plan.cues))
        for hall in plan.hall_pages:
            self.assertTrue(1 <= len(hall.lines) <= 8)
        for i, cue in enumerate(plan.cues):
            stream = cue.stream_page
            self.assertEqual(cue.step_index, i)
            self.assertIs(stream, plan.stream_pages[i])
            self.assertIs(cue.hall_page, plan.hall_pages[stream.hall_page_index])
            self.assertTrue(1 <= len(stream.lines) <= 4)
            self.assertEqual(stream.lines, cue.hall_page.lines[
                stream.hall_start:stream.hall_start + len(stream.lines)])
            expanded = [(r.section_id, n, r.pinned, r.repeated)
                        for r in cue.source_ranges for n in range(r.start, r.stop)]
            self.assertEqual(expanded, [(r.section_id, r.line_index, r.pinned, r.repeated)
                                        for r in stream.lines])

    def test_required_lengths(self):
        for count, halls, streams in [(4, [4], [4]), (6, [6], [4, 2]),
                                     (8, [8], [4, 4]), (10, [8, 2], [4, 4, 2]),
                                     (16, [8, 8], [4, 4, 4, 4])]:
            with self.subTest(count=count):
                inputs = [section(count)]
                plan = generate_pages(inputs)
                self.assertEqual([len(p.lines) for p in plan.hall_pages], halls)
                self.assertEqual([len(p.lines) for p in plan.stream_pages], streams)
                self.assert_synchronized(plan, inputs)
                if count > 4:
                    self.assertIs(plan.cues[0].hall_page, plan.cues[1].hall_page)
                self.assertEqual(plan, generate_pages(inputs))

    def test_two_short_sections_and_verse_chorus(self):
        for second in ('v2', 'r1'):
            inputs = [section(2), section(3, second)]
            plan = generate_pages(inputs)
            self.assertEqual([len(p.lines) for p in plan.hall_pages], [2, 3])
            self.assertEqual([c.occurrence_id for c in plan.cues], ['v1', second])
            self.assert_synchronized(plan, inputs)

    def test_two_explicit_pinned_rows_with_next_section(self):
        verse = section(6)
        copies = tuple(SourceLine(r.text, r.section_id, r.line_index,
                                  pinned=True, repeated=True) for r in verse.lines[-2:])
        chorus = LogicalSection('r1', copies + section(6, 'r1').lines)
        plan = generate_pages([verse, chorus])
        self.assertEqual([len(p.lines) for p in plan.hall_pages], [6, 8])
        self.assertEqual(plan.cues[2].source_ranges, (
            SourceRange('v1', 4, 6, True, True), SourceRange('r1', 0, 2, False, False)))
        self.assertIs(plan.cues[2].hall_page, plan.cues[3].hall_page)
        self.assert_synchronized(plan, [verse, chorus])

    def test_identical_text_does_not_infer_flags(self):
        rows = (SourceLine('same', 'v1', 0), SourceLine('same', 'v1', 1))
        plan = generate_pages([LogicalSection('v1', rows)])
        self.assertFalse(any(r.pinned or r.repeated for r in plan.hall_pages[0].lines))

    def test_empty_song_and_section(self):
        for inputs in ([], [section(0)]):
            plan = generate_pages(inputs)
            self.assertEqual((plan.hall_pages, plan.stream_pages, plan.cues), ((), (), ()))
            self.assertEqual(format_timeline(plan), '')

    def test_many_lengths_and_boundaries(self):
        for count in range(65):
            inputs = [section(count), section(7, 'r1')]
            self.assert_synchronized(generate_pages(inputs), inputs)

    def test_stable_ids_and_repeated_occurrences(self):
        inputs = [section(10, occurrence='v1/first'), section(10, occurrence='v1/second')]
        original = generate_pages(inputs)
        prefixed = generate_pages([section(3, 'intro')] + inputs)
        self.assertEqual([c.navigation_id for c in original.cues],
                         [c.navigation_id for c in prefixed.cues[1:]])
        self.assert_synchronized(original, inputs)
        with self.assertRaises(ValueError):
            generate_pages([section(1), section(1)])

    def test_invalid_rows_and_blank_row_capacity(self):
        for text in ('a\nb', 'a\rb'):
            with self.assertRaises(ValueError):
                SourceLine(text, 'v1', 0)
        with self.assertRaises(ValueError):
            SourceLine('a', 'v1', -1)
        with self.assertRaises(ValueError):
            LogicalSection('', ())
        rows = tuple(SourceLine('', 'v1', i) for i in range(9))
        self.assertEqual([len(p.lines) for p in generate_pages([
            LogicalSection('v1', rows)]).hall_pages], [8, 1])

    def test_diagnostics_and_import_without_gui(self):
        timeline = format_timeline(generate_pages([section(10)]))
        self.assertEqual(timeline.splitlines(), [
            'cue 1 -> hall 1 / stream 1.1 [v1:row:0]',
            'cue 2 -> hall 1 / stream 1.2 [v1:row:4]',
            'cue 3 -> hall 2 / stream 2.1 [v1:row:8]'])
        result = subprocess.run([sys.executable, '-B', '-c',
            'import superpresenter.services.stationary_pages; import sys; '
            'assert "tkinter" not in sys.modules; '
            'assert "super_presenter" not in sys.modules'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import patch

from superpresenter.domain.song import Song
from superpresenter.services.construct_parser import (
    parse_construct, ConstructLimitError, MAX_INPUT_LENGTH,
)
from superpresenter.services.stationary_navigation import build_plan
from superpresenter.services.presentation_session import WidgetSource
import test_release_stability as release


class BudgetTests(unittest.TestCase):
    def test_parser_boundaries_and_intermediate_work(self):
        for text in ('(v1)*4096', 'v1.1:4096', '(()*1)*4096',
                     '(' * 32 + 'v1' + ')*1' * 32,
                     'v1' + ' ' * (MAX_INPUT_LENGTH - 2)):
            parse_construct(text, ['v1'])
        for text in ('(v1)*4097', 'v1.1:4097', '((v1)*65)*64',
                     '((v1)*4097)*0', '(()*4097)*0',
                     '(v1)*4096 v1', '(' * 33 + 'v1' + ')*1' * 33,
                     'v1' + ' ' * (MAX_INPUT_LENGTH - 1)):
            with self.subTest(text=text[:80]), self.assertRaises(ConstructLimitError):
                parse_construct(text, ['v1'])

    def test_both_builders_bound_rows_and_languages_before_expansion(self):
        song = Song.from_texts('Test', {'cs': {'v1': 'a\nb'},
                                       'en': {'v1': 'c\nd'}}, {'default': 'v1'})
        source = WidgetSource('unused.xml', song=song)
        for languages, repeat in ((['cs'], 2048), (['cs', 'en'], 1024)):
            source.variants = languages
            for multiplier, accepted in ((repeat, True), (repeat + 1, False)):
                guide = f'(v1)*{multiplier}'
                source.repetitions = guide
                source.readInstructions()
                if accepted:
                    source.constructLines([{'type': 'long'}, {'type': 'short'}, {'type': 'short2'}])
                    plan, _ = build_plan(song, languages, guide)
                    self.assertEqual(sum(len(p.lines) for p in plan.hall_pages), 4096)
                else:
                    with patch.object(source, '_build_group_lengths', side_effect=AssertionError('expanded')):
                        with self.assertRaises(ConstructLimitError):
                            source.constructLines([{'type': 'long'}])
                    with patch('superpresenter.services.stationary_navigation.resolve_sections',
                               side_effect=AssertionError('expanded')):
                        with self.assertRaises(ConstructLimitError):
                            build_plan(song, languages, guide)


class RecoveryTests(unittest.TestCase):
    setUp = release.ReleaseTests.setUp
    destroy = release.ReleaseTests.destroy
    configure_outputs = release.ReleaseTests.configure_outputs

    def test_reject_then_restart_in_both_modes(self):
        gui = self.gui
        self.enterContext(patch.object(gui, '_prepare_song_transition', return_value=True))
        self.enterContext(patch.object(gui, 'saveRepetitions'))
        for styles in ([2], [0, 1]):
            self.configure_outputs(styles)
            for guide in ('(v1)*4097', '(v1)*410'):
                for source in gui.sources:
                    source.repetitions = guide
                gui.runButtFun()
                self.assertFalse(gui.runState)
                self.assertIsNone(getattr(gui, 'stationary_navigation', None))
                self.assertEqual(str(gui.openProjs.cget('state')), 'normal')
                self.assertIsNone(getattr(gui, '_editing_states', None))
                self.assertTrue(all(not hasattr(p, 'win') for p in gui.projectors))
                self.assertIn('limit', self.error.call_args.args[1])
                for source in gui.sources:
                    source.repetitions = 'v1 @v1.1'
                gui.runButtFun()
                self.assertTrue(gui.runState)
                gui.runButtFun()

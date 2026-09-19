"""Navigation, GUI wiring and canvas calls without a real Tk window."""
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, MagicMock

from superpresenter.domain.song import Song, SongVariant, SongSection
from superpresenter.services.stationary_navigation import (
    CueNavigation, StationaryPageWidget, build_plan, style_mode,
)
from superpresenter.services.stationary_pages import generate_pages
from super_presenter import GUI, ProjWindow


def plan_for(count):
    song = Song('Test', [SongVariant('cs', [SongSection(
        'v1', [str(i) for i in range(count)])])])
    return build_plan(song, ['cs'], 'v1')[0]


class NavigationTests(unittest.TestCase):
    def test_one_hall_two_stream_steps(self):
        nav = CueNavigation([plan_for(8)])
        nav.move(1)
        first = nav.cue
        nav.move(1)
        self.assertIs(first.hall_page, nav.cue.hall_page)
        self.assertIsNot(first.stream_page, nav.cue.stream_page)
        nav.move(-1)
        self.assertIs(first, nav.cue)

    def test_two_hall_three_stream_steps(self):
        nav = CueNavigation([plan_for(10)])
        pages = []
        for _ in range(3):
            nav.move(1)
            pages.append((nav.cue.hall_page.index, nav.cue.stream_page.index))
        self.assertEqual(pages, [(0, 0), (0, 1), (1, 2)])

    def test_full_reverse_including_song_boundaries_and_empty_song(self):
        nav = CueNavigation([plan_for(8), generate_pages([]), plan_for(10)])
        forward = [(nav.song, nav.step, nav.cue)]
        while (nav.song, nav.step) != (2, 4):
            nav.move(1)
            forward.append((nav.song, nav.step, nav.cue))
        nav.move(1)
        self.assertEqual((nav.song, nav.step), (2, 4))
        for state in reversed(forward[:-1]):
            nav.move(-1)
            self.assertEqual((nav.song, nav.step, nav.cue), state)
        nav.move(-1)
        self.assertEqual(nav.step, 0)
        nav.select(1)
        self.assertEqual((nav.song, nav.step, nav.cue), (1, 0, None))
        self.assertIn('cue=- hall=- stream=-', nav.diagnostic())

    def test_empty_playlist(self):
        nav = CueNavigation([])
        nav.move(1)
        nav.move(-1)
        self.assertIsNone(nav.cue)

    def test_languages_and_pins_resolved_before_pagination(self):
        song = Song('Test', [SongVariant(name, [SongSection('v1',
            [f'{name}{i}' for i in range(4)])]) for name in ('cs', 'en')])
        plan, legacy = build_plan(song, ['cs', 'en'], 'v1 @v1.4 v1.1:2')
        self.assertEqual([len(p.lines) for p in plan.hall_pages], [8, 2, 4])
        self.assertEqual([r.text for r in plan.hall_pages[0].lines][:4],
                         ['cs0', 'en0', 'cs1', 'en1'])
        self.assertEqual(legacy, (1, 3, 5, 6))
        self.assertTrue(plan.hall_pages[1].lines[0].pinned)

    def test_modes_and_old_configuration(self):
        styles = json.loads((Path(__file__).resolve().parents[1] /
                             'projectors_styles.json').read_text(encoding='utf-8'))['styles']
        self.assertEqual([style_mode(s) for s in styles],
                         ['stationary_hall', 'stationary_stream'] + ['legacy_scroll'] * 4)
        for style in styles:
            old = dict(style)
            del old['mode']
            self.assertEqual(style_mode(old), style_mode(style))
            self.assertEqual(style_mode(dict(style, name='Renamed')), style['mode'])
        self.assertEqual(style_mode({'name': 'custom'}), 'legacy_scroll')
        with self.assertRaises(ValueError):
            style_mode({'mode': 'typo'})

    def test_same_verse_row_repeats_fit_as_a_whole(self):
        song = Song('Test', [SongVariant('cs', [
            SongSection('v1', ['a', 'b', 'c', 'd', 'last']),
            SongSection('r1', ['last', 'last', 'last']),
        ])])
        cases = [
            ('v1 (v1.5)*3', [8], [4, 4]),
            ('v1 (v1.5)*2', [7], [4, 3]),
            ('v1 v1.5 v1.5 v1.5', [8], [4, 4]),
            ('v1 (v1.5)*4', [5, 4], [4, 1, 4]),
            ('v1 (v1.5)*10', [5, 8, 2], [4, 1, 4, 4, 2]),
            ('v1 r1', [5, 3], [4, 1, 3]),
            ('v1 (r1.1)*3', [5, 3], [4, 1, 3]),
            ('v1 r1 v1.5', [5, 3, 1], [4, 1, 3, 1]),
            ('v1 v1.4:5', [7], [4, 3]),
            ('(v1 (v1.5)*3)*2', [8, 8], [4, 4, 4, 4]),
        ]
        for guide, halls, streams in cases:
            with self.subTest(guide=guide):
                plan, _ = build_plan(song, ['cs'], guide)
                self.assertEqual([len(p.lines) for p in plan.hall_pages], halls)
                self.assertEqual([len(p.lines) for p in plan.stream_pages], streams)
                self.assertEqual(len({c.navigation_id for c in plan.cues}), len(plan.cues))
                nav = CueNavigation([plan])
                for cue in plan.cues:
                    nav.move(1)
                    self.assertIs(nav.cue, cue)
                nav.move(1)
                for cue in reversed(plan.cues):
                    nav.move(-1)
                    self.assertIs(nav.cue, cue)
        plan, legacy_steps = build_plan(song, ['cs'], 'v1 (v1.5)*3')
        self.assertEqual([r.text for r in plan.hall_pages[0].lines],
                         ['a', 'b', 'c', 'd', 'last', 'last', 'last', 'last'])
        self.assertEqual([r.line_index for r in plan.hall_pages[0].lines],
                         [0, 1, 2, 3, 4, 4, 4, 4])
        self.assertEqual(legacy_steps, (1, 5))
        self.assertIs(plan.cues[0].hall_page, plan.cues[1].hall_page)

    def test_row_repeats_count_all_language_rows(self):
        song = Song('Test', [SongVariant(name, [SongSection('v1', ['a', 'b'])])
                             for name in ('cs', 'en')])
        plan, _ = build_plan(song, ['cs', 'en'], 'v1 (v1.2)*2')
        self.assertEqual([len(p.lines) for p in plan.hall_pages], [8])
        plan, _ = build_plan(song, ['cs', 'en'], 'v1 (v1.2)*3')
        self.assertEqual([len(p.lines) for p in plan.hall_pages], [4, 6])

    def test_full_verse_repetition_keeps_its_boundary(self):
        song = Song('Test', [SongVariant('cs', [SongSection('v1', ['a', 'b'])])])
        plan, _ = build_plan(song, ['cs'], '(v1)*2')
        self.assertEqual([len(p.lines) for p in plan.hall_pages], [2, 2])


class ProjectionTests(unittest.TestCase):
    def make_gui(self, modes):
        gui = GUI.__new__(GUI)
        gui.runState = gui.stationary_active = True
        gui.animation = 0
        gui.runningSlide = gui.currentStep = 0
        gui.stationary_navigation = CueNavigation([plan_for(8), plan_for(10)])
        gui.projStyles = [{'mode': mode} for mode in modes]
        gui.projectors = [Mock(style=i) for i in range(len(modes))]
        gui.onlineSources = [Mock(variants=['cs'], cue_legacy_steps=(1, 5),
                                  lines={'longsteps': list(range(8))}),
                             Mock(variants=['cs'], cue_legacy_steps=(1, 5, 9),
                                  lines={'longsteps': list(range(10))})]
        for name in ('stepsList', 'slideLabel', 'stepsLabel', 'win'):
            setattr(gui, name, Mock())
        gui.stepsLang = MagicMock()
        gui.stepsList.cget.return_value = '#444444'
        gui.stepsList.winfo_rgb.return_value = (17476, 17476, 17476)
        gui.win.focus_get.return_value._name = '!button'
        return gui

    def test_start_prepares_each_song_and_restart_resets_timeline(self):
        gui = self.make_gui(['stationary_hall', 'stationary_stream'])
        gui.runState = False
        # Widget state restoration is covered with real Tk in test_main_controls.
        gui._lock_editing = Mock()
        gui._unlock_editing = Mock()
        gui.song_editor_widget = Mock()
        gui.song_editor_widget.confirm_transition.return_value = True
        gui.sourceList = [0, 1]
        gui.sources = []
        for count in (8, 10):
            source = Mock(path='test.xml', repetitions='v1', variants=['cs'])
            source.song = Song('Test', [SongVariant('cs', [
                SongSection('v1', [str(i) for i in range(count)])])])
            source.loadSong.side_effect = AssertionError('Projection must use the saved snapshot')
            source.constructLines.return_value = ['cs']
            gui.sources.append(source)
        for name in ('openProjs', 'addProj', 'delProj', 'fullscreenCheck',
                     'chooseProj', 'chooseStyle', 'saveRepetitions'):
            setattr(gui, name, Mock())
        gui.onStyle = gui.offStyle = {}
        gui.runButtFun()
        self.assertTrue(gui.runState)
        self.assertEqual([len(p.cues) for p in gui.stationary_navigation.plans], [2, 3])
        for source in gui.sources:
            source.constructLines.assert_not_called()
        for source in gui.onlineSources:
            source.loadSong.assert_not_called()
            source.constructLines.assert_called_once_with([{'type': 'long'}])
        gui.nextStep()
        gui.nextSlide()
        gui.runButtFun()
        self.assertIsNone(gui.stationary_navigation)
        gui.runButtFun()
        self.assertEqual((gui.stationary_navigation.song,
                          gui.stationary_navigation.step), (0, 0))

    def test_empty_running_playlist_navigation_is_safe(self):
        gui = self.make_gui(['stationary_hall'])
        gui.stationary_navigation = CueNavigation([])
        gui.onlineSources = []
        gui.nextStep()
        gui.prevStep()
        gui.nextSlide()
        gui.prevSlide()
        gui.projectors[0].showStationaryPage.assert_not_called()

    def test_hall_stream_and_mixed_outputs(self):
        for modes in (['stationary_hall'], ['stationary_stream'],
                      ['stationary_hall', 'stationary_stream'],
                      ['stationary_hall', 'legacy_scroll']):
            with self.subTest(modes=modes):
                gui = self.make_gui(modes)
                gui.nextStepKey()
                first = gui.stationary_navigation.cue
                gui.nextStep()
                second = gui.stationary_navigation.cue
                for proj, mode in zip(gui.projectors, modes):
                    if mode == 'legacy_scroll':
                        proj.switch.assert_called_with((5, 5), 0)
                    else:
                        expected = second.hall_page if mode == 'stationary_hall' else second.stream_page
                        proj.showStationaryPage.assert_called_with(expected)
                gui.prevStepKey()
                self.assertIs(gui.stationary_navigation.cue, first)
                gui.nextSlide()
                self.assertEqual((gui.runningSlide, gui.currentStep), (1, 0))
                gui.prevStep()
                self.assertEqual((gui.runningSlide, gui.currentStep), (0, 3))
                gui.nextStep()
                self.assertEqual((gui.runningSlide, gui.currentStep), (1, 0))
                gui.win.after.assert_not_called()

    def test_click_selects_cue(self):
        gui = self.make_gui(['stationary_hall'])
        gui.pair2_active = gui.paged_active = False
        gui.loadSteps()
        gui.stepsList.index.return_value = 5
        gui.stepSelect(Mock())
        self.assertEqual(gui.stationary_navigation.cue.step_index, 1)
        gui.win.after.assert_not_called()

    def test_every_preview_row_selects_exact_cue_and_matches_outputs(self):
        gui = self.make_gui(['stationary_hall', 'stationary_stream'])
        gui.loadSteps()
        rows = list(gui.cue_rows)
        displayed = [call.args[1] for call in gui.stepsList.insert.call_args_list]
        expected = ['', *[line.text for cue in gui.stationary_navigation.plans[0].cues
                          for line in cue.stream_page.lines], '']
        self.assertEqual(displayed, expected)
        for index, (cue, step, _) in enumerate(rows):
            gui._stationary_select_row(index)
            self.assertIs(gui.stationary_navigation.cue, cue)
            self.assertEqual(gui.currentStep, step)
            for proj, page in zip(gui.projectors, (
                    cue.hall_page if cue else None,
                    cue.stream_page if cue else None)):
                proj.showStationaryPage.assert_called_with(page)
        gui.nextStep()
        self.assertEqual((gui.runningSlide, gui.currentStep), (1, 0))
        gui.prevStep()
        self.assertEqual((gui.runningSlide, gui.currentStep), (0, 3))
        gui.prevStep()
        self.assertIs(gui.stationary_navigation.cue, rows[-2][0])

    def test_selection_is_four_stream_rows_or_eight_hall_rows(self):
        for modes, expected in ((['stationary_hall'], 8),
                                (['stationary_hall', 'stationary_stream'], 4)):
            gui = self.make_gui(modes)
            gui.loadSteps()
            gui.stepsList.selection_set.reset_mock()
            gui.nextStep()
            self.assertEqual(gui.stepsList.selection_set.call_count, expected)
            selected = [call.args[0] for call in gui.stepsList.selection_set.call_args_list]
            self.assertTrue(all(gui.cue_rows[i][2] for i in selected))

    def test_alternating_sections_keep_color_across_pages_and_restore_after_selection(self):
        gui = self.make_gui(['stationary_hall', 'stationary_stream'])
        song = Song('Test', [SongVariant('cs', [SongSection(
            'v1', [str(i) for i in range(10)])])])
        plan, _ = build_plan(song, ['cs'], '(v1)*3')
        gui.stationary_navigation = CueNavigation([plan])
        gui.loadSteps()

        def backgrounds():
            gui.stepsList.itemconfigure.reset_mock()
            gui._select_stationary_rows()
            return [call.kwargs['background']
                    for call in gui.stepsList.itemconfigure.call_args_list]

        initial = backgrounds()
        self.assertEqual(initial, ['#444444'] * 11 + ['#535353'] * 10 + ['#444444'] * 11)
        gui._stationary_select_row(11)
        self.assertEqual(backgrounds()[11:19], ['#535353'] * 8)
        gui._stationary_select_row(0)
        self.assertEqual(backgrounds(), initial)

    def test_unchanged_hall_does_not_touch_canvas(self):
        canvas = Mock()
        style = dict(x=0, y=0, y1=40, fill='white', primaryFont='font')
        widget = StationaryPageWidget(canvas, style, {'font': 'font'}, 'stationary_hall')
        plan = plan_for(8)
        widget.show_page(plan.cues[0].hall_page)
        canvas.reset_mock()
        widget.show_page(plan.cues[1].hall_page)
        canvas.itemconfigure.assert_not_called()
        widget.show_page(None)
        self.assertEqual(canvas.itemconfigure.call_count, 8)
        canvas.reset_mock()
        widget.show_page(plan.cues[0].hall_page)
        self.assertEqual(canvas.itemconfigure.call_count, 8)

    def test_legacy_style_still_uses_original_widget_routing(self):
        from super_presenter import Widget_FlowLines, Widget_OneLine
        proj = ProjWindow.__new__(ProjWindow)
        proj.animation = 0
        hall = Mock(spec=Widget_FlowLines)
        stream = Mock(spec=Widget_OneLine)
        stream.srcType = 'short2'
        hall.switch.return_value = stream.switch.return_value = 0
        proj.animated = [hall, stream]
        proj.switch((2, 3), 1)
        hall.switch.assert_called_with(3, 1)
        stream.switch.assert_called_with(2, 1)


if __name__ == '__main__':
    unittest.main()

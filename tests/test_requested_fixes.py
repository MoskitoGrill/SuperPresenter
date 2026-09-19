"""Regression coverage for independent scrolling and returning to a verse."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from superpresenter.domain.song import Song, SongVariant, SongSection
from superpresenter.services.song_search import SearchResult
from superpresenter.services.stationary_navigation import CueNavigation, build_plan
from superpresenter.ui.mousewheel import bind_canvas_wheel
import test_stationary_navigation as navigation_tests


class RequestedFixesTests(unittest.TestCase):
    def test_search_shows_number_for_title_and_text_matches(self):
        for location in ('Soubor', 'Název', 'cs / v1'):
            result = SearchResult(Path('Kancionálky/235 - song.xml'), 'Název písně', location, 'text', 2)
            self.assertEqual(result.display_title, '235 – Název písně')
        result = SearchResult(Path('song.xml'), 'Název písně', 'Název', '', 0)
        self.assertEqual(result.display_title, 'Název písně')
        result = SearchResult(Path('235 - song.xml'), '235 – Název', 'Název', '', 0)
        self.assertEqual(result.display_title, '235 – Název')

    def test_back_from_next_verse_starts_first_stream_part(self):
        song = Song('Test', [SongVariant('cs', [
            SongSection('v1', [str(i) for i in range(8)]),
            SongSection('v2', ['next verse']),
        ])])
        plan, _ = build_plan(song, ['cs'], 'v1 v2 v1')
        gui = navigation_tests.ProjectionTests.make_gui(self, ['stationary_hall', 'stationary_stream'])
        gui.stationary_navigation = CueNavigation([plan])
        gui.stationary_navigation.select(0, 3)
        gui.prevStep()
        self.assertIs(gui.stationary_navigation.cue, plan.cues[0])
        gui.projectors[0].showStationaryPage.assert_called_with(plan.cues[0].hall_page)
        gui.projectors[1].showStationaryPage.assert_called_with(plan.cues[0].stream_page)
        gui.nextStep()
        self.assertIs(gui.stationary_navigation.cue, plan.cues[1])
        gui.prevStep()
        self.assertIs(gui.stationary_navigation.cue, plan.cues[0])
        gui.stationary_navigation.select(0, 4)
        gui.prevStep()
        self.assertIs(gui.stationary_navigation.cue, plan.cues[2])

    def test_wheel_only_scrolls_canvas_under_pointer_and_cleans_up(self):
        top = Mock()
        top.bind.return_value = 'binding-id'
        canvas = Mock(master=top)
        canvas.winfo_toplevel.return_value = top
        callback = Mock()
        bind_canvas_wheel(canvas, callback)
        handler = top.bind.call_args.args[1]
        event = SimpleNamespace(x_root=10, y_root=20, delta=-120)
        outside = Mock(master=None)
        canvas.winfo_containing.return_value = outside
        handler(event)
        callback.assert_not_called()
        child = Mock(master=canvas)
        child.winfo_class.return_value = 'Label'
        canvas.winfo_containing.return_value = child
        self.assertEqual(handler(event), 'break')
        callback.assert_called_once_with(event)
        callback.reset_mock()
        child.winfo_class.return_value = 'Text'
        handler(event)
        callback.assert_not_called()
        canvas.bind.call_args.args[1](SimpleNamespace(widget=canvas))
        top.unbind.assert_called_once_with('<MouseWheel>', 'binding-id')

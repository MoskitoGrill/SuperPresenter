"""Configurable hall capacity, shared stream cues and profile persistence."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from superpresenter.domain.song import Song, SongVariant, SongSection
from superpresenter.services.stationary_navigation import (
    build_plan, CueNavigation, StationaryPageWidget,
)
from superpresenter.services.projection_config import (
    ConfigError, validate_layout, save_layout, load_layout, layout_row_limit,
)
from superpresenter.services.projection_editor_model import editor_cards, layout_from_cards


class LineLimitTests(unittest.TestCase):
    def song(self, count=11):
        return Song('Test', [SongVariant(name, [SongSection('v1', [str(i) for i in range(count)])])
                             for name in ('cs', 'en')])

    def test_all_capacities_preserve_rows_and_reverse_navigation(self):
        for limit in (1, 2, 3, 4, 5, 7, 8, 9, 12, 25):
            for languages in (['cs'], ['cs', 'en']):
                with self.subTest(limit=limit, languages=languages):
                    plan, steps = build_plan(self.song(), languages, 'v1', limit)
                    expected = [str(i) for i in range(11) for _ in languages]
                    self.assertEqual([r.text for p in plan.hall_pages for r in p.lines], expected)
                    self.assertEqual([r.text for p in plan.stream_pages for r in p.lines], expected)
                    self.assertTrue(all(len(p.lines) <= limit for p in plan.hall_pages))
                    self.assertTrue(all(len(p.lines) <= min(4, limit) for p in plan.stream_pages))
                    self.assertEqual(len(steps), len(plan.cues))
                    self.assertEqual(len({c.navigation_id for c in plan.cues}), len(plan.cues))
                    nav = CueNavigation([plan])
                    for cue in plan.cues:
                        nav.move(1)
                        self.assertIs(nav.cue, cue)
                    nav.move(1)
                    for cue in reversed(plan.cues):
                        nav.move(-1)
                        self.assertIs(nav.cue, cue)

    def test_append_and_repeat_use_selected_capacity(self):
        for guide in ('v1 @v1.3', 'v1 v1.3'):
            for limit, lengths in ((3, [3, 1]), (4, [4]), (12, [4])):
                plan, _ = build_plan(self.song(3), ['cs'], guide, limit)
                self.assertEqual([len(p.lines) for p in plan.hall_pages], lengths)
        plan, _ = build_plan(self.song(5), ['cs'], 'v1 (v1.5)*5', 10)
        self.assertEqual([len(p.lines) for p in plan.hall_pages], [10])
        plan, _ = build_plan(self.song(5), ['cs'], 'v1 (v1.5)*5', 9)
        self.assertEqual([len(p.lines) for p in plan.hall_pages], [5, 5])

    def test_invalid_capacity(self):
        for limit in (0, -1, True, 2.5, '3', None):
            with self.assertRaises(ValueError):
                build_plan(self.song(), ['cs'], 'v1', limit)

    def test_shared_hall_limit_and_stream_only_default(self):
        styles = [dict(name='hall', mode='stationary_hall'), dict(name='stream', mode='stationary_stream')]
        halls = [dict(style='hall', lines_per_page=n) for n in (12, 3)]
        stream = dict(style='stream', lines_per_page=8)
        self.assertEqual(layout_row_limit(dict(outputs=halls + [stream]), styles), 3)
        self.assertEqual(layout_row_limit(dict(outputs=[stream]), styles), 8)

    def test_renderer_uses_same_capacity_and_scales_large_pages(self):
        style = dict(x=100, y=20, y1=50, primaryFont='main', fill='white')
        for limit in (1, 3, 5, 8, 12):
            for mode in ('stationary_hall', 'stationary_stream'):
                canvas, font = Mock(), Mock()
                font.copy.return_value.cget.return_value = 48
                widget = StationaryPageWidget(canvas, style, {'main': font}, mode, limit)
                capacity = limit if mode == 'stationary_hall' else min(4, limit)
                self.assertEqual(len(widget.items), capacity)
                self.assertEqual(canvas.create_text.call_count, capacity)
                if limit > 8 and mode == 'stationary_hall':
                    font.copy.return_value.configure.assert_called_once_with(size=32)
                plan, _ = build_plan(self.song(), ['cs'], 'v1', limit)
                widget.show_page(plan.hall_pages[0] if mode == 'stationary_hall' else plan.stream_pages[0])
                self.assertEqual(canvas.itemconfigure.call_count, capacity)

    def test_editor_profile_roundtrip_and_validation(self):
        styles = [{'name': 'hall', 'mode': 'stationary_hall'}]
        monitor = SimpleNamespace(name='screen', x=0, y=0, width=1920, height=1080)
        output = dict(style='hall', monitor=vars(monitor), fullscreen=True,
                      collection=False, window_position=None, lines_per_page=3)
        layout = dict(version=2, outputs=[output])
        cards = editor_cards(layout, [monitor])
        data = layout_from_cards(cards, [monitor], styles)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'profile.json'
            save_layout(path, data, styles)
            self.assertEqual(load_layout(path, styles)['outputs'][0]['lines_per_page'], 3)
        for invalid in (0, -1, True, '3', 3.5):
            output['lines_per_page'] = invalid
            with self.assertRaises(ConfigError):
                validate_layout(layout, styles)
        del output['lines_per_page']
        validate_layout(layout, styles)  # Old profiles keep their default of eight.

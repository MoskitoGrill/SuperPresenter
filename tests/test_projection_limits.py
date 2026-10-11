"""Stage 13C: capacities, profile persistence, fresh runs and actual Tk output."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from superpresenter.domain.song import Song
from superpresenter.services.projection_config import ConfigError, layout_row_limit, load_layout, save_layout
from superpresenter.services.stationary_navigation import build_plan
from superpresenter.services.stationary_pages import format_timeline
from superpresenter.ui.projection_profiles import ProjectionProfiles
import test_release_stability as release
import test_projection_editor as editor_tests


class LimitsTests(unittest.TestCase):
    def test_per_output_drafts_migrate_to_shared_limit(self):
        styles = [dict(name='hall', mode='stationary_hall'),
                  dict(name='stream', mode='stationary_stream')]
        data = dict(outputs=[dict(style='hall', lines_per_page=10),
                             dict(style='hall', lines_per_page=3),
                             dict(style='stream', lines_per_page=1)])
        self.assertEqual(layout_row_limit(data, styles), 3)
        data['hall_max_rows'] = 4
        self.assertEqual(layout_row_limit(data, styles), 4)

    def test_sections_long_verse_stream_and_fresh_plans(self):
        song = Song.from_texts('Test', {'cs': {
            'v1': '\n'.join('abcd'), 'v2': '\n'.join(map(str, range(13))),
            'r1': 'refrain\nend'}}, {'default': 'v1 v2 r1'})
        original = deepcopy(song)
        expected = {3: [3, 1, 3, 3, 3, 3, 1, 2], 4: [4, 4, 4, 4, 1, 2],
                    8: [4, 8, 5, 2], 10: [4, 10, 3, 2], 1: [1] * 19, 2: [2, 2] + [2] * 6 + [1, 2]}
        for limit in (3, 4, 8, 10, 1, 2, 8):
            with self.subTest(limit=limit):
                plan, _ = build_plan(song, ['cs'], 'v1 v2 r1', limit)
                self.assertEqual([len(p.lines) for p in plan.hall_pages], expected[limit])
                self.assertTrue(all(len(p.lines) <= min(4, limit) for p in plan.stream_pages))
                self.assertEqual([r for p in plan.hall_pages for r in p.lines],
                                 [r for p in plan.stream_pages for r in p.lines])
                self.assertEqual(len(set(c.navigation_id for c in plan.cues)), len(plan.cues))
                self.assertIn('stream 1.1', format_timeline(plan))
                self.assertEqual(song, original)

    def test_explicit_append_uses_current_capacity(self):
        song = Song.from_texts('Test', {'cs': {'v1': 'a\nb\nc'}}, {'default': 'v1'})
        for guide in ('v1 @v1.3', 'v1 v1.3'):
            for limit, expected in ((3, [3, 1]), (4, [4]), (8, [4]), (10, [4])):
                with self.subTest(guide=guide, limit=limit):
                    plan, _ = build_plan(song, ['cs'], guide, limit)
                    self.assertEqual([len(p.lines) for p in plan.hall_pages], expected)

    def test_invalid_limits_and_profile_roundtrip(self):
        for value in (0, -1, True, 3.5, '3', None):
            with self.subTest(value=value), self.assertRaises(ConfigError):
                save_layout('unused.json', dict(version=2, outputs=[], hall_max_rows=value), [])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'last-layout.json'
            for limit in (3, 4, 8, 10):
                data = dict(version=2, outputs=[], hall_max_rows=limit)
                save_layout(path, data, [])
                self.assertEqual(load_layout(path, []), data)


class EditorLimitsTests(unittest.TestCase):
    setUp = editor_tests.ProjectionEditorWidgetTests.setUp

    def test_load_per_output_draft_retains_its_effective_limit(self):
        self.editor.original['outputs'][0]['lines_per_page'] = 3
        self.editor.render_cards()
        self.assertEqual(self.editor.hall_rows.get(), '3')
        self.assertEqual(self.editor.draft()['hall_max_rows'], 3)

    def test_draft_save_reload_and_invalid_values(self):
        editor = self.editor
        for value in ('', '0', '-1', '3.5', 'abc'):
            editor.hall_rows.set(value)
            with self.assertRaises(ConfigError):
                editor.draft()
        for limit in (3, 4, 8, 10):
            editor.hall_rows.set(str(limit))
            self.assertEqual(editor.draft()['hall_max_rows'], limit)
            self.assertTrue(editor.save_profile())
            saved = load_layout(editor.entries[editor.selected_profile]['path'], self.owner.projStyles)
            self.assertEqual(saved['hall_max_rows'], limit)
            editor.original = saved
            editor.render_cards()
            self.assertEqual(editor.hall_rows.get(), str(limit))


class RunningLimitsTests(unittest.TestCase):
    setUp = release.ReleaseTests.setUp
    destroy = release.ReleaseTests.destroy
    configure_outputs = release.ReleaseTests.configure_outputs

    def test_restart_recomputes_preview_and_canvas_without_changing_song(self):
        gui = self.gui
        self.configure_outputs([0, 1])
        original = [deepcopy(s.song) for s in gui.sources]
        previous_plan = None
        for limit in (3, 4, 8, 10, 3):
            gui.hall_max_rows = limit
            gui.runButtFun()
            self.assertTrue(gui.runState)
            plan = gui.stationary_navigation.plans[0]
            self.assertIsNot(plan, previous_plan)
            self.assertEqual([len(p.lines) for p in plan.hall_pages],
                             [min(limit, 10 - start) for start in range(0, 10, limit)])
            gui.nextStep()
            for projector, page, capacity in zip(gui.projectors,
                    (plan.cues[0].hall_page, plan.cues[0].stream_page), (limit, min(4, limit))):
                widget = projector.animated[0]
                self.assertEqual(len(widget.items), capacity)
                if projector is gui.projectors[0] and limit > 8:
                    self.assertLess(widget.font.cget('size'), 33)
                    self.assertLessEqual(projector.canvas.coords(widget.items[-1])[1], 100 + 8 * 48)
                self.assertEqual([projector.canvas.itemcget(item, 'text') for item in widget.items],
                                 [r.text for r in page.lines] + [''] * (capacity - len(page.lines)))
            self.assertEqual(len(gui.stepsList.curselection()), min(4, limit))
            self.assertEqual([s.song for s in gui.sources], original)
            previous_plan = plan
            gui.runButtFun()
            self.assertIsNone(gui.stationary_navigation)
        # Restore the setting through the same path used on application startup.
        gui.profile_dir = Path(self.tmp.name)
        gui._profiles_ready = True
        gui._preserve_last = False
        ProjectionProfiles.persist_layout(gui)
        gui.hall_max_rows = 8
        self.assertTrue(gui.restore_profile(gui.profile_dir / 'last-layout.json'))
        self.assertEqual(gui.hall_max_rows, 3)
        self.error.assert_not_called()

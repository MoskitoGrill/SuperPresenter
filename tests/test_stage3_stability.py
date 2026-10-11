"""Stage 3 error boundaries, interval clocks and per-refresh playlist marks."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_release_stability as release
from superpresenter.ui.song_search_window import SongSearchWindow, playlist_paths


class ErrorBoundaryTests(unittest.TestCase):
    def setUp(self):
        release.ReleaseTests.setUp(self)
        self.bgerrors = []
        self.gui.win.createcommand('stage3_bgerror', self.bgerrors.append)
        self.gui.win.tk.eval('proc bgerror {message} {stage3_bgerror $message}')
        self.addCleanup(lambda: self.assertEqual(self.bgerrors, []))

    destroy = release.ReleaseTests.destroy
    configure_outputs = release.ReleaseTests.configure_outputs

    def search_window(self):
        window = SongSearchWindow(self.gui)
        self.addCleanup(window.close)
        timer = window.poll
        window.future.result(timeout=10)
        window.check_index()
        if timer is not None:
            self.assertNotIn(timer, self.gui.win.tk.call('after', 'info'))
        return window

    def test_auxiliary_failure_keeps_projection_and_recovers(self):
        self.configure_outputs([0])
        self.gui.runButtFun()
        snapshot = deepcopy([s.song for s in self.gui.onlineSources])
        window = self.search_window()
        result = SimpleNamespace(path=self.gui.sources[0].path,
                                 display_title='First', snippet='text')
        with patch.object(window.search_index, 'search', return_value=[result]):
            window.search()
            window.tree.selection_set('0')
            with patch.object(window.search_index, 'search', side_effect=RuntimeError('read failed')):
                with self.assertLogs('superpresenter.ui.song_search_window', level='ERROR'):
                    window.search()
            self.assertEqual(window.results, [])
            self.assertEqual(window.tree.get_children(), ())
            self.assertEqual(str(window.add_button['state']), 'disabled')
            self.assertTrue(self.gui.runState)
            self.assertTrue(hasattr(self.gui.projectors[0], 'win'))
            self.assertEqual([s.song for s in self.gui.onlineSources], snapshot)
            window.search()
            self.assertEqual(len(window.results), 1)
        self.gui.nextStep()
        self.gui.runButtFun()
        self.assertNotEqual(str(self.gui.chooseStyle['state']), 'disabled')

    def test_mutation_failure_uses_global_cleanup_and_can_restart(self):
        self.configure_outputs([2])
        self.gui.runButtFun()
        window = self.search_window()
        result = SimpleNamespace(path=self.gui.sources[0].path,
                                 display_title='First', snippet='text')
        with patch.object(window.search_index, 'search', return_value=[result]):
            window.search()
        window.tree.selection_set('0')
        window.add_button.configure(state='normal')
        with patch('superpresenter.ui.song_search_window.add_result', side_effect=RuntimeError('mutation failed')):
            with patch('superpresenter.ui.main_window.tk.Tk', type(self.gui.win)):
                with patch.object(type(self.gui.win), 'report_callback_exception') as fallback:
                    with self.assertLogs('superpresenter.ui.main_window', level='ERROR'):
                        window.add_button.invoke()
        fallback.assert_called_once()
        self.assertFalse(self.gui.runState)
        self.assertFalse(hasattr(self.gui.projectors[0], 'win'))
        self.assertNotEqual(str(self.gui.chooseStyle['state']), 'disabled')
        self.gui.runButtFun()
        self.assertTrue(self.gui.runState)
        with patch.object(self.gui, 'addSource', side_effect=RuntimeError('browse mutation failed')):
            with patch('superpresenter.ui.main_window.tk.Tk', type(self.gui.win)):
                with patch.object(type(self.gui.win), 'report_callback_exception') as fallback:
                    with self.assertLogs('superpresenter.ui.main_window', level='ERROR'):
                        window.browse_button.invoke()
        fallback.assert_called_once()
        self.assertFalse(self.gui.runState)
        self.assertFalse(hasattr(self.gui.projectors[0], 'win'))
        self.gui.runButtFun()
        self.assertTrue(self.gui.runState)

    def test_projection_callback_failure_cancels_animation_and_restarts(self):
        self.configure_outputs([2])
        self.gui.runButtFun()
        self.gui.t = 0
        self.gui.nextStep()
        timer = self.gui._animation_timer
        with patch.object(self.gui.projectors[0], 'switch', side_effect=RuntimeError('projection failed')):
            with patch('superpresenter.ui.main_window.tk.Tk', type(self.gui.win)):
                with patch.object(type(self.gui.win), 'report_callback_exception') as fallback:
                    with self.assertLogs('superpresenter.ui.main_window', level='ERROR'):
                        self.gui.win.after(200, self.gui.win.quit)
                        self.gui.win.mainloop()
        fallback.assert_called_once()
        self.assertFalse(self.gui.runState)
        self.assertIsNone(self.gui._animation_timer)
        self.assertNotIn(timer, self.gui.win.tk.call('after', 'info'))
        self.assertFalse(hasattr(self.gui.projectors[0], 'win'))
        self.gui.runButtFun()
        self.assertTrue(self.gui.runState)

    def test_animation_uses_one_monotonic_sample(self):
        self.configure_outputs([2])
        self.gui.runButtFun()
        self.gui.t = 100
        timeout = self.gui.animationParams['anim_timeout']
        with patch('superpresenter.ui.main_window.time.time', side_effect=AssertionError('wall clock')):
            with patch('superpresenter.ui.main_window.time.monotonic', return_value=100 + timeout / 2) as clock:
                with patch.object(self.gui, '_update_projectors') as update:
                    self.gui.stepGoTo()
                clock.assert_called_once()
                update.assert_called_once_with(anim=0)
            with patch('superpresenter.ui.main_window.time.monotonic', return_value=101 + timeout):
                self.gui.stepGoTo()
                self.assertEqual(self.gui.animation, 1)
                self.assertIsNotNone(self.gui._animation_timer)

    def test_marks_refresh_with_duplicates_and_playlist_changes(self):
        window = self.search_window()
        results = [SimpleNamespace(path=s.path, display_title=str(i), snippet='text')
                   for i, s in enumerate(self.gui.sources)]
        self.gui.sourceList = [0, 0]
        with patch.object(window.search_index, 'search', return_value=results):
            with patch('superpresenter.ui.song_search_window.playlist_paths', wraps=playlist_paths) as paths:
                window.search()
                paths.assert_called_once()
            self.assertIn('(v playlistu)', window.tree.item('0', 'values')[0])
            self.assertNotIn('(v playlistu)', window.tree.item('1', 'values')[0])
            self.gui.sourceList = [1]
            window.search()
            self.assertNotIn('(v playlistu)', window.tree.item('0', 'values')[0])
            self.assertIn('(v playlistu)', window.tree.item('1', 'values')[0])

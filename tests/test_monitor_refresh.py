"""Automatic monitor refresh without real displays or a Tk root."""
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest

from superpresenter.ui.projection_profiles import ProjectionProfiles


def monitor(name, x, primary=False):
    return SimpleNamespace(name=name, x=x, y=0, width=1920, height=1080, is_primary=primary)


class MonitorRefreshTests(unittest.TestCase):
    def setUp(self):
        self.gui = ProjectionProfiles()
        self.main = monitor('main', 0, True)
        self.gui.monitors = [self.main]
        self.projector = SimpleNamespace(monitor=0, winPlacement='', window_position=None)
        self.gui.projectors = [self.projector]
        self.gui.projectorID = 0
        self.gui.runState = False
        self.gui.chooseProj = {}
        self.gui.win = Mock()
        self.gui.openProjector = Mock()
        self.gui._cleanup_after_stop = Mock()
        self.gui.restore_profile = Mock(return_value=True)
        self.gui.layout_snapshot = Mock(return_value={'snapshot': True})
        self.gui.start_monitor_watch()

    def poll(self, monitors):
        with patch('superpresenter.ui.projection_profiles.get_monitors', return_value=monitors):
            self.gui.poll_monitors()

    def test_new_monitor_remaps_indices_without_replacing_projector(self):
        self.gui.runState = True
        self.poll([self.main, monitor('new', -1920)])
        self.assertEqual(len(self.gui.monitors), 2)
        self.assertEqual(self.projector.monitor, 1)
        self.assertIs(self.gui.projectors[0], self.projector)
        self.gui._cleanup_after_stop.assert_not_called()
        self.assertTrue(self.gui.runState)

    def test_unchanged_poll_does_not_touch_selection(self):
        self.poll([self.main])
        self.gui.openProjector.assert_not_called()
        self.gui.win.after.assert_called_with(2000, self.gui.poll_monitors)

    def test_missing_active_display_stops_once_and_offers_restore(self):
        self.gui.runState = True
        replacement = monitor('replacement', 0, True)
        with patch('superpresenter.ui.projection_profiles.messagebox.showwarning') as warning:
            self.poll([replacement])
            self.poll([replacement])
        self.gui._cleanup_after_stop.assert_called_once()
        self.gui.restore_profile.assert_called_once_with(None, data={'snapshot': True})
        warning.assert_called_once()
        self.assertFalse(self.gui.runState)
        self.assertTrue(self.gui._preserve_last)

    def test_moved_active_monitor_stops_and_clears_window_position(self):
        self.gui.runState = True
        self.projector.window_position = [30, 20]
        with patch('superpresenter.ui.projection_profiles.messagebox.showwarning'):
            self.poll([monitor('main', -1920, True)])
        self.gui._cleanup_after_stop.assert_called_once()
        self.assertIsNone(self.projector.window_position)

    def test_failed_or_empty_enumeration_keeps_old_monitors(self):
        self.poll([])
        with patch('superpresenter.ui.projection_profiles.get_monitors', side_effect=OSError('temporarily unavailable')), patch('superpresenter.ui.projection_profiles.logging.getLogger'):
            self.gui.poll_monitors()
        self.assertEqual(self.gui.monitors, [self.main])
        self.gui.openProjector.assert_not_called()

    def test_editor_is_refreshed_without_fallback_dialog(self):
        self.gui._projection_editor = Mock()
        self.gui._projection_editor.win.winfo_exists.return_value = True
        replacement = monitor('replacement', 0, True)
        self.poll([replacement])
        self.gui._projection_editor.refresh_topology.assert_called_once_with([replacement])
        self.gui.restore_profile.assert_not_called()
        self.gui._projection_editor.win.winfo_exists.return_value = False
        self.poll([replacement])
        self.gui.restore_profile.assert_called_once()

    def test_stopping_watch_cancels_callback(self):
        self.gui.stop_monitor_watch()
        self.gui.win.after_cancel.assert_called_once()
        self.gui.win.after.reset_mock()
        self.poll([self.main])
        self.gui.win.after.assert_not_called()


if __name__ == '__main__':
    unittest.main()

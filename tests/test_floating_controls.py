"""Floating remote integration with real widgets and isolated songs."""
import unittest

import test_release_stability as release
from superpresenter.services.stationary_navigation import style_mode


class FloatingTests(unittest.TestCase):
    setUp = release.ReleaseTests.setUp
    destroy = release.ReleaseTests.destroy
    configure_outputs = release.ReleaseTests.configure_outputs

    def open_remote(self, stream=False):
        styles = self.gui.projStyles
        hall = next(i for i, style in enumerate(styles) if style_mode(style) == 'stationary_hall')
        outputs = [hall]
        if stream:
            outputs.append(next(i for i, style in enumerate(styles) if style_mode(style) == 'stationary_stream'))
        self.configure_outputs(outputs)
        self.gui.openFloatingControls()
        remote = self.gui.floating_controls
        self.addCleanup(lambda: remote.close() if remote.win.winfo_exists() else None)
        remote.win.geometry('+30000+30000')
        remote.toggle()
        return remote

    def test_hall_skips_stream_halves_and_boundaries(self):
        remote = self.open_remote()
        nav = self.gui.stationary_navigation
        self.assertTrue(remote.win.attributes('-topmost'))
        remote.move(1)
        first = nav.cue.hall_page
        self.assertEqual(first.lines[-1].text, remote.current['text'])
        remote.move(1)
        self.assertIsNot(nav.cue.hall_page, first)
        remote.move(-1)
        self.assertIs(nav.cue.hall_page, first)
        self.assertEqual(nav.step, 1)
        remote.boundary(True)
        self.assertEqual(nav.step, nav.last_step)
        self.assertEqual(nav.song, 0)
        remote.boundary(False)
        self.assertEqual(nav.step, 0)
        remote.close()
        self.assertTrue(self.gui.runState)

    def test_stream_preview_and_external_navigation(self):
        remote = self.open_remote(True)
        nav = self.gui.stationary_navigation
        remote.move(1)
        self.assertIn(nav.cue.stream_page.lines[-1].text, remote.current['text'])
        expected = nav.plans[0].cues[1].stream_page.lines[0].text
        self.assertEqual(expected, remote.following['text'])
        self.assertEqual(remote.run['text'], '■')
        self.gui.nextStep()
        remote.refresh()
        self.assertEqual(nav.step, 2)
        self.assertIn(nav.cue.stream_page.lines[-1].text, remote.current['text'])
        remote.move(-1)
        self.assertEqual(nav.step, 1)
        remote.toggle()
        self.assertFalse(self.gui.runState)
        self.assertEqual(str(remote.buttons[0]['state']), 'disabled')
        self.assertEqual(remote.run['text'], '▶')
        self.assertEqual(remote.current['text'], '')
        self.assertEqual(remote.following['text'], '')

    def test_toggle_reopens_one_window(self):
        self.gui.openFloatingControls()
        first = self.gui.floating_controls
        self.gui.openFloatingControls()
        self.assertIsNone(self.gui.floating_controls)
        self.assertFalse(first.win.winfo_exists())
        self.gui.openFloatingControls()
        self.gui.floating_controls.close()


if __name__ == '__main__':
    unittest.main()

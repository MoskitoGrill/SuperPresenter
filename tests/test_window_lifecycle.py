"""Stage 2 regressions with real Tk windows and isolated songs."""
import gc
import weakref
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest

import test_release_stability as release
from superpresenter.ui.collection_qr_editor import CollectionQREditor
from superpresenter.ui.projector_widgets import Widget_Image
from PIL import Image


class LifecycleTests(unittest.TestCase):
    setUp = release.ReleaseTests.setUp
    destroy = release.ReleaseTests.destroy
    configure_outputs = release.ReleaseTests.configure_outputs

    def drain(self):
        self.gui.win.tk.call('after', 80)
        self.gui.win.update()

    def watch_errors(self):
        self.errors = []
        self.gui.win.createcommand('record_bgerror', self.errors.append)
        self.gui.win.tk.eval('proc bgerror {message} {record_bgerror $message}')
        self.gui.win.report_callback_exception = lambda *args: self.errors.append(str(args[1]))

    def test_sorter_remote_and_qr_destroy_cancel_pending_jobs(self):
        self.watch_errors()
        for _ in range(3):
            self.gui.sortSources()
            sorter = self.gui.sorter
            self.gui.sortSources()
            self.assertIs(self.gui.sorter, sorter)
            sorter.click(SimpleNamespace(x_root=sorter.win.winfo_rootx(),
                                         y_root=sorter.win.winfo_rooty()))
            timer = sorter._drag_timer
            sorter.win.destroy()
            del self.gui.sorter
            self.assertNotIn(timer, self.gui.win.tk.call('after', 'info'))
            self.gui.openFloatingControls()
            remote = self.gui.floating_controls
            timer = remote.timer
            remote.win.destroy()
            self.assertIsNone(self.gui.floating_controls)
            self.assertNotIn(timer, self.gui.win.tk.call('after', 'info'))
            qr = CollectionQREditor(self.gui.win, self.gui.projStyles[0], None, lambda _: None)
            qr.schedule_draw()
            timer = qr._draw_job
            qr.win.destroy()
            self.assertNotIn(timer, self.gui.win.tk.call('after', 'info'))
            self.drain()
        self.assertEqual(self.errors, [])

    def test_recovery_idle_and_main_timers_cancel_on_root_destroy(self):
        gui = self.gui
        editor = gui.song_editor_widget
        editor.start_recovery(self.tmp.name + '/recovery')
        offer = editor._recovery_offer_after
        self.assertIn(offer, gui.win.tk.call('after', 'info'))
        # Exercise the real watch, which the shared fixture disables at startup.
        from superpresenter.ui.projection_profiles import ProjectionProfiles
        ProjectionProfiles.start_monitor_watch(gui)
        gui._animation_timer = gui.win.after(500, lambda: None)
        gui.win.destroy()
        self.assertIsNone(editor._recovery_offer_after)
        self.assertIsNone(editor._recovery)
        self.assertIsNone(gui._animation_timer)
        self.assertIsNone(gui._monitor_timer)
        self.assertFalse(gui.win.tk.call('after', 'info'))
        gui.win = Mock(winfo_exists=Mock(return_value=False))

    def test_image_files_close_even_when_photo_creation_fails(self):
        gui = self.gui
        path = self.tmp.name + '/image.png'
        with Image.new('RGB', (10, 10)) as image:
            image.save(path)
        original_open = Image.open
        opened = []
        def tracked_open(*args, **kwargs):
            image = original_open(*args, **kwargs)
            opened.append(image)
            return image
        import tkinter as tk
        canvas = tk.Canvas(gui.win)
        for resized in (False, True):
            style = dict(source=path, x=0, y=0, anchor='nw')
            if resized:
                style['resize'] = [20, 20]
            with patch('superpresenter.ui.projector_widgets.resource_path', return_value=path), \
                 patch('superpresenter.ui.projector_widgets.Image.open', side_effect=tracked_open), \
                 patch('superpresenter.ui.projector_widgets.ImageTk.PhotoImage', side_effect=RuntimeError('photo')):
                with self.assertRaisesRegex(RuntimeError, 'photo'):
                    Widget_Image(canvas, style, gui.win)
            self.assertIsNone(opened[-1].fp)
        self.configure_outputs([2])
        projector = gui.projectors[0]
        projector.canvas = canvas
        for size in (0, 20):
            with patch.object(projector, '_get_collection_cfg', return_value=dict(source=path, size=size)), \
                 patch('superpresenter.ui.projector_window.resource_path', return_value=path), \
                 patch('PIL.Image.open', side_effect=tracked_open), \
                 patch('PIL.ImageTk.PhotoImage', side_effect=RuntimeError('photo')):
                with self.assertRaisesRegex(RuntimeError, 'photo'):
                    projector._build_collection_overlay()
            self.assertIsNone(opened[-1].fp)

    def test_stop_releases_renderers_and_failed_partial_start_can_restart(self):
        self.watch_errors()
        for styles in ([0, 1], [2], [3], [4], [5]):
            self.configure_outputs(styles)
            for _ in range(2):
                self.gui.runButtFun()
                self.assertTrue(self.gui.runState)
                renderer_refs = [weakref.ref(w) for p in self.gui.projectors for w in p.animated + p.others]
                self.gui.runButtFun()
                gc.collect()
                self.assertTrue(all(ref() is None for ref in renderer_refs))
                for p in self.gui.projectors:
                    self.assertFalse(hasattr(p, 'canvas'))
                    self.assertFalse(hasattr(p, 'win'))
                    self.assertIsNone(p.collection_img)
                    p.stopProjection()
        self.configure_outputs([0, 1])
        projector = self.gui.projectors[1]
        with patch.object(projector, '_build_collection_overlay', side_effect=RuntimeError('partial start')):
            with self.assertLogs('superpresenter.ui.main_window', level='ERROR'):
                self.gui.runButtFun()
        self.assertFalse(self.gui.runState)
        self.assertFalse(self.gui.onlineSources)
        self.assertTrue(all(not hasattr(p, 'win') for p in self.gui.projectors))
        self.assertIsNone(self.gui._editing_states)
        self.gui.runButtFun()
        self.assertTrue(self.gui.runState)
        self.gui.runButtFun()
        self.drain()
        self.assertEqual(self.errors, [])

    def test_remove_compacts_indices_preserves_duplicates_sorter_and_snapshot(self):
        gui = self.gui
        self.enterContext(patch.object(gui, '_prepare_song_transition', return_value=True))
        self.enterContext(patch.object(gui, 'saveRepetitions'))
        self.configure_outputs([0])
        gui.sourceList = [1, 0, 1]
        removed = weakref.ref(gui.sources[0])
        gui.runButtFun()
        snapshot = gui.onlineSources
        gui.sortSources()
        gui.sorter.positions.reverse()
        gui.sourceID = 1
        gui.closeSourceFun()
        gc.collect()
        self.assertIsNone(removed())
        self.assertEqual(gui.sourceList, [0, 0])
        self.assertEqual(gui.sorter.positions, [0, 0])
        self.assertEqual(len(gui.sources), 1)
        self.assertEqual([s.song.title for s in snapshot], ['Second', 'First', 'Second'])
        with patch('superpresenter.ui.main_window.tkmsg.askyesnocancel', return_value=True):
            gui.closeSorter()
        gui.closeSourceFun()
        self.assertEqual(len(gui.sources), 1)
        gui.closeSourceFun()
        self.assertEqual(gui.sources, [])
        self.assertEqual(gui.sourceList, [])
        self.assertIs(gui.onlineSources, snapshot)
        gui.runButtFun()
        path = snapshot[0].path
        for _ in range(5):
            gui.loadSource(path)
            gui.closeSourceFun()
            self.assertEqual(gui.sources, [])


if __name__ == '__main__':
    unittest.main()

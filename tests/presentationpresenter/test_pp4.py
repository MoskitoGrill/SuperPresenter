import tkinter as tk
import unittest
import sys
import ctypes
from ctypes import wintypes
from types import SimpleNamespace
from unittest.mock import patch
from presentationpresenter.ui import MainWindow
from presentationpresenter.projection import Monitor, monitors, configure_dpi
from presentationpresenter.settings import AppSettings

configure_dpi()


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.update()
        self.monitors = [Monitor('A', 0, 0, 800, 600), Monitor('B', -640, -100, 640, 360)]
        self.discovery = patch('presentationpresenter.ui.monitors', return_value=self.monitors)
        self.discovery.start()
        self.w = MainWindow(self.root, AppSettings())
        self.callback_errors = []
        self.root.report_callback_exception = lambda *error: self.callback_errors.append(error)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.discovery.stop()
        self.assertEqual(self.callback_errors, [])

    def test_synchronization_snapshot_blackout_resize_and_restart(self):
        w = self.w
        w.text.insert('1.0', 'Potvrzený obsah')
        self.root.update()
        self.assertTrue(w.start_projection(('hall', 'stream')))
        self.root.update()
        plan = w.session.plan
        windows = dict(w.projections)
        self.assertTrue(w.start_projection(('hall', 'stream')))
        self.assertEqual(w.projections, windows)
        w.title.set('Rozpracováno')
        w.text.insert('end', ' další obsah')
        self.root.update()
        w.add_section()
        w.undo()
        w.redo()
        w.change_aspect('hall', '16:9')
        w.rebuild()
        self.assertIs(w.session.plan, plan)
        self.assertIs(w.plan, plan)
        w.thumbnail_clicked(0)
        self.assertEqual(w.session.current_slide_id, plan.slides[0].id)
        w.jump(1)
        position = w.session.current_slide_id
        w.blackout_key(SimpleNamespace(widget=w.text))
        self.assertFalse(w.session.blackout)
        w.blackout_key(SimpleNamespace(widget=w.title_entry))
        self.assertFalse(w.session.blackout)
        w.blackout_key(SimpleNamespace(widget=w.preview))
        self.assertTrue(w.session.blackout)
        for window in windows.values():
            self.assertEqual(window.canvas.find_all(), ())
        w.toggle_blackout()
        self.assertEqual(w.session.current_slide_id, position)
        for window in windows.values():
            self.assertTrue(window.canvas.find_all())
            actual = [window.canvas.itemcget(item, 'text') for item in window.canvas.find_all() if window.canvas.type(item) == 'text']
            expected = [p.text.replace('\t', '    ').replace('\r', '') for p in getattr(plan.slides[1], window.output).pieces]
            self.assertEqual(actual, expected)
            window.window.geometry('500x300+0+0')
        self.root.update()
        self.assertEqual(w.session.current_slide_id, position)
        w.stop_projection('hall')
        self.assertIs(w.session.plan, plan)
        self.assertTrue(w.start_projection(('hall',)))
        self.assertIs(w.session.plan, plan)
        w.projections['stream'].window.destroy()
        self.assertEqual(set(w.projections), {'hall'})
        w.stop_projection()
        self.assertIsNone(w.session)
        self.assertEqual(w.projections, {})
        w.stop_projection()
        self.assertTrue(w.start_projection(('stream',)))
        self.assertEqual(w.session.plan.source, w.document)
        self.assertNotEqual(w.session.plan, plan)

    def test_monitor_conflicts_disconnect_and_invalid_plan(self):
        w = self.w
        w.monitor_choices['stream'].set('A')
        self.assertFalse(w.start_projection(('hall', 'stream')))
        self.assertIsNone(w.session)
        self.assertTrue(w.start_projection(('hall',)))
        self.assertFalse(w.start_projection(('stream',)))
        w.monitor_choices['stream'].set('missing')
        self.assertFalse(w.start_projection(('stream',)))
        self.monitors.clear()
        w.refresh_monitors_now()
        self.assertEqual(w.projections, {})
        self.assertIsNone(w.session)
        self.monitors.append(Monitor('A', 0, 0, 800, 600))
        w.title.set('X'*10000)
        self.assertFalse(w.start_projection(('hall',)))
        self.assertIsNone(w.session)

    def test_two_movable_windows_on_one_monitor_and_fullscreen_conflict(self):
        w = self.w
        w.monitor_choices['stream'].set('A')
        w.projection_controls.fullscreen = {'hall': False, 'stream': False}
        w.text.insert('1.0', 'Obsah obou testovacích oken')
        self.root.update()
        self.assertTrue(w.start_projection(('hall', 'stream')))
        self.root.update()
        plan = w.session.plan
        for field, window in w.projections.items():
            self.assertFalse(window.window.overrideredirect())
            self.assertLess(window.canvas.winfo_width(), self.monitors[0].width)
            window.window.geometry('320x220+70+90')
        self.root.update()
        w.jump(1)
        for window in w.projections.values():
            self.assertTrue(window.canvas.find_all())
        w.toggle_blackout()
        for window in w.projections.values():
            self.assertEqual(window.canvas.find_all(), ())
        w.toggle_blackout()
        w.projections['hall'].window.destroy()
        self.assertEqual(set(w.projections), {'stream'})
        self.assertIs(w.session.plan, plan)
        self.assertTrue(w.start_projection(('hall',)))
        w.stop_projection()
        w.projection_controls.fullscreen['hall'] = True
        self.assertFalse(w.start_projection(('hall', 'stream')))
        self.assertIsNone(w.session)

    def test_actual_monitor_enumeration_and_root_lifecycle(self):
        self.assertTrue(monitors(self.root))
        self.assertTrue(self.w.start_projection(('hall', 'stream')))
        windows = [p.window for p in self.w.projections.values()]
        self.root.destroy()
        self.assertIsNone(self.w.session)
        self.assertEqual(self.w.projections, {})
        self.assertIsNone(self.w.monitor_job)
        for window in windows:
            self.assertNotIn(window, self.root.children.values())
        self.root = tk.Tk()
        self.root.withdraw()

    def test_signed_placement_text_key_and_window_close(self):
        w = self.w
        self.assertTrue(w.start_projection(('hall', 'stream')))
        self.root.update()
        stream = w.projections['stream']
        self.assertEqual((stream.window.winfo_x(), stream.window.winfo_y()), (-640, -100))
        self.assertEqual((stream.canvas.winfo_width(), stream.canvas.winfo_height()), (640, 360))
        self.root.deiconify()
        self.root.update()
        self.root.lift()
        w.text.focus_force()
        self.root.update()
        w.text.event_generate('<KeyPress-b>')
        self.root.update()
        self.assertIn('b', w.text.get('1.0', 'end-1c'))
        self.assertFalse(w.session.blackout)
        stream.window.event_generate('<KeyPress-b>')
        self.root.update()
        # Explicit handler covers shortcut independent of focus ownership.
        w.blackout_key(SimpleNamespace(widget=stream.canvas))
        script = stream.window.protocol('WM_DELETE_WINDOW')
        self.root.tk.call(script)
        self.assertEqual(set(w.projections), {'hall'})
        w.projections['hall'].window.destroy()
        self.assertIsNone(w.session)

    @unittest.skipUnless(sys.platform == 'win32', 'Windows native geometry')
    def test_physical_window_and_canvas_cover_each_available_monitor(self):
        actual = monitors(self.root)
        user = ctypes.windll.user32
        user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user.GetParent.argtypes = [wintypes.HWND]
        user.GetParent.restype = wintypes.HWND
        self.monitors[:] = actual
        for monitor in actual:
            self.w.monitor_choices['hall'].set(monitor.id)
            self.assertTrue(self.w.start_projection(('hall',)))
            self.root.update()
            window = self.w.projections['hall']
            hwnd = user.GetParent(window.window.winfo_id()) or window.window.winfo_id()
            rect = wintypes.RECT()
            self.assertTrue(user.GetWindowRect(hwnd, ctypes.byref(rect)))
            self.assertEqual((rect.left, rect.top, rect.right, rect.bottom),
                             (monitor.x, monitor.y, monitor.x+monitor.width, monitor.y+monitor.height))
            self.assertEqual((window.canvas.winfo_width(), window.canvas.winfo_height()),
                             (monitor.width, monitor.height))
            # Repeated UI updates must not restore Tk's stale placement.
            self.w.jump(1)
            self.root.update()
            self.assertTrue(user.GetWindowRect(hwnd, ctypes.byref(rect)))
            self.assertEqual((rect.left, rect.top), (monitor.x, monitor.y))
            self.w.stop_projection()


if __name__ == '__main__':
    unittest.main()

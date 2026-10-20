"""Calibration is detached, uses real output coordinates, and never publishes drafts."""
import tempfile
import tkinter as tk
import unittest
import json
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from presentationpresenter.camera_settings_window import CameraSettingsWindow, fit_camera
from presentationpresenter.settings import AppSettings, load_settings, save_settings
from presentationpresenter.domain import CameraRegion, Aspect
from presentationpresenter.ui import MainWindow
from presentationpresenter.session import ProjectionSession

class CameraSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.w = MainWindow(self.root, AppSettings(), recovery_dir=Path(self.temp.name)/'recovery')
        self.root.after_cancel(self.w.autosave_job)
        self.w.autosave_job = None
        self.errors = []
        self.root.report_callback_exception = lambda *e: self.errors.append(e)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.temp.cleanup()
        self.assertFalse(self.errors)

    def test_slider_constraints_and_cancel_keep_document(self):
        w = self.w
        original = w.document
        dialog = CameraSettingsWindow(w)
        dialog.values['x'].set(90)
        dialog.changed('x')
        self.assertEqual(dialog.camera.x, .5)
        dialog.values['width'].set(30)
        dialog.changed('width')
        self.assertEqual(dialog.camera.x, .7)
        dialog.values['x'].set(70)
        dialog.changed('x')
        self.assertEqual(dialog.camera.x, .7)
        self.assertEqual(dialog.camera.width, .3)
        dialog.values['width'].set(90)
        dialog.changed('width')
        self.assertEqual(dialog.camera.width, .9)
        self.assertEqual(dialog.camera.x, .1)
        dialog.redraw()
        self.root.update()
        self.assertTrue(dialog.canvas.find_withtag('camera_border'))
        self.assertTrue(dialog.canvas.find_withtag('camera_gap'))
        self.assertEqual(w.document, original)
        dialog.close()
        self.assertEqual(w.document, original)

    def test_resize_edges_center_and_full_size_roundtrip(self):
        for previous, field, value, expected in (
                (CameraRegion(), 'width', 30, (.7, .5, .3, .5)),
                (CameraRegion(), 'height', 30, (.5, .7, .5, .3)),
                (CameraRegion(0, 0, .3, .3), 'width', 60, (0, 0, .6, .3)),
                (CameraRegion(0, 0, .3, .3), 'height', 60, (0, 0, .3, .6)),
                (CameraRegion(.3, .3, .4, .4), 'width', 60, (.2, .3, .6, .4)),
                (CameraRegion(.3, .3, .4, .4), 'height', 20, (.3, .4, .4, .2)),
                (CameraRegion(.1, .2, .2, .2), 'width', 100, (0, .2, .4, .2))):
            values = {key: getattr(previous, key)*100 for key in ('x', 'y', 'width', 'height', 'gap')}
            values[field] = value
            result = fit_camera(values, field, previous)
            self.assertEqual((result.x, result.y, result.width, result.height), expected)
        dialog = CameraSettingsWindow(self.w)
        for field in ('width', 'height'):
            dialog.values[field].set(100)
            dialog.changed(field)
            self.root.update()  # Includes deferred callbacks from the position Scale.
            dialog.values[field].set(30)
            dialog.changed(field)
            self.root.update()
        self.assertEqual(dialog.camera, CameraRegion(.7, .7, .3, .3, .02))
        dialog.close()
        self.w.document = replace(self.w.document, stream=replace(self.w.document.stream, camera=CameraRegion(.3, .3, .4, .4)))
        dialog = CameraSettingsWindow(self.w)
        dialog.values['width'].set(40.5)
        dialog.changed('width')
        self.root.update()
        self.assertAlmostEqual(dialog.camera.x+dialog.camera.width/2, .5)
        self.assertAlmostEqual(dialog.camera.width, .405)
        self.assertAlmostEqual(dialog.values['x'].get(), 29.75)
        dialog.close()

    def test_apply_once_undo_live_isolation_and_portability(self):
        w = self.w
        w.text.insert('end', 'Obsah prezentace')
        w.finish_editing()
        w.rebuild()
        original, settings = w.document, w.settings
        w.session = ProjectionSession.confirm(w.plan)
        live = w.session
        dialog = CameraSettingsWindow(w)
        dialog.values['width'].set(35)
        dialog.changed('width')
        with patch('presentationpresenter.camera_settings_window.save_settings') as save:
            self.assertTrue(dialog.apply(False))
            save.assert_not_called()
        self.assertEqual(w.document.stream.camera.width, .35)
        self.assertEqual(w.settings, settings)
        self.assertIs(w.session, live)
        from presentationpresenter.storage import save as save_doc, load
        path = Path(self.temp.name)/'camera.ppres'
        save_doc(path, w.document)
        self.assertEqual(load(path).stream.camera, w.document.stream.camera)
        w.undo()
        self.assertEqual(w.document, original)

    def test_save_defaults_new_documents_old_settings_and_failed_save(self):
        w = self.w
        original = w.document
        dialog = CameraSettingsWindow(w)
        dialog.values['height'].set(30)
        dialog.changed('height')
        with patch('presentationpresenter.camera_settings_window.save_settings', side_effect=OSError('disk full')), \
             patch('presentationpresenter.camera_settings_window.messagebox.showerror'):
            self.assertFalse(dialog.apply(True))
        self.assertEqual(w.document, original)
        path = Path(self.temp.name)/'settings.json'
        with patch('presentationpresenter.camera_settings_window.save_settings', side_effect=lambda s: save_settings(s, path)):
            self.assertTrue(dialog.apply(True))
        self.assertEqual(load_settings(path).default_camera().height, .3)
        self.assertEqual(w.default_document().stream.camera.height, .3)
        self.assertEqual(original.stream.camera.height, .5)
        path.write_text('{}', encoding='utf8')
        self.assertEqual(load_settings(path).default_camera(), CameraRegion())
        path.write_text(json.dumps({'camera_x': .9, 'camera_width': .8}), encoding='utf8')
        self.assertEqual(load_settings(path), AppSettings())

    def test_calibration_window_controls_and_cleanup(self):
        w = self.w
        original = w.document
        w.show_camera_settings()
        dialog = w.camera_settings_window
        dialog.fullscreen.set(False)
        dialog.toggle_test()
        self.root.update()
        self.assertIsNotNone(dialog.test)
        self.assertIsNone(w.session)
        self.assertFalse(w.projections)
        self.assertFalse(w.start_projection(('hall',)))
        self.assertEqual(w.document, original)
        before = dialog.test.canvas.coords('camera_border')
        dialog.values['height'].set(25)
        dialog.changed('height')
        dialog.redraw()
        self.assertTrue(dialog.test.canvas.find_withtag('camera_border'))
        after = dialog.test.canvas.coords('camera_border')
        self.assertAlmostEqual(after[3]-after[1], (before[3]-before[1])/2)
        test_window = dialog.test.window
        test_window.destroy()
        self.assertIsNone(dialog.test)
        dialog.toggle_test()
        dialog.close()
        self.assertIsNone(dialog.test)
        self.assertIsNone(dialog.monitor_job)
        self.assertIsNone(dialog.redraw_job)
        self.assertEqual(w.document, original)

    def test_disconnect_stops_only_calibration_and_live_blocks_test(self):
        w = self.w
        dialog = CameraSettingsWindow(w)
        dialog.fullscreen.set(False)
        dialog.toggle_test()
        self.assertIsNotNone(dialog.test)
        inventory = w.monitor_inventory
        w.monitor_inventory = []
        dialog.refresh_monitors()
        self.assertIsNone(dialog.test)
        w.monitor_inventory = inventory
        dialog.refresh_monitors()
        w.session = ProjectionSession.confirm(w.plan)
        dialog.toggle_test()
        self.assertIsNone(dialog.test)
        self.assertIsNotNone(w.session)
        dialog.close()

    def test_both_aspects_calibration_border_matches_config(self):
        for aspect in (Aspect.STANDARD, Aspect.WIDE):
            self.w.document = replace(self.w.document, stream=replace(self.w.document.stream, aspect=aspect))
            dialog = CameraSettingsWindow(self.w)
            self.root.update()
            dialog.redraw()
            canvas = dialog.canvas
            x0, y0, x1, y1 = canvas.coords('slide_border')
            a, b, c, d = canvas.coords('camera_border')
            self.assertAlmostEqual((x1-x0)/(y1-y0), 4/3 if aspect == Aspect.STANDARD else 16/9)
            self.assertAlmostEqual((a-x0)/(x1-x0), .5)
            self.assertAlmostEqual((b-y0)/(y1-y0), .5)
            self.assertAlmostEqual((c-a)/(x1-x0), .5)
            self.assertAlmostEqual((d-b)/(y1-y0), .5)
            dialog.close()

    def test_invalid_layout_blocks_apply_and_legacy_uses_saved_default(self):
        w = self.w
        original = w.document
        dialog = CameraSettingsWindow(w)
        with patch('presentationpresenter.camera_settings_window.paginate', side_effect=ValueError('Text se nevejde')), \
             patch('presentationpresenter.camera_settings_window.messagebox.showerror'), \
             patch('presentationpresenter.camera_settings_window.save_settings') as save:
            self.assertFalse(dialog.apply(True))
            save.assert_not_called()
        self.assertEqual(w.document, original)
        dialog.close()
        w.settings = replace(w.settings, camera_height=.3)
        path = Path(self.temp.name)/'legacy.json'
        path.write_text(json.dumps([{'link': 'Jan', 'text': 'Obsah'}]), encoding='utf8')
        with patch('presentationpresenter.ui.filedialog.askopenfilename', return_value=str(path)), \
             patch('presentationpresenter.ui.messagebox.showwarning'):
            w.import_document()
        self.assertEqual(w.document.stream.camera.height, .3)

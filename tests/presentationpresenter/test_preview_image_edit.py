from dataclasses import replace
import tempfile
import json
from pathlib import Path
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from presentationpresenter.domain import ImagePlacement, ImageSection, OutputConfig, Aspect, CameraRegion
from presentationpresenter.layout import Rect, geometry, LayoutError
from presentationpresenter.preview_image_edit import resized_box
from presentationpresenter.settings import AppSettings, load_settings, save_settings
from presentationpresenter.session import ProjectionSession
from presentationpresenter.ui import MainWindow
from tests.presentationpresenter.test_image_composition import source
from presentationpresenter.composition import camera_core


class ResizeTests(unittest.TestCase):
    def test_direct_edit_preference_old_invalid_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'settings.json'
            path.write_text(json.dumps({'geometry': '900x650'}), encoding='utf-8')
            self.assertTrue(load_settings(path).direct_image_edit)
            self.assertEqual(load_settings(path).geometry, '900x650')
            save_settings(AppSettings(direct_image_edit=True), path)
            self.assertTrue(load_settings(path).direct_image_edit)
            save_settings(AppSettings(direct_image_edit=False), path)
            self.assertFalse(load_settings(path).direct_image_edit)
            path.write_text(json.dumps({'direct_image_edit': 'false'}), encoding='utf-8')
            self.assertTrue(load_settings(path).direct_image_edit)

    def test_camera_limit_keeps_opposite_corner(self):
        for aspect in Aspect:
            config = OutputConfig(aspect, CameraRegion())
            box = Rect(50, 400, 200, 100)
            core = camera_core(geometry(config)[2])
            result = resized_box(box, 'es', 2000, 1000, config)
            self.assertFalse(result.intersects(core))
            self.assertAlmostEqual(result.x, box.x)
            self.assertAlmostEqual(result.y, box.y)
            self.assertAlmostEqual(result.width/result.height, 2)

    def test_four_fixed_corners_and_bounds(self):
        config = OutputConfig(Aspect.WIDE)
        box = Rect(200, 160, 240, 120)
        for corner in ('wn', 'en', 'ws', 'es'):
            for dx, dy in ((80, 40), (-80, -40), (5000, 5000), (-5000, -5000)):
                result = resized_box(box, corner, dx, dy, config)
                self.assertAlmostEqual(result.width/result.height, 2)
                self.assertAlmostEqual(result.x+result.width if corner[0] == 'w' else result.x,
                                       box.x+box.width if corner[0] == 'w' else box.x)
                self.assertAlmostEqual(result.y+result.height if corner[1] == 'n' else result.y,
                                       box.y+box.height if corner[1] == 'n' else box.y)
                self.assertGreater(result.width, 0)
                self.assertGreaterEqual(result.x, -1e-6)
                self.assertGreaterEqual(result.y, -1e-6)
                self.assertLessEqual(result.x+result.width, 1280+1e-6)
                self.assertLessEqual(result.y+result.height, 720+1e-6)


class PreviewImageEditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)
        self.owner = MainWindow(self.root, AppSettings(direct_image_edit=False), recovery_dir=self.tmp.name)
        doc = source(count=2, text='Krátký text pro obtékání.')
        section = doc.sections[0]
        section = replace(section, break_before=False, images=tuple(
            replace(item, hall=ImagePlacement(.12+i*.35, .42, .2)) for i, item in enumerate(section.images)))
        self.owner.commit(replace(doc, sections=(section,), black_start=False))
        self.owner.rebuild()
        self.owner.jump(0)
        self.root.geometry('1100x800')
        self.root.update()
        self.edit = self.owner.preview_image_edit
        self.owner.image_edit_button.invoke()
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.tmp.cleanup()
        self.assertEqual(self.errors, [])

    def point(self, box, corner=False):
        context = self.edit.context()
        scale, (ox, oy) = context[2:4]
        return SimpleNamespace(x=ox+(box.x+box.width*(1 if corner else .5))*scale,
                               y=oy+(box.y+box.height*(1 if corner else .5))*scale)

    def test_preference_applies_immediately_and_survives_restart(self):
        owner, edit = self.owner, self.edit
        path = Path(self.tmp.name) / 'settings.json'
        self.assertEqual(owner.direct_image_edit_check.cget('text'), 'Úprava obrázků napřímo')
        self.assertFalse(int(owner.direct_image_edit_check.cget('indicatoron')))
        with patch('presentationpresenter.ui.save_settings', side_effect=lambda settings: save_settings(settings, path)):
            owner.direct_image_edit_check.invoke()
        self.assertTrue(edit.active)
        self.assertFalse(edit.enabled)
        self.assertEqual(str(owner.image_edit_button.cget('state')), 'disabled')
        original = owner.document
        image = edit.context()[1][0]
        start = self.point(image.box)
        edit.press(start)
        edit.motion(SimpleNamespace(x=start.x+10, y=start.y))
        edit.escape()
        edit.escape()
        self.assertTrue(edit.active)
        self.assertEqual(owner.document, original)
        fresh_root = tk.Tk()
        try:
            fresh = MainWindow(fresh_root, load_settings(path), recovery_dir=Path(self.tmp.name)/'fresh')
            self.assertTrue(fresh.preview_image_edit.active)
            self.assertEqual(str(fresh.image_edit_button.cget('state')), 'disabled')
        finally:
            fresh_root.destroy()
        with patch('presentationpresenter.ui.save_settings'):
            owner.direct_image_edit_check.invoke()
        self.assertFalse(edit.active)
        self.assertEqual(str(owner.image_edit_button.cget('state')), 'normal')
        owner.image_edit_button.invoke()
        self.assertTrue(edit.active)

    def test_preference_save_failure_restores_old_value(self):
        with patch('presentationpresenter.ui.save_settings', side_effect=OSError('QA')), \
             patch('presentationpresenter.ui.messagebox.showerror') as error:
            self.owner.direct_image_edit_check.invoke()
        error.assert_called_once()
        self.assertFalse(self.owner.direct_image_edit.get())
        self.assertFalse(self.owner.settings.direct_image_edit)
        self.assertTrue(self.edit.enabled)  # Existing manually enabled mode remains unchanged.

    def test_move_is_one_undo_and_leaves_peer_and_live_unchanged(self):
        owner, edit = self.owner, self.edit
        original = owner.document
        owner.session = ProjectionSession.confirm(owner.plan)
        owner.view_version.set('draft')
        live = owner.session.plan
        context = edit.context()
        image, peer = context[1]
        start = self.point(image.box)
        end = SimpleNamespace(x=start.x+30*context[2], y=start.y+10*context[2])
        history = len(owner.history.past)
        edit.press(start)
        edit.motion(end)
        self.assertEqual(owner.document, original)
        self.assertTrue(owner.preview.find_withtag('image-edit'))
        edit.release(end)
        self.assertEqual(len(owner.history.past), history+1)
        after = edit.context()[1]
        self.assertAlmostEqual(after[0].box.x, image.box.x+30)
        self.assertEqual(after[1].box, peer.box)
        self.assertIs(owner.session.plan, live)
        owner.undo()
        self.assertEqual(owner.document, original)
        owner.redo()
        self.assertNotEqual(owner.document, original)

    def test_resize_and_escape(self):
        edit, owner = self.edit, self.owner
        original = owner.document
        image = edit.context()[1][0]
        start = self.point(image.box, True)
        edit.press(start)
        end = SimpleNamespace(x=start.x-25, y=start.y-10)
        edit.motion(end)
        edit.escape()
        self.assertEqual(owner.document, original)
        edit.press(start)
        edit.release(end)
        box = edit.context()[1][0].box
        self.assertLess(box.width, image.box.width)
        self.assertAlmostEqual(box.width/box.height, image.box.width/image.box.height)
        self.assertAlmostEqual(box.x, image.box.x)
        self.assertAlmostEqual(box.y, image.box.y)

    def test_stream_detaches_and_does_not_move_hall(self):
        owner, edit = self.owner, self.edit
        original = owner.document.sections[0]
        owner.toggle_preview_output()
        context = edit.context()
        image = context[1][0]
        start = self.point(image.box, True)
        edit.press(start)
        edit.release(SimpleNamespace(x=start.x-15, y=start.y-8))
        section = owner.document.sections[0]
        self.assertFalse(section.stream_linked)
        self.assertEqual([i.hall for i in section.images], [i.hall for i in original.images])
        self.assertTrue(all(i.stream for i in section.images))

    def test_switch_output_stale_drag_and_failed_layout(self):
        edit, owner = self.edit, self.owner
        image = edit.context()[1][0]
        start = self.point(image.box)
        original = owner.document
        edit.press(start)
        owner.toggle_preview_output()
        self.assertIsNone(edit.drag)
        edit.release(start)
        self.assertEqual(owner.document, original)
        owner.toggle_preview_output()
        edit.press(start)
        with patch('presentationpresenter.preview_image_edit.paginate', side_effect=LayoutError('QA no space')):
            edit.release(SimpleNamespace(x=start.x+20, y=start.y))
        self.assertEqual(owner.document, original)
        self.assertIn('QA no space', owner.status.get())

    def test_legacy_image_section_and_noop(self):
        owner, edit = self.owner, self.edit
        doc = owner.document
        section = ImageSection('Samostatný obrázek', doc.media[0].id, break_after=False)
        owner.commit(replace(doc, sections=(section,)))
        owner.rebuild()
        owner.jump(0)
        original = owner.document
        image = edit.context()[1][0]
        start = self.point(image.box)
        edit.press(start)
        edit.release(start)
        self.assertEqual(owner.document, original)
        start = self.point(image.box, True)
        edit.press(start)
        edit.release(SimpleNamespace(x=start.x-30, y=start.y-20))
        self.assertEqual(owner.document.sections[0].id, section.id)
        self.assertTrue(owner.document.sections[0].images[0].hall)


if __name__ == '__main__':
    unittest.main()

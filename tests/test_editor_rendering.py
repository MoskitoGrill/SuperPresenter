"""Rendering regressions without requiring a desktop Tk runtime."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from superpresenter.ui.collection_qr_editor import CollectionQREditor
from superpresenter.ui.projection_editor import ProjectionEditor


class EditorRenderingTests(unittest.TestCase):
    def test_qr_wheel_fine_steps_and_limits(self):
        editor = CollectionQREditor.__new__(CollectionQREditor)
        value = Mock()
        editor.values = {'x_pct': value, 'size_pct': value}
        value.get.return_value = '50,00'
        editor.adjust_slider('x_pct', SimpleNamespace(delta=120, state=0))
        value.set.assert_called_with('50.10')
        editor.adjust_slider('x_pct', SimpleNamespace(delta=-30, state=1))
        value.set.assert_called_with('49.99')
        value.get.return_value = '100'
        editor.adjust_slider('x_pct', SimpleNamespace(delta=120, state=0))
        value.set.assert_called_with('100.00')
        value.get.return_value = '1'
        editor.adjust_slider('size_pct', SimpleNamespace(delta=-120, state=0))
        value.set.assert_called_with('1.00')
        value.get.return_value = '0'
        editor.adjust_slider('x_pct', SimpleNamespace(delta=-120, state=0))
        value.set.assert_called_with('0.00')
        value.set.reset_mock()
        for invalid in ('', 'abc', 'nan'):
            value.get.return_value = invalid
            editor.adjust_slider('x_pct', SimpleNamespace(delta=120, state=0))
        value.set.assert_not_called()

    def make_qr_editor(self):
        editor = CollectionQREditor.__new__(CollectionQREditor)
        editor.win = Mock()
        editor.canvas = Mock()
        editor.canvas.winfo_width.return_value = 640
        editor.canvas.winfo_height.return_value = 360
        editor.canvas.find_withtag.return_value = ()
        editor.style = {'canvas': {}, 'widgets': [], 'fonts': {}}
        editor.hall_rows = 8
        editor.status = Mock()
        editor.image = object()
        editor._background_size = editor._photo_key = editor._draw_job = None
        editor.current = Mock(return_value={'size_pct': 30, 'x_pct': 0, 'y_pct': 0})
        return editor

    @patch('superpresenter.ui.collection_qr_editor.ImageTk.PhotoImage')
    @patch('superpresenter.ui.collection_qr_editor.render_image')
    def test_position_reuses_image_and_background(self, render, photo):
        editor = self.make_qr_editor()
        editor.draw()
        editor.canvas.find_withtag.return_value = (1,)
        editor.current.return_value['x_pct'] = 100
        editor.current.return_value['y_pct'] = 100
        editor.draw()
        self.assertEqual(render.call_count, 1)
        self.assertEqual(photo.call_count, 1)
        self.assertEqual(editor.canvas.create_text.call_count, 8)
        self.assertEqual(editor.canvas.create_image.call_count, 1)
        editor.canvas.coords.assert_called_with('qr', 532.0, 252.0)
        editor.current.return_value['size_pct'] = 40
        editor.draw()
        self.assertEqual(render.call_count, 2)
        editor.image = object()
        editor.draw()
        self.assertEqual(render.call_count, 3)
        editor.canvas.winfo_width.return_value = 800
        editor.canvas.winfo_height.return_value = 450
        editor.draw()
        self.assertEqual(editor.canvas.create_text.call_count, 16)
        self.assertEqual(render.call_count, 4)

    def test_changes_are_combined_and_pending_draw_is_cancelled(self):
        editor = self.make_qr_editor()
        editor.win.after.return_value = 'job'
        editor.schedule_draw()
        editor.schedule_draw()
        editor.win.after.assert_called_once()
        editor.draw = Mock()
        editor._scheduled_draw()
        editor.draw.assert_called_once()
        editor.schedule_draw()
        editor.cancel()
        editor.win.after_cancel.assert_called_once_with('job')

    def test_moving_body_does_not_repeat_layout_work(self):
        editor = ProjectionEditor.__new__(ProjectionEditor)
        editor.canvas = Mock()
        editor.canvas.winfo_width.return_value = 800
        editor.body = Mock()
        editor.body.winfo_reqwidth.return_value = 600
        editor.body.winfo_reqheight.return_value = 1000
        editor.body_id = 1
        editor.center_body()
        editor.center_body()
        editor.canvas.configure.assert_called_once()
        editor.body.winfo_reqheight.return_value = 1200
        editor.center_body()
        self.assertEqual(editor.canvas.configure.call_count, 2)

    def test_card_compacts_preview_when_window_hits_screen_limit(self):
        editor = ProjectionEditor.__new__(ProjectionEditor)
        editor.win = Mock()
        editor.win.winfo_exists.return_value = True
        editor.win.winfo_height.return_value = 820
        editor.win.winfo_width.return_value = 600
        editor.win.winfo_screenheight.return_value = 900
        editor.canvas = Mock()
        editor.canvas.winfo_height.return_value = 550
        preview = Mock()
        preview.master.winfo_reqheight.return_value = 630
        preview.cget.return_value = 180
        editor.cards = [{'preview': preview}]
        editor._fit_visible_card()
        preview.configure.assert_called_once_with(height=76)
        editor.win.geometry.assert_not_called()

    def test_card_grows_window_without_compacting_when_space_available(self):
        editor = ProjectionEditor.__new__(ProjectionEditor)
        editor.win = Mock()
        editor.win.winfo_exists.return_value = True
        editor.win.winfo_height.return_value = 800
        editor.win.winfo_width.return_value = 600
        editor.win.winfo_screenheight.return_value = 1080
        editor.canvas = Mock()
        editor.canvas.winfo_height.return_value = 550
        preview = Mock()
        preview.master.winfo_reqheight.return_value = 630
        editor.cards = [{'preview': preview}]
        editor._fit_visible_card()
        preview.configure.assert_not_called()
        editor.win.geometry.assert_called_once_with('600x904')

    def test_frame_clearance_can_shrink_preview_below_old_minimum(self):
        editor = ProjectionEditor.__new__(ProjectionEditor)
        editor.win = Mock()
        editor.win.winfo_exists.return_value = True
        editor.win.winfo_height.return_value = 820
        editor.win.winfo_width.return_value = 600
        editor.win.winfo_screenheight.return_value = 900
        editor.canvas = Mock()
        editor.canvas.winfo_height.return_value = 470
        preview = Mock()
        preview.master.winfo_reqheight.return_value = 470
        preview.cget.return_value = 60
        editor.cards = [{'preview': preview}]
        editor._fit_visible_card()
        preview.configure.assert_called_once_with(height=36)
        editor.win.geometry.assert_not_called()

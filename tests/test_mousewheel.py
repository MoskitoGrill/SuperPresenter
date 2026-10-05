import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from superpresenter.ui.mousewheel import bind_canvas_wheel, scroll_widget


class MouseWheelTests(unittest.TestCase):
    def test_axes_direction_and_small_deltas(self):
        widget = Mock()
        scroll_widget(widget, SimpleNamespace(delta=-30, state=0))
        widget.yview_scroll.assert_called_once_with(1, 'units')
        widget.xview_scroll.assert_not_called()
        scroll_widget(widget, SimpleNamespace(delta=240, state=1))
        widget.xview_scroll.assert_called_once_with(-2, 'units')
        scroll_widget(widget, SimpleNamespace(delta=-120, state=0), horizontal=True)
        widget.xview_scroll.assert_called_with(1, 'units')

    def test_canvas_scroll_is_scoped_to_pointer(self):
        canvas = Mock()
        canvas.winfo_toplevel.return_value = Mock()
        handler = bind_canvas_wheel(canvas)
        child = Mock(master=canvas)
        child.winfo_class.return_value = 'Label'
        canvas.winfo_containing.return_value = child
        event = SimpleNamespace(delta=-120, state=1, x_root=10, y_root=20)
        self.assertEqual(handler(event), 'break')
        canvas.xview_scroll.assert_called_once_with(1, 'units')
        canvas.winfo_containing.return_value = Mock(master=None)
        self.assertIsNone(handler(event))
        self.assertEqual(canvas.xview_scroll.call_count, 1)

    def test_expanding_text_uses_canvas_but_regular_text_keeps_native_scroll(self):
        canvas = Mock()
        handler = bind_canvas_wheel(canvas)
        text = Mock(master=canvas)
        text.winfo_class.return_value = 'Text'
        canvas.winfo_containing.return_value = text
        event = SimpleNamespace(delta=-120, state=0, x_root=10, y_root=20)
        handler(event)
        canvas.yview_scroll.assert_not_called()
        text._scroll_parent_canvas = True
        self.assertEqual(handler(event), 'break')
        canvas.yview_scroll.assert_called_once_with(1, 'units')

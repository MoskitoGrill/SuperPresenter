"""Wheel bindings scoped to a canvas and its descendants."""


def scroll_widget(widget, event, horizontal=False):
    """Shift selects horizontal scrolling; Ctrl retains its usual meaning."""
    delta = getattr(event, 'delta', 0)
    if delta:
        steps = max(1, int(abs(delta) / 120))
        view = widget.xview_scroll if horizontal or getattr(event, 'state', 0) & 1 else widget.yview_scroll
        view(-steps if delta > 0 else steps, 'units')
    return 'break'


def bind_widget_wheel(widget):
    # Run before native class bindings, including for small wheel deltas.
    widget.bind('<MouseWheel>', lambda event: scroll_widget(widget, event))


def bind_canvas_wheel(canvas, callback=None):
    if callback is None:
        callback = lambda event: scroll_widget(canvas, event)
    top = canvas.winfo_toplevel()

    def on_wheel(event):
        widget = canvas.winfo_containing(event.x_root, event.y_root)
        # Text widgets already scroll through their native class binding.
        if (widget is not None and widget.winfo_class() == 'Text'
                and getattr(widget, '_scroll_parent_canvas', False) is not True):
            return
        while widget is not None:
            if widget is canvas:
                callback(event)
                return 'break'
            widget = getattr(widget, 'master', None)

    binding = top.bind('<MouseWheel>', on_wheel, add='+')

    def cleanup(event):
        if event.widget is canvas:
            top.unbind('<MouseWheel>', binding)

    canvas.bind('<Destroy>', cleanup, add='+')
    # Expanding Text fields must use this handler before their native class
    # binding consumes the wheel. Other Text widgets keep native scrolling.
    return on_wheel

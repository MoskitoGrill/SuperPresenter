"""Wheel bindings scoped to a canvas and its descendants."""


def bind_canvas_wheel(canvas, callback):
    top = canvas.winfo_toplevel()

    def on_wheel(event):
        widget = canvas.winfo_containing(event.x_root, event.y_root)
        # Text widgets already scroll through their native class binding.
        if widget is not None and widget.winfo_class() == 'Text':
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

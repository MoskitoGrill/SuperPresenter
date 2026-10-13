"""The same Tk fonts measure and render, in pixels, independent of monitor DPI."""
import tkinter.font as tkfont
from functools import lru_cache
from .domain import TextStyle

class TkMetrics:
    def __init__(self, root, family='Courier New'):
        self.root, self.family = root, family

    @lru_cache(maxsize=64)
    def font(self, style, size):
        return tkfont.Font(root=self.root, family=self.family, size=-size,
                           weight='bold' if style.bold else 'normal',
                           slant='italic' if style.italic else 'roman', underline=style.underline)

    @lru_cache(maxsize=16384)
    def width(self, text, style, size):
        # Canvas text has side bearings/overhang; retain four pixels of ink guard.
        return self.font(style, size).measure(display_text(text)) + (4 if text else 0)

    @lru_cache(maxsize=64)
    def height(self, style, size):
        return self.font(style, size).metrics('linespace')


def draw(canvas, slide, output, metrics, typography, show_camera=True, scale=1, resize_canvas=True):
    """Native-size static preview; no font substitution or layout recalculation."""
    canvas.delete('all')
    canvas.configure(bg='black')
    canvas._pp_image = None
    canvas._pp_images = []
    layout = getattr(slide, output)
    if slide.black or layout is None:
        return
    canvas.configure(scrollregion=(0, 0, layout.width*scale, layout.height*scale))
    if scale == 1 and resize_canvas:
        canvas.configure(width=layout.width, height=layout.height)
    camera_warning = any('zakryje kamera' in warning for warning in layout.warnings)
    if show_camera and layout.camera:
        c = layout.camera
        canvas.create_rectangle(c.x*scale, c.y*scale, (c.x+c.width)*scale, (c.y+c.height)*scale, fill='#181818', outline='#555555')
        if scale > .3 and not camera_warning:
            canvas.create_text((c.x+12)*scale, (c.y+12)*scale, text='Rezerva kamery', anchor='nw', fill='#777777', font=metrics.font(TextStyle(), max(1, round(18*scale))))
    if layout.image_box:
        from PIL import Image, ImageTk
        from .media import decode
        box = layout.image_box
        image = decode(layout.image_locator)
        image = image.resize((max(1, int(box.width*scale)), max(1, int(box.height*scale))), Image.Resampling.LANCZOS)
        canvas._pp_image = ImageTk.PhotoImage(image, master=canvas)
        canvas.create_image((box.x+box.width/2)*scale, (box.y+box.height/2)*scale, image=canvas._pp_image)
    for placed in layout.images:
        from PIL import Image, ImageTk
        from .media import decode
        box = placed.box
        image = decode(placed.locator).resize((max(1, int(box.width*scale)), max(1, int(box.height*scale))), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image, master=canvas)
        canvas._pp_images.append(photo)
        canvas.create_image((box.x+box.width/2)*scale, (box.y+box.height/2)*scale, image=photo)
    for piece in layout.pieces:
        size = max(1, int(piece.font_size*scale))
        if scale < 1:
            # Pixel-rounded small Tk fonts can be wider than scaled geometry.
            # Fit each existing piece without recalculating any line breaks.
            available = max(1, (piece.box.width-4)*scale)
            while size > 1 and metrics.font(piece.style, size).measure(display_text(piece.text)) > available:
                size -= 1
        canvas.create_text((piece.box.x+2)*scale, piece.box.y*scale, text=display_text(piece.text), anchor='nw',
                           font=metrics.font(piece.style, size), fill=piece.style.color)
    if show_camera and layout.camera and camera_warning:
        c = layout.camera
        canvas.create_rectangle(c.x*scale, c.y*scale, (c.x+c.width)*scale, (c.y+c.height)*scale,
                                fill='#ff3333', stipple='gray12', outline='#ff5555', tags='camera-warning')
        if scale > .3:
            canvas.create_text((c.x+8)*scale, (c.y+8)*scale, text='Část obrázku zakryje kamera', anchor='nw',
                               fill='#ffbbbb', font=metrics.font(TextStyle(), max(1, round(18*scale))), tags='camera-warning')


def display_text(text):
    return text.replace('\t', '    ').replace('\r', '')

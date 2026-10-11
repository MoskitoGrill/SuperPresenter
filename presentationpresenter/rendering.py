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


def draw(canvas, slide, output, metrics, typography, show_camera=True):
    """Native-size static preview; no font substitution or layout recalculation."""
    canvas.delete('all')
    canvas.configure(bg='black')
    layout = getattr(slide, output)
    if slide.black or layout is None:
        return
    canvas.configure(scrollregion=(0, 0, layout.width, layout.height), width=layout.width, height=layout.height)
    if show_camera and layout.camera:
        c = layout.camera
        canvas.create_rectangle(c.x, c.y, c.x+c.width, c.y+c.height, fill='#181818', outline='#555555')
        canvas.create_text(c.x+12, c.y+12, text='Rezerva kamery', anchor='nw', fill='#777777', font=metrics.font(TextStyle(), 18))
    for piece in layout.pieces:
        canvas.create_text(piece.box.x+2, piece.box.y, text=display_text(piece.text), anchor='nw',
                           font=metrics.font(piece.style, piece.font_size), fill=piece.style.color)


def display_text(text):
    return text.replace('\t', '    ').replace('\r', '')

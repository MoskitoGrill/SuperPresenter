"""Actual Tk screenshots of mixed content and independent camera overlap."""
import sys
import tempfile
import io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import tkinter as tk
from dataclasses import replace
from PIL import Image, ImageDraw, ImageGrab
from presentationpresenter import media
from presentationpresenter.domain import *
from presentationpresenter.ui import MainWindow
from presentationpresenter.settings import AppSettings
from presentationpresenter.composition import normalize
from presentationpresenter.composition import CAMERA_OVERLAP_LEFT
from presentationpresenter.layout import Rect, geometry
from presentationpresenter.projection import configure_dpi

def sample(size, color):
    image = Image.new('RGB', size, color)
    ink = ImageDraw.Draw(image)
    ink.rectangle((10, 10, size[0]-10, size[1]-10), outline='white', width=6)
    r = min(size)*.35
    x, y = size[0]/2, size[1]/2
    ink.ellipse((x-r, y-r, x+r, y+r), outline='white', width=8)
    raw = io.BytesIO()
    image.save(raw, 'PNG')
    return media.from_bytes(raw.getvalue())

configure_dpi()
folder = Path(__file__).parent/'previews'
folder.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as directory:
    root = tk.Tk()
    root.withdraw()
    w = MainWindow(root, AppSettings(), recovery_dir=Path(directory)/'recovery')
    a, b = sample((600, 400), '#467ba2'), sample((600, 300), '#b57828')
    _, _, camera, _ = geometry(w.document.stream)
    width = 300+camera.height*CAMERA_OVERLAP_LEFT
    overlap = normalize(Rect(camera.x-300, camera.y+60, width, width*2/3), w.document.stream)
    images = (ImageItem(a.id, ImagePlacement(.65, .2, .3), overlap, repeat=True),
              ImageItem(b.id, ImagePlacement(.65, .65, .25), ImagePlacement(.05, .1, .22), repeat=False))
    section = TextSection('Text a dva obrázky', (TextBlock((TextRun('Text obtéká obdélníky obrázků. Sál a stream mají stejné části textu, ale vlastní zalomení. ' * 15),)),),
                          images=images, stream_linked=False, break_after=False, break_before=True)
    w.commit(replace(w.document, sections=(section,), media=(a, b)))
    w.rebuild()
    w.edit_images()
    editor = w.image_editor
    editor.window.geometry('1120x780+0+0')
    for output in ('hall', 'stream'):
        editor.output.set(output)
        editor.refresh()
        editor.window.lift()
        root.update()
        x, y = editor.window.winfo_rootx(), editor.window.winfo_rooty()
        ImageGrab.grab(bbox=(x, y, x+editor.window.winfo_width(), y+editor.window.winfo_height()), all_screens=True).save(folder/f'mixed_{output}.png')
    editor.page = 1
    editor.refresh()
    root.update()
    x, y = editor.window.winfo_rootx(), editor.window.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x+editor.window.winfo_width(), y+editor.window.winfo_height()), all_screens=True).save(folder/'mixed_continuation.png')
    root.destroy()

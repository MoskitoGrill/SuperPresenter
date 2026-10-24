"""Actual Tk raster previews; isolated recovery, no preference writes."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import tkinter as tk
from PIL import Image, ImageDraw, ImageGrab
from presentationpresenter.ui import MainWindow
from presentationpresenter.settings import AppSettings
from presentationpresenter.projection import configure_dpi

configure_dpi()
folder = Path(__file__).parent/'previews'
folder.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as directory:
    source = Path(directory)/'image.png'
    image = Image.new('RGB', (900, 600), '#e5b56a')
    ink = ImageDraw.Draw(image)
    ink.ellipse((260, 110, 640, 490), fill='#385c7c', outline='white', width=10)
    ink.rectangle((20, 20, 880, 580), outline='#442020', width=12)
    image.save(source)
    root = tk.Tk()
    w = MainWindow(root, AppSettings(), recovery_dir=Path(directory)/'recovery')
    root.geometry('1280x900+0+0')
    w.insert_image(source)
    source.unlink()
    w.jump(next(i for i, slide in enumerate(w.plan.slides) if slide.hall and slide.hall.images))
    for output in ('hall', 'stream'):
        w.output.set(output)
        w.render_preview()
        root.update()
        root.lift()
        root.update()
        x, y = root.winfo_rootx(), root.winfo_rooty()
        ImageGrab.grab(bbox=(x, y, x+root.winfo_width(), y+root.winfo_height()), all_screens=True).save(folder/f'pp6_{output}.png')
    root.destroy()

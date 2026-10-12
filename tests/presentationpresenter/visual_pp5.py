"""Actual Tk views, no user preference writes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import tkinter as tk
import time
from PIL import ImageGrab
from presentationpresenter.ui import MainWindow
from presentationpresenter.settings import AppSettings
from presentationpresenter.projection import configure_dpi

configure_dpi()
root = tk.Tk()
w = MainWindow(root, AppSettings())
root.geometry('1280x900+0+0')
w.text.insert('1.0', 'První promítaná věta.\nDalší odstavec živé prezentace.')
root.update()
w.projection_controls.fullscreen['hall'] = False
assert w.start_projection(('hall',))
w.jump(1)
w.text.insert('1.0', 'Rozpracovaná oprava před původním začátkem.\n')
root.update()
w.rebuild()
folder = Path(__file__).parent / 'previews'
for window in w.projections.values():
    window.window.withdraw()
for version in ('live', 'draft'):
    w.view_version.set(version)
    w.switch_version()
    root.lift()
    root.update()
    time.sleep(.5)
    x, y = root.winfo_rootx(), root.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x+root.winfo_width(), y+root.winfo_height()), all_screens=True).save(folder / f'pp5_{version}.png')
projected = w.session.current_slide_id
w.jump(len(w.plan.slides)-1)
w.view_version.set('live')
w.switch_version()
assert w.session.current_slide_id == projected
root.update()
time.sleep(.5)
x, y = root.winfo_rootx(), root.winfo_rooty()
ImageGrab.grab(bbox=(x, y, x+root.winfo_width(), y+root.winfo_height()), all_screens=True).save(folder / 'pp5_live_preview.png')
assert w.apply_live()
root.destroy()

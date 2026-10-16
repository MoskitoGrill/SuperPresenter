"""Capture the pre-PP8L UI without opening user documents or saving settings."""
from pathlib import Path
import sys
import tempfile
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import ImageGrab
from presentationpresenter.projection import configure_dpi
from presentationpresenter.settings import AppSettings
from presentationpresenter.ui import MainWindow

configure_dpi()
with tempfile.TemporaryDirectory() as recovery:
    root = tk.Tk()
    app = MainWindow(root, settings=AppSettings(), recovery_dir=recovery)
    root.after_cancel(app.autosave_job)
    app.autosave_job = None
    root.geometry('1280x900+30+30')
    root.update()
    output = Path(__file__).parent / 'previews' / 'pp8l-before.png'
    ImageGrab.grab(bbox=(root.winfo_rootx(), root.winfo_rooty(),
                        root.winfo_rootx()+root.winfo_width(),
                        root.winfo_rooty()+root.winfo_height())).save(output)
    print('Window:', root.winfo_width(), root.winfo_height())
    print('Preview:', app.preview.winfo_width(), app.preview.winfo_height())
    print('Editor:', app.text.winfo_width(), app.text.winfo_height())
    root.destroy()

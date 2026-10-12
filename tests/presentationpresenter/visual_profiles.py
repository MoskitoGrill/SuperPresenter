"""Capture only the new UI, without writing user preferences or presets."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import tkinter as tk
import time
from PIL import ImageGrab
from presentationpresenter.projection import configure_dpi
from presentationpresenter.settings import AppSettings
from presentationpresenter.ui import MainWindow
from presentationpresenter.projection import Monitor
from unittest.mock import patch

configure_dpi()
root = tk.Tk()
w = MainWindow(root, AppSettings())
root.update()
folder = Path(__file__).parent/'previews'
folder.mkdir(exist_ok=True)
for name in ('pp4_profiles_main.png', 'pp4_profiles_editor.png'):
    if name.endswith('editor.png'):
        w.projection_controls.open_editor()
        root.update()
        widget = w.projection_controls.editor.win
    else:
        widget = root
    widget.lift()
    root.update()
    time.sleep(.3)
    x, y = widget.winfo_rootx(), widget.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x+widget.winfo_width(), y+widget.winfo_height()), all_screens=True).save(folder/name)
w.projection_controls.editor.cancel()
with patch('presentationpresenter.ui.monitors', return_value=[Monitor('QA-left', -1280, 0, 1280, 720), Monitor('QA-primary', 0, 0, 1920, 1080, True)]):
    w.refresh_monitors_now()
    w.monitor_choices['hall'].set('QA-primary')
    w.projection_controls.open_editor()
    editor = w.projection_controls.editor
    editor.cards['QA-left']['style'].set('Stream')
    editor.cards['QA-left']['name'].set('Stream monitor')
    editor.win.lift()
    root.update()
    time.sleep(.3)
    x, y = editor.win.winfo_rootx(), editor.win.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x+editor.win.winfo_width(), y+editor.win.winfo_height()), all_screens=True).save(folder/'pp4_profiles_two_monitors.png')
w.projection_controls.editor.cancel()
w.refresh_monitors_now()
for field in ('hall', 'stream'):
    w.monitor_choices[field].set(w.monitor_inventory[0].id)
    w.projection_controls.enabled[field] = True
    w.projection_controls.fullscreen[field] = False
w.text.insert('1.0', 'Test běžného projekčního okna.\nSál a stream používají stejnou potvrzenou session.')
root.update()
assert w.projection_controls.start()
w.jump(1)
for field in ('hall', 'stream'):
    widget = w.projections[field].window
    widget.lift()
    root.update()
    time.sleep(.3)
    x, y = widget.winfo_rootx(), widget.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x+widget.winfo_width(), y+widget.winfo_height()), all_screens=True).save(folder/f'pp4_windowed_{field}.png')
root.destroy()

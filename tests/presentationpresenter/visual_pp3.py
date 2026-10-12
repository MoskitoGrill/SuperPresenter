"""Actual editor-window capture and focus smoke check. Does not save preferences."""
import ctypes
import sys
import tkinter as tk
from time import perf_counter
from pathlib import Path
from PIL import ImageGrab
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from presentationpresenter.ui import MainWindow
from presentationpresenter.settings import AppSettings

ctypes.windll.shcore.SetProcessDpiAwareness(2)
root = tk.Tk()
window = MainWindow(root, AppSettings(geometry='1280x850+0+0'))
root.attributes('-topmost', True)
root.update()
root.focus_force()
window.title.set('Žalm 23 • Příprava prezentace')
window.text.insert('1.0', 'Hospodin je můj pastýř.\nNic mi neschází.\n'+('Český text pro společné pokračování sálu a streamu. '*45))
root.update()
window.text.tag_add('sel', '1.0', '1.8')
window.format_selection('bold')
window.format_selection('color', '#ffd166')
window.text.tag_remove('sel', '1.0', 'end')
window.text.mark_set('insert', '3.0')
window.toggle_bullets()
window.rebuild()
window.jump(1, select=True)
window.text.focus_set()
root.update()
assert root.focus_get() is window.text
assert window.strip.winfo_rooty()+window.strip.winfo_height() <= root.winfo_rooty()+root.winfo_height()
assert window.text.winfo_height() > 100
widgets = tuple(window.thumbnails)
window.jump(2)
root.update()
assert root.focus_get() is window.text
assert tuple(window.thumbnails) == widgets
started = perf_counter()
for i in range(30):
    window.jump(i % len(window.plan.slides))
print(f'30 navigations: {perf_counter()-started:.3f}s; thumbnail widgets preserved')
window.undo()
window.redo()
root.update()
assert root.focus_get() is window.text
folder = Path(__file__).resolve().parent/'previews'
original = window.document
window.thumbnails[0].event_generate('<Button-1>')
root.update()
assert root.focus_get() is window.thumbnails[0]
window.thumbnails[0].event_generate('<KeyPress-Delete>')
root.update()
assert not window.document.sections[0].break_before
assert window.document.black_end
window.undo()
assert window.document == original
root.update()
window.thumbnails[-1].event_generate('<Button-1>')
root.update()
assert window.current == len(window.plan.slides)-1
assert root.focus_get() is window.thumbnails[-1]
window.thumbnails[-1].event_generate('<KeyPress-Delete>')
root.update()
assert not window.document.black_end
window.undo()
assert window.document == original
window.text.focus_set()
folder.mkdir(exist_ok=True)
for output in ('hall', 'stream'):
    window.output.set(output)
    window.jump(1)
    root.update()
    root.after(200)
    root.update()
    x, y = root.winfo_rootx(), root.winfo_rooty()
    path = folder/f'pp3_{output}.png'
    ImageGrab.grab(bbox=(x, y, x+root.winfo_width(), y+root.winfo_height())).save(path)
    print(path)
root.geometry('1100x720+0+0')
window.output.set('hall')
root.update()
root.after(200)
root.update()
assert window.strip.winfo_rooty()+window.strip.winfo_height() <= root.winfo_rooty()+root.winfo_height()
x, y = root.winfo_rootx(), root.winfo_rooty()
for button in window.source_buttons+[window.copy_slide_button]:
    assert button.winfo_height() >= button.winfo_reqheight(), button.cget('text')
ImageGrab.grab(bbox=(x, y, x+root.winfo_width(), y+root.winfo_height())).save(folder/'pp3_default.png')
root.destroy()
print('Focus, navigation cache, undo/redo and both previews OK')

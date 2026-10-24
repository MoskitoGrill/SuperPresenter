"""Owned-window visual QA. Pass an output directory; no user settings are saved."""
import sys
import tempfile
import tkinter as tk
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import ImageGrab
from presentationpresenter.projection import configure_dpi
from presentationpresenter.ui import MainWindow
from presentationpresenter.settings import AppSettings
from presentationpresenter.pptx_import_window import ImportWindow
from tests.presentationpresenter.test_pptx_import import fixture, slide, shape

def main():
    configure_dpi()
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        source = fixture(Path(folder)/'qa.pptx', [slide(black=True),
            slide(shape('Jan 16:4–21', True)+shape('První část textu. '*12)),
            slide(shape('Jan 16:4–21', True)+shape('Druhá část textu. '*12)),
            slide(black=True), slide(shape('Jan 16:4–21', True)+shape('Samostatný úsek za předělem.'))])
        root = tk.Tk()
        root.geometry('1280x900+30+30')
        app = MainWindow(root, AppSettings(), recovery_dir=Path(folder)/'recovery')
        root.after_cancel(app.autosave_job)
        app.autosave_job = None
        errors = []
        root.report_callback_exception = lambda *e: errors.append(e)
        def capture(window, name):
            window.attributes('-topmost', True)
            window.lift()
            window.update()
            # HWND coverage alone does not mean the Windows map/fade animation
            # has finished; wait before capturing an opaque owned window.
            window.after(600, window.quit)
            window.mainloop()
            import ctypes
            from ctypes import wintypes
            class Point(ctypes.Structure):
                _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]
            user = ctypes.windll.user32
            user.WindowFromPoint.argtypes = [Point]
            user.WindowFromPoint.restype = wintypes.HWND
            user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
            user.GetAncestor.restype = wintypes.HWND
            expected = user.GetAncestor(window.winfo_id(), 2)
            actual = user.GetAncestor(user.WindowFromPoint(Point(window.winfo_rootx()+10, window.winfo_rooty()+10)), 2)
            assert actual == expected, 'Screenshot target is occluded'
            ImageGrab.grab(bbox=(window.winfo_rootx(), window.winfo_rooty(), window.winfo_rootx()+window.winfo_width(), window.winfo_rooty()+window.winfo_height())).save(output/name)
            window.attributes('-topmost', False)
            print(name, window.winfo_width(), window.winfo_height())
        app.ribbon.show('Soubor')
        capture(root, 'pptx-file.png')
        app.ribbon.show('Úseky')
        capture(root, 'pptx-sections.png')
        review = ImportWindow(app, source)
        review.window.geometry('1050x760+60+60')
        review.move(1)
        capture(review.window, 'pptx-review.png')
        assert review.insert.winfo_y()+review.insert.winfo_height() <= review.insert.master.winfo_height()
        notebook = next(w for w in review.window.winfo_children() if isinstance(w, __import__('tkinter').ttk.Notebook))
        notebook.select(1)
        capture(review.window, 'pptx-details.png')
        review.window.geometry('760x600+60+60')
        capture(review.window, 'pptx-review-small.png')
        assert review.insert.winfo_ismapped()
        review.window.destroy()
        root.destroy()
        assert not errors, errors

if __name__ == '__main__':
    main()

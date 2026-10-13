"""Capture only the QA Bible window; no user settings or clipboard changes."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import ImageGrab
from presentationpresenter.bible_window import BibleWindow
from presentationpresenter.projection import configure_dpi

configure_dpi()
bible = BibleWindow()
bible.window.geometry('850x700+80+80')
bible.query.set('Jan 3:36–4:2')
bible.lookup()
bible.window.update()
out = Path(__file__).parent / 'previews'
out.mkdir(exist_ok=True)

def capture(name):
    w = bible.window
    w.update()
    ImageGrab.grab(bbox=(w.winfo_rootx(), w.winfo_rooty(),
                         w.winfo_rootx()+w.winfo_width(), w.winfo_rooty()+w.winfo_height())).save(out/name)

def finish():
    capture('pp7_bible.png')
    bible.query.set('Janovy listy 1:1')
    bible.lookup()
    bible.window.after(200, ambiguous)

def ambiguous():
    capture('pp7_ambiguous.png')
    bible.close()

bible.window.after(300, finish)
bible.window.mainloop()

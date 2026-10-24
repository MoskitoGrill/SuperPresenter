"""Repeat a large image through the real renderer, without user data/settings."""
import io
import sys
import time
from pathlib import Path
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image
from presentationpresenter.media import from_bytes
from presentationpresenter.domain import Presentation, ImageSection
from presentationpresenter.layout import paginate, Typography
from presentationpresenter.rendering import TkMetrics, draw

root = tk.Tk()
root.withdraw()
metrics = TkMetrics(root)
raw = io.BytesIO()
Image.effect_noise((1600, 900), 40).convert('RGB').save(raw, 'PNG')
asset = from_bytes(raw.getvalue())
document = Presentation(sections=(ImageSection('QA', asset.id, break_after=False),), media=(asset,), black_start=False)
slide = paginate(document, metrics).slides[0]
canvas = tk.Canvas(root)
started = time.perf_counter()
for _ in range(30):
    draw(canvas, slide, 'hall', metrics, Typography(), scale=.65)
print('30 repeated image renders:', round(time.perf_counter()-started, 4), 'seconds')
root.destroy()

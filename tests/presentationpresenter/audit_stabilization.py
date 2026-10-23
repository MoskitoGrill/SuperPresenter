"""Read-only audit of the maintained example across both output aspects."""
from pathlib import Path
import sys
import hashlib
import json
import time
import tkinter as tk
from dataclasses import replace

root_path = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root_path))
from presentationpresenter.storage import load
from presentationpresenter.domain import Aspect
from presentationpresenter.layout import paginate, Typography
from presentationpresenter.rendering import TkMetrics, draw
from presentationpresenter.preflight import check
from presentationpresenter.projection import Monitor, configure_dpi

configure_dpi()
paths = [root_path/'presentation/Vzorova_prezentace.ppres',
         root_path/'presentation/Vzorova_prezentace_navod.md',
         root_path/'scripts/create_demo_presentation.py']
before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
document = load(paths[0])
root = tk.Tk()
root.withdraw()
metrics = TkMetrics(root)
canvas = tk.Canvas(root)
try:
    for hall in Aspect:
        for stream in Aspect:
            source = replace(document, hall=replace(document.hall, aspect=hall), stream=replace(document.stream, aspect=stream))
            started = time.perf_counter()
            plan = paginate(source, metrics)
            issues = check(source, metrics, Typography(), [Monitor('QA', 0, 0, 1280, 900)],
                           dict(hall='QA', stream='QA'), dict(hall=False, stream=False), ('hall', 'stream'), plan)
            assert not any(i.blocking for i in issues), [i.message for i in issues if i.blocking]
            for slide in plan.slides:
                for output in ('hall', 'stream'):
                    draw(canvas, slide, output, metrics, Typography(), scale=.25)
            print(json.dumps(dict(hall=hall.value, stream=stream.value, sections=len(source.sections),
                                  slides=len(plan.slides), warnings=len(issues),
                                  seconds=round(time.perf_counter()-started, 3),
                                  raster_cache_bytes=metrics.rasters.resident_bytes)), flush=True)
finally:
    metrics.clear()
    root.destroy()
assert before == [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
print('Example, guide and generator unchanged.')

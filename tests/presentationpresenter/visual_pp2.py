"""Capture actual Tk renderer pixels for PP2 visual QA (no user settings)."""
import sys
from pathlib import Path
import tkinter as tk
import ctypes
from dataclasses import replace
from PIL import ImageGrab, Image, ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from presentationpresenter.domain import *
from presentationpresenter.layout import paginate, Typography
from presentationpresenter.rendering import TkMetrics, draw
from tests.presentationpresenter.test_pp2 import stress_document

ctypes.windll.shcore.SetProcessDpiAwareness(2)
root=tk.Tk()
root.title('PP2 visual verification')
root.geometry('1300x780+0+0')
root.attributes('-topmost',True)
canvas=tk.Canvas(root,highlightthickness=0)
canvas.pack(anchor='nw')
metrics=TkMetrics(root)
folder=Path(__file__).resolve().parent/'previews'
folder.mkdir(exist_ok=True)
shots=[]
for hall in Aspect:
    for stream in Aspect:
        source=replace(stress_document(),hall=OutputConfig(hall),stream=OutputConfig(stream,CameraRegion()))
        plan=paginate(source,metrics)
        candidates=[s for s in plan.slides if not s.black and s.ranges]
        selected=[candidates[0],next(s for s in candidates if any(p.text=='↳' for p in s.stream.pieces)),
                  next(s for s in candidates if any(p.style.color=='#ffd166' for p in s.stream.pieces)),
                  next(s for s in candidates if any('WWWW' in p.text for p in s.stream.pieces))]
        for index,slide in enumerate(selected):
            for output in ('hall','stream'):
                draw(canvas,slide,output,metrics,Typography())
                root.update()
                root.after(150)
                root.update()
                layout=getattr(slide,output)
                x,y=canvas.winfo_rootx(),canvas.winfo_rooty()
                screenshot=ImageGrab.grab(bbox=(x,y,x+layout.width,y+layout.height))
                label=f'{hall.value.replace(":","-")}_{stream.value.replace(":","-")}_{index}_{output}'
                screenshot.save(folder/(label+'.png'))
                thumbnail=screenshot.copy()
                thumbnail.thumbnail((640,360))
                tile=Image.new('RGB',(660,395),'#444444')
                tile.paste(thumbnail,(10,30))
                ImageDraw.Draw(tile).text((10,8),label,fill='white')
                shots.append(tile)
root.destroy()
contact=Image.new('RGB',(1320,395*(len(shots)//2)),'#444444')
for i,shot in enumerate(shots):
    contact.paste(shot,((i%2)*660,(i//2)*395))
contact.save(folder/'contact.png')
print(folder/'contact.png')

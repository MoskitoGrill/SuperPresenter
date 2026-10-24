"""Calculated geometry diagrams for the reported image combinations."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw
from presentationpresenter.composition import grid
from presentationpresenter.domain import Aspect, OutputConfig, CameraRegion
from presentationpresenter.layout import geometry

# Standalone raster of the calculated geometry, suitable for layout inspection.
folder = Path(__file__).parent/'previews'
folder.mkdir(exist_ok=True)
sizes = ((360, 520), (900, 420), (400, 520))
for count in (2, 3):
    reference = grid(sizes[:count], OutputConfig(Aspect.STANDARD))
    for output, config in (('hall', OutputConfig(Aspect.STANDARD)), ('stream', OutputConfig(Aspect.WIDE, CameraRegion()))):
        w, h, camera, exclusion = geometry(config)
        image = Image.new('RGB', (w, h), 'black')
        ink = ImageDraw.Draw(image)
        if camera:
            ink.rectangle((camera.x, camera.y, camera.x+camera.width, camera.y+camera.height), fill='#242424', outline='#888888')
            ink.text((camera.x+12, camera.y+12), 'KAMERA', fill='white')
        for index, box in enumerate(grid(sizes[:count], config, reference=reference if output == 'stream' else None)):
            ink.rectangle((box.x, box.y, box.x+box.width-1, box.y+box.height-1), fill=('#386e9c', '#a3772a', '#765082')[index], outline='white', width=3)
            ink.text((box.x+12, box.y+12), str(index+1), fill='white')
        image.save(folder/f'camera_grid_{count}_{output}.png')

"""Validated, immutable embedded raster media; never consult source paths."""
import base64
import io
from functools import lru_cache
from collections import OrderedDict
from pathlib import Path
from PIL import Image, ImageOps
from .domain import MediaAsset

MAX_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 20_000_000

def decode(locator):
    try:
        if not locator.startswith('data:image/png;base64,'):
            raise ValueError('Médium není vložený PNG obrázek')
        if len(locator) > MAX_BYTES * 4 // 3 + 100:
            raise ValueError('Obrázek je příliš velký')
        raw = base64.b64decode(locator.split(',', 1)[1], validate=True)
        if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Vložené médium není PNG')
        return raster(raw)
    except (OSError, TypeError, AttributeError) as exc:
        raise ValueError('Neplatný obrázek') from exc

def raster(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('Obrázek překračuje 20 MiB')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in ('PNG', 'JPEG', 'GIF', 'BMP', 'WEBP'):
                raise ValueError('Nepodporovaný obrazový formát')
            if image.width * image.height > MAX_PIXELS:
                raise ValueError('Obrázek překračuje 20 milionů pixelů')
            image.load()
            return ImageOps.exif_transpose(image).convert('RGBA')
    except (OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValueError('Poškozený obrázek') from exc

def from_bytes(raw):
    image = raster(raw)
    stream = io.BytesIO()
    image.save(stream, format='PNG')
    if stream.tell() > MAX_BYTES:
        raise ValueError('Převedený obrázek překračuje 20 MiB')
    return MediaAsset('data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode('ascii'), 'image/png')

def from_path(path):
    with Path(path).open('rb') as source:
        return from_bytes(source.read(MAX_BYTES + 1))

@lru_cache(maxsize=16)
def dimensions(locator):
    return decode(locator).size


class ScaledRasterCache:
    """Read-only resized rasters, bounded by pixels plus retained locator bytes.

    Owned by one renderer, without Tk objects or full-resolution decode caching.
    Callers must not mutate returned images. Oversized entries bypass the cache.
    """
    def __init__(self, max_bytes=32*1024*1024, max_entries=32):
        self.max_bytes = max_bytes
        self.max_entries = max_entries
        self.entries = OrderedDict()
        self.resident_bytes = 0

    def get(self, locator, size):
        size = tuple(max(1, int(value)) for value in size)
        key = locator, size
        entry = self.entries.get(key)
        if entry is not None:
            self.entries.move_to_end(key)
            return entry[0]
        image = decode(locator).resize(size, Image.Resampling.LANCZOS)
        cost = size[0]*size[1]*4+len(locator)
        if cost <= self.max_bytes and self.max_entries > 0:
            while self.entries and (len(self.entries) >= self.max_entries or self.resident_bytes+cost > self.max_bytes):
                _, (_, removed) = self.entries.popitem(last=False)
                self.resident_bytes -= removed
            self.entries[key] = image, cost
            self.resident_bytes += cost
        return image

    def clear(self):
        self.entries.clear()
        self.resident_bytes = 0

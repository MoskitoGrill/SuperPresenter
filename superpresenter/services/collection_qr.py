"""Portable QR preferences and shared preview/projector geometry."""
import base64
from io import BytesIO
import math

from PIL import Image, ImageOps


def default_settings(style):
    old = style.get('collection', {})
    width = style.get('canvas', {}).get('width', 1920)
    height = style.get('canvas', {}).get('height', 1080)
    size = min(old.get('size', 360), width, height)
    anchor = old.get('anchor', 'center')
    ax = 0 if 'w' in anchor else 1 if 'e' in anchor and anchor != 'center' else .5
    ay = 0 if 'n' in anchor and anchor != 'center' else 1 if 's' in anchor else .5
    x = old.get('relx', .87) * width - ax * size
    y = old.get('rely', .55) * height - ay * size
    return dict(size_pct=100 * size / min(width, height),
                x_pct=max(0, min(100, 100 * x / max(1, width - size))),
                y_pct=max(0, min(100, 100 * y / max(1, height - size))))


def decode_image(data):
    if not isinstance(data, str) or len(data) > 8_000_000:
        raise ValueError('Obrázek QR je příliš velký nebo neplatný.')
    try:
        raw = base64.b64decode(data, validate=True)
        with Image.open(BytesIO(raw)) as image:
            if image.width * image.height > 16_000_000:
                raise ValueError('Obrázek QR je příliš velký.')
            return image.convert('RGBA')
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValueError('Nelze načíst obrázek QR.') from exc


def encode_image(path):
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert('RGBA')
        image.thumbnail((1600, 1600), Image.Resampling.NEAREST)
        stream = BytesIO()
        image.save(stream, format='PNG')
    return base64.b64encode(stream.getvalue()).decode('ascii')


def validate_settings(settings):
    if not isinstance(settings, dict):
        raise ValueError('Nastavení QR musí být objekt.')
    for key in ('size_pct', 'x_pct', 'y_pct'):
        value = settings.get(key)
        if (type(value) not in (int, float) or not math.isfinite(value)
                or not (1 if key == 'size_pct' else 0) <= value <= 100):
            raise ValueError('Velikost QR musí být 1–100 %, poloha 0–100 %.')
    if 'image_data' in settings:
        decode_image(settings['image_data'])
    if not isinstance(settings.get('image_name', ''), str):
        raise ValueError('Neplatný název obrázku QR.')
    return settings


def geometry(settings, width, height):
    """Position percentages describe available travel, keeping the QR in view."""
    side = max(1, round(min(width, height) * settings['size_pct'] / 100))
    return (round((width - side) * settings['x_pct'] / 100),
            round((height - side) * settings['y_pct'] / 100), side)


def render_image(image, side):
    # The white margin is part of the requested size. Do not stretch or blur QR.
    margin = max(1, round(side * .08))
    content = ImageOps.contain(image, (max(1, side - 2 * margin),) * 2,
                              Image.Resampling.NEAREST)
    result = Image.new('RGB', (side, side), 'white')
    result.paste(content, ((side - content.width) // 2, (side - content.height) // 2),
                 content.getchannel('A') if content.mode == 'RGBA' else None)
    return result

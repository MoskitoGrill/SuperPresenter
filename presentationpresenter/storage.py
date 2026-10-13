"""PPRES v2: bounded UTF-8 JSON envelope; v1 remains readable.

Writes use a unique sibling temporary file, fsync and atomic os.replace.
Loading validates everything before callers change their draft.
"""
import base64
import json
import os
import tempfile
from pathlib import Path
from dataclasses import replace
from . import persistence
from .domain import Presentation, ImageSection, TextSection, TextBlock, TextRun, ImportOrigin
from .media import decode, from_bytes

MAX_FILE = 100 * 1024 * 1024

def validate(document):
    if type(document.title) is not str:
        raise ValueError('Název prezentace musí být text')
    if len(document.sections) > 10000 or len(document.media) > 1000:
        raise ValueError('Prezentace překračuje povolený počet položek')
    for asset in document.media:
        if asset.mime_type != 'image/png':
            raise ValueError('Nepodporované médium')
        decode(asset.locator)
    return document

def encode(document):
    validate(document)
    payload = json.dumps({'format': 'PresentationPresenter', 'version': 2,
                          'document': json.loads(persistence.dumps(document))},
                         ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(payload) > MAX_FILE:
        raise ValueError('Prezentace překračuje 100 MiB')
    return payload

def atomic_write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as target:
            target.write(payload)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def save(path, document):
    atomic_write(path, encode(document))

def read_json(path):
    with Path(path).open('rb') as source:
        raw = source.read(MAX_FILE+1)
    if len(raw) > MAX_FILE:
        raise ValueError('Soubor překračuje 100 MiB')
    try:
        return json.loads(raw.decode('utf-8-sig'))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ValueError('Neplatný JSON soubor') from exc

def load(path):
    data = read_json(path)
    try:
        if data['format'] != 'PresentationPresenter' or type(data['version']) is not int or data['version'] not in (1, 2):
            raise ValueError('Nepodporovaný formát nebo verze')
        return validate(persistence.loads(json.dumps(data['document'], allow_nan=False)))
    except (KeyError, TypeError, RecursionError) as exc:
        raise ValueError('Neplatný soubor prezentace') from exc

def import_legacy(path):
    """Only original list of link/text or embedded img_data items; read-only."""
    data = read_json(path)
    if not isinstance(data, list) or len(data) > 10000:
        raise ValueError('Původní formát musí být seznam snímků')
    sections, media = [], []
    warnings = ['Import zachovává prostý text a vložené obrázky. Původní styly, profily, dělení a samostatný soubor _images.json se nepřenášejí. Originál zůstává beze změny.']
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            warnings.append(f'Položka {index+1}: nepodporovaný obsah vynechán.')
            continue
        origin = ImportOrigin('legacy-json', str(path), str(index))
        try:
            if item.get('image'):
                encoded = item.get('img_data', '')
                if type(encoded) is not str or len(encoded) > 28_000_000:
                    raise ValueError('Neplatná velikost obrázku')
                asset = from_bytes(base64.b64decode(encoded, validate=True))
                media.append(asset)
                sections.append(ImageSection(f'Obrázek {index+1}', asset.id, origin=origin, break_after=False, break_before=True))
            else:
                text, title = item.get('text', ''), item.get('link', '')
                if type(text) is not str or type(title) is not str:
                    raise ValueError('Text nebo odkaz není řetězec')
                if not text and not title:
                    continue
                sections.append(TextSection(title, tuple(TextBlock((TextRun(line),)) for line in text.split('\n')),
                                            origin=origin, break_after=False, break_before=True))
            if set(item) - {'image', 'img_data', 'text', 'link'}:
                warnings.append(f'Položka {index+1}: další obsah nebo formátování vynecháno.')
        except (ValueError, OSError) as exc:
            warnings.append(f'Položka {index+1}: vynechána ({exc}).')
    if not sections:
        raise ValueError('Soubor neobsahuje podporovaný obsah')
    return Presentation(title=Path(path).stem, sections=tuple(sections), media=tuple(media), black_start=False, black_end=True), warnings

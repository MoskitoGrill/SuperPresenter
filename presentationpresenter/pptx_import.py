"""Bounded, read-only PresentationML content adapter. Not a slide renderer."""
from dataclasses import dataclass, replace
from pathlib import Path
import posixpath
import zipfile
import xml.etree.ElementTree as ET
from .domain import (Presentation, TextSection, TextBlock, TextRun, TextStyle,
                     BlockKind, ImageItem, ImportOrigin)
from . import media

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
RID = '{'+NS['r']+'}'

@dataclass(frozen=True)
class ImportResult:
    document: Presentation
    warnings: tuple[str, ...]
    mapping: tuple[str, ...]

class Package:
    def __init__(self, archive):
        self.archive = archive
        infos = archive.infolist()
        if len(infos) > 10000 or sum(i.file_size for i in infos) > 250 * 1024 * 1024:
            raise ValueError('PPTX překračuje limity (10 000 součástí / 250 MiB po rozbalení).')
        if len({i.filename for i in infos}) != len(infos):
            raise ValueError('PPTX obsahuje duplicitní součásti.')

    def xml(self, name):
        if self.archive.getinfo(name).file_size > 5 * 1024 * 1024:
            raise ValueError('XML součást PPTX překračuje 5 MiB.')
        raw = self.archive.read(name)
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise ValueError('Nepovolená deklarace XML.')
        return ET.fromstring(raw)

    def rels(self, name):
        path = posixpath.join(posixpath.dirname(name), '_rels', posixpath.basename(name)+'.rels')
        if path not in self.archive.namelist():
            return {}
        result = {}
        for rel in self.xml(path):
            target = rel.get('Target', '')
            external = rel.get('TargetMode') == 'External'
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target)) if not target.startswith('/') else target.lstrip('/')
            if not external and (resolved.startswith('../') or '\\' in resolved):
                raise ValueError('Neplatná cesta uvnitř PPTX.')
            result[rel.get('Id')] = (rel.get('Type', '').rsplit('/', 1)[-1], resolved, external)
        return result

    def ancestor(self, name, kind):
        target = next((v[1] for v in self.rels(name).values() if v[0] == kind and not v[2]), None)
        return (target, self.xml(target)) if target else (None, None)

def text_of(shape):
    return '\n'.join(''.join(n.text or '' for n in p.iter() if n.tag == '{'+NS['a']+'}t')
                     for p in shape.findall('./p:txBody/a:p', NS)).strip()

def placeholder(shape):
    return shape.find('./p:nvSpPr/p:nvPr/p:ph', NS)

def content_shapes(tree, kind):
    """Walk supported groups only; never import both AlternateContent branches."""
    result = []
    for child in tree:
        if child.tag == '{'+NS['p']+'}'+kind:
            result.append(child)
        elif child.tag == '{'+NS['p']+'}grpSp':
            result.extend(content_shapes(child, kind))
    return result

def matching_shape(root, shape):
    ph = placeholder(shape)
    if root is None or ph is None:
        return None
    for candidate in root.findall('.//p:sp', NS):
        other = placeholder(candidate)
        if other is not None and other.get('idx', '0') == ph.get('idx', '0'):
            return candidate
    return None

def paragraph_props(paragraph, shape, layout, master):
    direct = paragraph.find('a:pPr', NS)
    level = int(direct.get('lvl', '0')) if direct is not None else 0
    props = [direct]
    for ancestor in (shape, matching_shape(layout, shape), matching_shape(master, shape)):
        if ancestor is not None:
            props.append(ancestor.find(f'p:txBody/a:lstStyle/a:lvl{level+1}pPr', NS))
    ph = placeholder(shape)
    kind = ph.get('type', 'obj') if ph is not None else None
    if master is not None and ph is not None:
        style = 'titleStyle' if kind in ('title', 'ctrTitle') else 'bodyStyle' if kind in ('body', 'obj') else 'otherStyle'
        props.append(master.find(f'p:txStyles/p:{style}/a:lvl{level+1}pPr', NS))
    return level, [p for p in props if p is not None]

def blocks_of(shape, layout, master, style, warn):
    blocks = []
    for paragraph in shape.findall('p:txBody/a:p', NS):
        level, props = paragraph_props(paragraph, shape, layout, master)
        bullet = next((c for p in props for c in p if c.tag.rsplit('}', 1)[-1] in ('buNone', 'buChar', 'buAutoNum', 'buBlip')), None)
        tag = bullet.tag.rsplit('}', 1)[-1] if bullet is not None else 'buNone'
        kind = BlockKind.NUMBERED if tag == 'buAutoNum' else BlockKind.BULLET if tag in ('buChar', 'buBlip') else BlockKind.PARAGRAPH
        if tag == 'buBlip':
            warn('Obrázková odrážka nahrazena běžnou odrážkou.')
        if tag == 'buAutoNum':
            warn('Číslování používá naše pořadí od 1 a naše značky, ne původní styl či počáteční číslo.')
        if kind != BlockKind.PARAGRAPH and level > 2:
            warn('Seznam hlubší než tři úrovně převeden na třetí úroveň.')
        runs = []
        for child in paragraph:
            local = child.tag.rsplit('}', 1)[-1]
            if local == 'br':
                runs.append(TextRun('\n', style))
            elif local in ('r', 'fld'):
                value = child.findtext('a:t', '', NS)
                if value:
                    inherited = [child.find('a:rPr', NS)] + [p.find('a:defRPr', NS) for p in props]
                    def flag(key, default):
                        value = next((p.get(key) for p in inherited if p is not None and p.get(key) is not None), None)
                        return default if value is None else value not in ('0', 'false', 'none')
                    runs.append(TextRun(value, replace(style, bold=flag('b', style.bold),
                                                      italic=flag('i', style.italic), underline=flag('u', style.underline))))
                if local == 'fld':
                    warn('Dynamické textové pole převedeno na jeho uložený text.')
        blocks.append(TextBlock(tuple(runs) or (TextRun('', style),), kind=kind,
                                level=min(level, 2) if kind != BlockKind.PARAGRAPH else 0))
    return blocks

def black_background(roots, theme=None):
    """Conservative solid black, including a resolved template theme color."""
    for root in roots:
        if root is None:
            continue
        bg = root.find('p:cSld/p:bg', NS)
        if bg is not None:
            color = bg.find('p:bgPr/a:solidFill/a:srgbClr', NS)
            if color is not None:
                return len(color) == 0 and color.get('val', '').upper() == '000000'
            scheme = bg.find('p:bgPr/a:solidFill/a:schemeClr', NS)
            if scheme is not None and len(scheme) == 0 and theme is not None:
                key = scheme.get('val')
                master = roots[-1]
                cmap = master.find('p:clrMap', NS) if master is not None else None
                override = next((r.find('p:clrMapOvr/a:overrideClrMapping', NS) for r in roots if r is not None and r.find('p:clrMapOvr/a:overrideClrMapping', NS) is not None), None)
                if override is not None:
                    cmap = override
                key = cmap.get(key, key) if cmap is not None else {'tx1': 'dk1', 'bg1': 'lt1'}.get(key, key)
                entry = theme.find(f'a:themeElements/a:clrScheme/a:{key}', NS)
                if entry is not None and len(entry):
                    value = entry[0].get('lastClr', '') if entry[0].tag.endswith('}sysClr') else entry[0].get('val', '')
                    return len(entry[0]) == 0 and value.upper() == '000000'
            return False
    return False

def black_cover(shapes, presentation):
    """A simple opaque full-slide black rectangle is also a template divider."""
    size = presentation.find('p:sldSz', NS)
    if size is None or len(shapes) != 1:
        return False
    shape = shapes[0]
    color = shape.find('p:spPr/a:solidFill/a:srgbClr', NS)
    geom = shape.find('p:spPr/a:prstGeom', NS)
    offset = shape.find('p:spPr/a:xfrm/a:off', NS)
    extent = shape.find('p:spPr/a:xfrm/a:ext', NS)
    line = shape.find('p:spPr/a:ln', NS)
    return (color is not None and color.get('val', '').upper() == '000000' and len(color) == 0
            and line is not None and line.find('a:noFill', NS) is not None
            and shape.find('p:style', NS) is None and shape.find('p:spPr/a:effectLst', NS) is None
            and geom is not None and geom.get('prst') == 'rect'
            and offset is not None and offset.get('x') == '0' and offset.get('y') == '0'
            and extent is not None and extent.get('cx') == size.get('cx') and extent.get('cy') == size.get('cy')
            and shape.find('p:spPr/a:xfrm', NS).get('rot', '0') == '0')

def read_pptx(path, *, style=None, join_same=True, hall=None, stream=None):
    style = style or TextStyle(family='Calibri')
    path = Path(path)
    if path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError('PPTX překračuje 100 MiB.')
    warnings, mapping, sections, assets = [], [], [], []
    pending_black = False
    try:
        with zipfile.ZipFile(path) as archive:
            package = Package(archive)
            presentation = package.xml('ppt/presentation.xml')
            rels = package.rels('ppt/presentation.xml')
            slides = presentation.findall('p:sldIdLst/p:sldId', NS)
            if len(slides) > 1000:
                raise ValueError('PPTX překračuje 1 000 snímků.')
            for index, sid in enumerate(slides, 1):
                def warn(message):
                    value = f'Snímek {index}: {message}'
                    if value not in warnings:
                        warnings.append(value)
                relation = rels.get(sid.get(RID+'id'))
                if not relation or relation[0] != 'slide' or relation[2]:
                    raise ValueError(f'Snímek {index}: neplatný odkaz.')
                name = relation[1]
                root = package.xml(name)
                slide_rels = package.rels(name)
                layout_name, layout = package.ancestor(name, 'slideLayout')
                master_name, master = package.ancestor(layout_name, 'slideMaster') if layout_name else (None, None)
                _, theme = package.ancestor(master_name, 'theme') if master_name else (None, None)
                tree = root.find('p:cSld/p:spTree', NS)
                if tree is None:
                    raise ValueError(f'Snímek {index}: chybí obsah.')
                shapes = content_shapes(tree, 'sp')
                texts = [s for s in shapes if text_of(s)]
                title = next((s for s in texts if placeholder(s) is not None and placeholder(s).get('type') in ('title', 'ctrTitle')), None)
                if title is None:
                    title = next((s for s in texts if (s.find('p:nvSpPr/p:cNvPr', NS).get('name', '').casefold() if s.find('p:nvSpPr/p:cNvPr', NS) is not None else '').startswith(('nadpis', 'title', 'odkaz'))), None)
                if title is None and len(texts) > 1:
                    title = min(texts, key=lambda s: int(s.find('p:spPr/a:xfrm/a:off', NS).get('y', '0')) if s.find('p:spPr/a:xfrm/a:off', NS) is not None else 0)
                    warn('Nadpis odhadnut z horního textového pole; ověřte název a pořadí.')
                body = [s for s in texts if s is not title]
                if len(body) > 1:
                    warn('Více textových polí spojeno v pořadí objektů PPTX; ověřte pořadí čtení.')
                blocks = [b for s in body for b in blocks_of(s, layout, master, style, warn)]
                pictures = content_shapes(tree, 'pic')
                images = []
                for picture in pictures:
                    blip = picture.find('p:blipFill/a:blip', NS)
                    rel = slide_rels.get(blip.get(RID+'embed')) if blip is not None else None
                    if not rel or rel[2] or rel[0] != 'image':
                        warn('Propojený nebo nepodporovaný obrázek nebyl převzat.')
                        continue
                    try:
                        if archive.getinfo(rel[1]).file_size > media.MAX_BYTES:
                            raise ValueError('Obrázek překračuje 20 MiB')
                        asset = media.from_bytes(archive.read(rel[1]))
                        assets.append(asset)
                        images.append(ImageItem(asset.id, repeat=False))
                    except (ValueError, OSError) as exc:
                        warn(f'Obrázek nebyl převzat: {exc}')
                    if picture.find('p:blipFill/a:srcRect', NS) is not None or picture.find('p:spPr/a:xfrm', NS) is not None:
                        warn('Obrázky používají naši mřížku; původní pozice, ořez, rotace a efekty se nepřenášejí.')
                unsupported = []
                for node in tree.iter():
                    tag = node.tag.rsplit('}', 1)[-1]
                    if tag in ('graphicFrame', 'cxnSp', 'grpSp', 'contentPart', 'AlternateContent'):
                        unsupported.append(tag)
                if unsupported:
                    warn('Tabulky, grafy, spojnice a složená grafika se nepřenášejí ('+', '.join(sorted(set(unsupported)))+'). Ze skupin lze převzít jen běžný text a obrázky; získaný obsah ověřte.')
                decorative = [s for s in shapes if not text_of(s) and placeholder(s) is None]
                cover = black_cover(decorative, presentation)
                if decorative and not cover:
                    warn('Netextové tvary a dekorace se nepřenášejí.')
                for kind, _, _ in slide_rels.values():
                    if kind in ('notesSlide', 'video', 'audio', 'media', 'oleObject', 'hyperlink'):
                        warn({'notesSlide': 'Poznámky přednášejícího se neimportují.', 'hyperlink': 'Cíle hypertextových odkazů se nepřenášejí.'}.get(kind, 'Video, zvuk nebo vložený objekt se nepřehrává a není převzat.'))
                if root.find('p:timing', NS) is not None or root.find('p:transition', NS) is not None:
                    warn('Animace a přechody se nepřenášejí; importován je statický obsah.')
                if root.get('show') == '0':
                    warn('Skrytý snímek je zahrnut do importu (naše aplikace skrývání nemá).')
                if not texts and not pictures and not unsupported and (cover or (not decorative and black_background((root, layout, master), theme))):
                    if pending_black:
                        warn('Sousední černé snímky sjednoceny na jeden předěl.')
                    pending_black = True
                    mapping.append(f'{index}: černý předěl')
                    continue
                if not texts and not images:
                    warn('Prázdný nebo nepřevedený snímek ponechán jako prázdný úsek; ověřte či odstraňte jej.')
                heading = text_of(title) if title is not None else ''
                section = TextSection(heading, tuple(blocks), images=tuple(images), break_before=pending_black,
                                      break_after=False, origin=ImportOrigin('pptx', str(path), str(index)))
                if join_same and heading.strip() and sections and not pending_black and sections[-1].title.strip() == heading.strip() and len(sections[-1].images)+len(images) <= 64:
                    previous = sections[-1]
                    origin = replace(previous.origin, item_key=previous.origin.item_key+','+str(index))
                    sections[-1] = replace(previous, blocks=previous.blocks+section.blocks,
                                           images=previous.images+section.images, origin=origin)
                    mapping.append(f'{index}: připojeno k úseku {len(sections)} — {heading}')
                else:
                    sections.append(section)
                    mapping.append(f'{index}: úsek {len(sections)} — {heading or "Bez názvu"}')
                pending_black = False
    except (zipfile.BadZipFile, KeyError, ET.ParseError, RuntimeError, NotImplementedError, RecursionError) as exc:
        raise ValueError(f'PPTX nelze přečíst: {exc}') from exc
    if not sections:
        raise ValueError('PPTX neobsahuje žádný obsahový snímek.')
    document = Presentation(title=path.stem, sections=tuple(sections), media=tuple(assets),
                            black_start=False, black_end=pending_black)
    if hall is not None:
        document = replace(document, hall=hall)
    if stream is not None:
        document = replace(document, stream=stream)
    return ImportResult(document, tuple(warnings), tuple(mapping))

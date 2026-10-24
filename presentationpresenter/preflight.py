"""Read-only checks of the draft, using the actual shared paginator."""
from dataclasses import dataclass, replace
from .domain import ImageSection
from .layout import paginate
from .media import dimensions
from .composition import camera_core


@dataclass(frozen=True)
class Issue:
    message: str
    section_id: str | None = None
    slide_id: str | None = None
    output: str | None = None
    blocking: bool = True


def check(source, metrics, typography, inventory, choices, fullscreen, outputs, plan=None):
    issues = []
    outputs = tuple(outputs)
    available = {m.id: m for m in inventory}
    if not outputs or any(f not in ('hall', 'stream') for f in outputs) or len(set(outputs)) != len(outputs):
        issues.append(Issue('Vyberte alespoň jeden platný výstup (Sál / Stream).'))
    else:
        for field in outputs:
            monitor = available.get(choices.get(field))
            if monitor is None or monitor.width <= 0 or monitor.height <= 0:
                issues.append(Issue('Vybraný monitor není dostupný. V Zobrazení vyberte náhradu.', output=field))
        if len(outputs) == 2 and choices.get('hall') == choices.get('stream') and any(fullscreen.get(f, True) for f in outputs):
            issues.append(Issue('Pro dva výstupy na stejném monitoru vypněte Celá obrazovka u obou.'))
    assets = {a.id: a for a in source.media}
    invalid = {}
    for asset in source.media:
        try:
            if asset.mime_type != 'image/png':
                raise ValueError('Nepodporovaný typ média')
            dimensions(asset.locator)
        except ValueError as exc:
            invalid[asset.id] = str(exc)
    for section in source.sections:
        ids = [section.media_id] if isinstance(section, ImageSection) else [i.media_id for i in section.images]
        for mid in dict.fromkeys(ids):
            if mid not in assets or mid in invalid:
                issues.append(Issue('Chybný nebo chybějící obrázek: '+invalid.get(mid, 'médium není v prezentaci'), section.id))
    if invalid:
        for mid in invalid.keys() - {i for s in source.sections for i in ([s.media_id] if isinstance(s, ImageSection) else [x.media_id for x in s.images])}:
            issues.append(Issue('Nepoužívané poškozené médium: '+invalid[mid], blocking=False))
    # Check every section even if another one cannot be paginated.
    plans = []
    if plan is not None and plan.source == source:
        plans.append(plan)
    else:
        for section in source.sections:
            if any(i.blocking and i.section_id == section.id for i in issues):
                continue
            try:
                plans.append(paginate(replace(source, sections=(section,)), metrics, typography))
            except ValueError as exc:
                issues.append(Issue('Text nebo rozložení se nevejde: '+str(exc), section.id))
    for current in plans:
        by_run = {}
        for slide in current.slides:
            for span in slide.ranges:
                by_run.setdefault(span.run_id, []).append(span)
        for section in current.source.sections:
            if isinstance(section, ImageSection):
                continue
            for block in section.blocks:
                for run in block.runs:
                    spans = by_run.get(run.id, ())
                    cursor = 0
                    for span in spans:
                        if span.start != cursor:
                            break
                        cursor = span.end
                    else:
                        if cursor == len(run.text):
                            continue
                    issues.append(Issue('Dělení nezachovává celý text právě jednou.', section.id))
        for slide in current.slides:
            if slide.black:
                continue
            for field in ('hall', 'stream'):
                layout = getattr(slide, field)
                if layout is None:
                    issues.append(Issue('Chybí rozložení snímku.', slide.section_id, slide.id, field))
                    continue
                for piece in layout.pieces:
                    box = piece.box
                    if box.x < -.01 or box.y < -.01 or box.x+box.width > layout.width+.01 or box.y+box.height > layout.height+.01:
                        issues.append(Issue('Text přetéká mimo snímek.', slide.section_id, slide.id, field))
                    if layout.exclusion and box.intersects(layout.exclusion):
                        issues.append(Issue('Text zasahuje do rezervované oblasti kamery.', slide.section_id, slide.id, field))
                boxes = [i.box for i in layout.images]
                if layout.image_box:
                    boxes.append(layout.image_box)
                for box in boxes:
                    if box.x < -.01 or box.y < -.01 or box.x+box.width > layout.width+.01 or box.y+box.height > layout.height+.01:
                        issues.append(Issue('Obrázek přesahuje plochu snímku.', slide.section_id, slide.id, field))
                    if layout.camera:
                        core = camera_core(layout.camera)
                        if core.width > 0 and core.height > 0 and box.intersects(core):
                            issues.append(Issue('Obrázek překračuje povolený přesah do kamery.', slide.section_id, slide.id, field))
                for warning in layout.warnings:
                    issues.append(Issue(warning, slide.section_id, slide.id, field, False))
    if not source.sections:
        issues.append(Issue('Prezentace nemá žádný obsahový úsek.'))
    # Repeated warnings on continuations link to their first occurrence.
    unique = {}
    for issue in issues:
        unique.setdefault((issue.message, issue.section_id, issue.output, issue.blocking), issue)
    return tuple(unique.values())

"""Deterministic image grids, linked outputs and camera-safe editing geometry."""
import math
from functools import lru_cache
from dataclasses import replace
from .domain import ImagePlacement
from .layout import Rect, OutputLayout, PlacedImage, geometry, LayoutError
from .media import dimensions

CAMERA_OVERLAP_TOP = .10
CAMERA_OVERLAP_LEFT = .15  # Both measured against camera HEIGHT.
CAMERA_OVERLAP_OTHER = .05  # Preserve prior tolerance for other camera edges.
MIN_IMAGE_EDGE = 72  # 10% of the fixed logical output height; warning only.

def fit(size, box):
    scale = min(box.width/size[0], box.height/size[1])
    w, h = size[0]*scale, size[1]*scale
    return Rect(box.x+(box.width-w)/2, box.y+(box.height-h)/2, w, h)

def free_rectangles(config, bounds=None):
    w, h, _, exclusion = geometry(config)
    bounds = bounds or Rect(0, 0, w, h)
    if not exclusion or not bounds.intersects(exclusion):
        return [bounds]
    left, top = bounds.x, bounds.y
    right, bottom = left+bounds.width, top+bounds.height
    result = [Rect(left, top, min(right, exclusion.x)-left, bounds.height),
              Rect(left, top, bounds.width, min(bottom, exclusion.y)-top),
              Rect(max(left, exclusion.x+exclusion.width), top, right-max(left, exclusion.x+exclusion.width), bounds.height),
              Rect(left, max(top, exclusion.y+exclusion.height), bounds.width, bottom-max(top, exclusion.y+exclusion.height))]
    return [r for r in result if r.width > 0 and r.height > 0]

def camera_core(camera):
    left = camera.height*CAMERA_OVERLAP_LEFT
    top = camera.height*CAMERA_OVERLAP_TOP
    other = camera.height*CAMERA_OVERLAP_OTHER
    return Rect(camera.x+left, camera.y+top, max(0, camera.width-left-other), max(0, camera.height-top-other))

def arrangement_score(boxes, reference=None):
    # Concave area rewards useful sizes for every image, not one huge winner.
    score = sum(math.sqrt(b.width*b.height) for b in boxes)
    if reference:
        violations = pairs = 0
        for i, original in enumerate(reference):
            for j in range(i+1, len(reference)):
                other = reference[j]
                a, b = boxes[i], boxes[j]
                if original.y+original.height <= other.y+1e-8:
                    matches = a.y+a.height <= b.y+1e-8
                elif other.y+other.height <= original.y+1e-8:
                    matches = b.y+b.height <= a.y+1e-8
                elif original.x+original.width <= other.x+1e-8:
                    matches = a.x+a.width <= b.x+1e-8
                elif other.x+other.width <= original.x+1e-8:
                    matches = b.x+b.width <= a.x+1e-8
                else:
                    continue
                pairs += 1
                violations += not matches
        if pairs:
            score *= 1-.35*violations/pairs
    return score

def grid_in_rectangle(sizes, area, reference=None):
    best, best_score = None, -1
    for columns in range(1, len(sizes)+1):
        rows = math.ceil(len(sizes)/columns)
        cw = (area.width-16*(columns-1))/columns
        ch = (area.height-16*(rows-1))/rows
        if cw <= 0 or ch <= 0:
            continue
        boxes = tuple(fit(size, Rect(area.x+(i%columns)*(cw+16), area.y+(i//columns)*(ch+16), cw, ch)) for i, size in enumerate(sizes))
        score = arrangement_score(boxes, reference)
        if len(sizes) >= 3 and (rows == 1 or columns == 1):
            score *= .9  # Prefer compact multi-row grids over long strips.
        if score > best_score:
            best, best_score = boxes, score
    return best

def partitions(config, bounds):
    """Two disjoint tilings of the entire available area around any camera."""
    _, _, _, obstacle = geometry(config)
    if not obstacle or not bounds.intersects(obstacle):
        return [(bounds,)]
    x0, y0 = bounds.x, bounds.y
    x1, y1 = x0+bounds.width, y0+bounds.height
    left, right = max(x0, obstacle.x), min(x1, obstacle.x+obstacle.width)
    top, bottom = max(y0, obstacle.y), min(y1, obstacle.y+obstacle.height)
    vertical = (Rect(x0, y0, left-x0, y1-y0), Rect(right, y0, x1-right, y1-y0),
                Rect(left, y0, right-left, top-y0), Rect(left, bottom, right-left, y1-bottom))
    horizontal = (Rect(x0, y0, x1-x0, top-y0), Rect(x0, bottom, x1-x0, y1-bottom),
                  Rect(x0, top, left-x0, bottom-top), Rect(right, top, x1-right, bottom-top))
    return [tuple(r for r in layout if r.width > 0 and r.height > 0) for layout in (vertical, horizontal)]

def pack_partition(sizes, regions, reference=None):
    """For up to eight images consider every allocation; larger sets use greedy."""
    n = len(sizes)
    if n > 8:
        groups = [[] for _ in regions]
        for index, size in enumerate(sizes):
            def score(region_index):
                trial = [list(g) for g in groups]
                trial[region_index].append(index)
                placed = []
                for group, region in zip(trial, regions):
                    if group:
                        boxes = grid_in_rectangle([sizes[i] for i in group], region,
                                                  tuple(reference[i] for i in group) if reference else None)
                        if boxes is None:
                            return -1
                        placed.extend(zip(group, boxes))
                placed.sort()
                return arrangement_score([b for _, b in placed], tuple(reference[i] for i, _ in placed) if reference else None)
            groups[max(range(len(regions)), key=score)].append(index)
        result = [None]*n
        for group, region in zip(groups, regions):
            if group:
                boxes = grid_in_rectangle([sizes[i] for i in group], region,
                                          tuple(reference[i] for i in group) if reference else None)
                if boxes is None:
                    return None
                for index, box in zip(group, boxes):
                    result[index] = box
        return tuple(result)

    @lru_cache(maxsize=None)
    def layout(region_index, mask):
        indices = [i for i in range(n) if mask & (1 << i)]
        boxes = grid_in_rectangle([sizes[i] for i in indices], regions[region_index],
                                  tuple(reference[i] for i in indices) if reference else None) if indices else ()
        return tuple(zip(indices, boxes)) if boxes is not None else None

    @lru_cache(maxsize=None)
    def solve(region_index, mask):
        if region_index == len(regions):
            return (0, ()) if mask == 0 else (-1, ())
        best = (-1, ())
        subset = mask
        while True:
            placed = layout(region_index, subset)
            if placed is not None:
                rest_score, rest = solve(region_index+1, mask ^ subset)
                if rest_score >= 0:
                    combined = sorted(placed+rest)
                    score = arrangement_score([box for _, box in combined],
                                              tuple(reference[i] for i, _ in combined) if reference else None)
                    if score > best[0]:
                        best = (score, placed+rest)
            if subset == 0:
                break
            subset = (subset-1) & mask
        return best
    score, placed = solve(0, (1 << n)-1)
    return tuple(box for _, box in sorted(placed)) if score >= 0 else None

def grid(sizes, config, text=False, reference=None):
    return automatic_grid(tuple(sizes), config, text, tuple(reference) if reference else None)

@lru_cache(maxsize=128)
def automatic_grid(sizes, config, text=False, reference=None):
    w, h, _, _ = geometry(config)
    bounds = Rect(w*.55, 96, w*.45-32, h-128) if text else Rect(0, 0, w, h)
    candidates = free_rectangles(config, bounds)
    if not candidates:
        raise LayoutError('Kamera nezanechává plochu pro obrázky')
    best, best_area = None, -1
    for area in candidates:
        boxes = grid_in_rectangle(sizes, area, reference)
        if boxes:
            score = arrangement_score(boxes, reference)
            if score > best_area:
                best, best_area = boxes, score
    for regions in partitions(config, bounds):
        if len(regions) < 2:
            continue
        boxes = pack_partition(sizes, regions, reference)
        if boxes and arrangement_score(boxes, reference) > best_area+1e-8:
            best, best_area = boxes, arrangement_score(boxes, reference)
    if best is None:
        raise LayoutError('Mřížka obrázků se nevejde')
    return best

def normalize(box, config):
    w, h, _, _ = geometry(config)
    return ImagePlacement(max(0, min(1, box.x/w)), max(0, min(1, box.y/h)), max(.000001, min(1, box.width/w)))


def with_image_box(document, section, item_id, output, box):
    """Freeze existing geometry before a single manual edit; never reshuffle peers."""
    pair = compose_pair(document, section)
    if output == 'stream' and section.stream_linked:
        positions = {p.item_id: normalize(p.box, document.stream) for p in pair[1].images}
        section = replace(section, stream_linked=False, images=tuple(
            replace(i, stream=positions[i.id]) for i in section.images))
    config = getattr(document, output)
    positions = {p.item_id: normalize(p.box, config) for p in pair[0 if output == 'hall' else 1].images}
    box = constrain(box, config)
    return replace(section, images=tuple(replace(i, **{
        output: normalize(box, config) if i.id == item_id else positions[i.id]
    }) for i in section.images))

def constrain(box, config):
    """Asymmetric edge intrusion limits are measured against camera height."""
    w, h, camera, _ = geometry(config)
    factor = min(1, w/box.width, h/box.height)
    box = Rect(max(0, min(w-box.width*factor, box.x)), max(0, min(h-box.height*factor, box.y)), box.width*factor, box.height*factor)
    if not camera:
        return box
    core = camera_core(camera)
    if core.width <= 0 or core.height <= 0:
        return box
    if not box.intersects(core):
        return box
    options = [replace(box, x=core.x-box.width), replace(box, x=core.x+core.width),
               replace(box, y=core.y-box.height), replace(box, y=core.y+core.height)]
    valid = [b for b in options if b.x >= 0 and b.y >= 0 and b.x+b.width <= w+1e-8 and b.y+b.height <= h+1e-8 and not b.intersects(core)]
    if not valid:
        candidates = free_rectangles(config)
        if not candidates:
            raise LayoutError('Obrázek se nevejde mimo kameru')
        return max((fit((box.width, box.height), r) for r in candidates), key=lambda b: b.width*b.height)
    return min(valid, key=lambda b: (b.x-box.x)**2+(b.y-box.y)**2)

def placement_box(placement, size, config):
    w, h, _, _ = geometry(config)
    return constrain(Rect(placement.x*w, placement.y*h, placement.width*w, placement.width*w*size[1]/size[0]), config)

def compose_pair(source, section, first=True):
    items = list(section.images)
    configs = (source.hall, source.stream)
    if not items:
        return tuple(OutputLayout(*geometry(c)[:2], (), *geometry(c)[2:]) for c in configs)
    assets = {a.id: a for a in source.media}
    sizes = [dimensions(assets[i.media_id].locator) for i in items]
    text = any(run.text for block in section.blocks for run in block.runs)
    hall_auto = grid(sizes, source.hall, text)
    hall_boxes = [placement_box(i.hall, size, source.hall) if i.hall else b for i, size, b in zip(items, sizes, hall_auto)]
    adapted = False
    if section.stream_linked:
        # A stable automatic reference gives size changes a consistent scale.
        # Translate the whole group together to preserve ordering and proportions.
        hw, hh, _, _ = geometry(source.hall)
        sw, sh, _, _ = geometry(source.stream)
        bounds = Rect(sw*.55, 96, sw*.45-32, sh-128) if text else None
        regions = free_rectangles(source.stream, bounds)
        def envelope(boxes):
            x, y = min(b.x for b in boxes), min(b.y for b in boxes)
            return Rect(x, y, max(b.x+b.width for b in boxes)-x, max(b.y+b.height for b in boxes)-y)
        baseline, group = envelope(hall_auto), envelope(hall_boxes)
        def mapped(region):
            scale = min(region.width/baseline.width, region.height/baseline.height,
                        region.width/group.width, region.height/group.height)
            gw, gh = group.width*scale, group.height*scale
            x = region.x+(group.x+group.width/2)/hw*region.width-gw/2
            y = region.y+(group.y+group.height/2)/hh*region.height-gh/2
            x = max(region.x, min(region.x+region.width-gw, x))
            y = max(region.y, min(region.y+region.height-gh, y))
            return [Rect(x+(b.x-group.x)*scale, y+(b.y-group.y)*scale, b.width*scale, b.height*scale) for b in hall_boxes]
        if not regions:
            raise LayoutError('Stream nemá místo pro obrázky')
        stream_boxes = max((mapped(r) for r in regions), key=lambda boxes: sum(b.width*b.height for b in boxes))
        chosen = max(regions, key=lambda r: sum(b.width*b.height for b in mapped(r)))
        desired_scale = min(chosen.width/baseline.width, chosen.height/baseline.height)
        actual_scale = stream_boxes[0].width/hall_boxes[0].width
        adapted = actual_scale < desired_scale-1e-8
        # Pure automatic image grids should use the available region fully.
        if all(i.hall is None for i in items):
            stream_boxes = grid(sizes, source.stream, text, hall_auto)
    else:
        auto = grid(sizes, source.stream, text, hall_auto)
        stream_boxes = [placement_box(i.stream, size, source.stream) if i.stream else b for i, size, b in zip(items, sizes, auto)]
    outputs = []
    for output_index, (config, boxes) in enumerate(zip(configs, (hall_boxes, stream_boxes))):
        w, h, camera, exclusion = geometry(config)
        warnings = []
        if output_index == 1 and adapted:
            warnings.append('Sestava se do streamu nevešla v požadované velikosti; byla proporčně zmenšena.')
        placed = []
        for index, (item, box) in enumerate(zip(items, boxes)):
            if not first and not item.repeat:
                continue
            placed.append(PlacedImage(item.id, assets[item.media_id].locator, box))
            if min(box.width, box.height) < MIN_IMAGE_EDGE:
                warnings.append(f'Obrázek {index+1} je příliš malý (kratší strana pod {MIN_IMAGE_EDGE} px).')
            if camera and box.intersects(camera):
                warnings.append('Část obrázku zakryje kamera (limit shora 10 %, zleva 15 % výšky kamery).')
            elif exclusion and box.intersects(exclusion):
                warnings.append('Obrázek zasahuje do bezpečného odstupu kamery.')
            if any(box.intersects(other.box) for other in placed[:-1]):
                warnings.append('Obrázky se překrývají.')
        outputs.append(OutputLayout(w, h, (), camera, exclusion, images=tuple(placed), warnings=tuple(dict.fromkeys(warnings))))
    return tuple(outputs)

"""Stationary projection routing and reversible navigation, without Tk."""
from itertools import zip_longest
from .projection_limits import DEFAULT_HALL_ROWS, row_limits

from .construct_parser import parse_construct
from .stationary_pages import LogicalSection, generate_pages, resolve_sections


MODES = {'legacy_scroll', 'stationary_hall', 'stationary_stream'}
# Compatibility only for configurations saved before mode was introduced.
OLD_NAMES = {
    'chvály sál – stacionární': 'stationary_hall',
    'chvály stream – stacionární': 'stationary_stream',
}


def style_mode(style):
    mode = style.get('mode', OLD_NAMES.get(style.get('name'), 'legacy_scroll'))
    if mode not in MODES:
        raise ValueError(f'Unknown projector mode: {mode!r}')
    return mode


def build_plan(song, variant_names, guide, hall_rows=DEFAULT_HALL_ROWS):
    """Interleave selected languages; every physical row counts toward capacity.

    Resolve selections before interleaving so original line numbers retain
    their meaning. Return legacy row positions for mixed projector setups.
    """
    variants = [next(v for v in song.variants if v.name == name)
                for name in variant_names]
    if not variants:
        raise ValueError('Stationary projection needs a selected language')
    legal = set(s.identifier for s in variants[0].sections)
    for variant in variants[1:]:
        legal.intersection_update(s.identifier for s in variant.sections)
    construct = parse_construct(guide, legal)
    resolved = [list(resolve_sections(construct, v)) for v in variants]
    sections, positions = [], {}
    legacy_position = 1
    for occurrences in zip(*resolved):
        rows = []
        for translations in zip_longest(*(s.lines for s in occurrences)):
            for row in translations:
                if row is not None:
                    rows.append(row)
                    positions[id(row)] = legacy_position
            legacy_position += 1
        sections.append(LogicalSection(occurrences[0].occurrence_id, tuple(rows),
                                       occurrences[0].append_to_previous))
    plan = generate_pages(sections, hall_rows)
    return plan, tuple(positions[id(c.stream_page.lines[0])] for c in plan.cues)


class CueNavigation:
    """Each song has an intro, cues, and an outro. Boundaries clamp.

    Crossing songs lands on the adjacent boundary, making every move exactly
    reversible, including empty songs. Explicit song selection resets to intro.
    """
    def __init__(self, plans):
        self.plans = tuple(plans)
        self.song = 0
        self.step = 0

    @property
    def last_step(self):
        return len(self.plans[self.song].cues) + 1 if self.plans else 0

    @property
    def cue(self):
        if self.plans and 0 < self.step < self.last_step:
            return self.plans[self.song].cues[self.step - 1]
        return None

    def select(self, song, step=0):
        if not self.plans:
            return
        self.song = max(0, min(song, len(self.plans) - 1))
        self.step = max(0, min(step, self.last_step))

    def move(self, direction, *, restart_previous_section=False):
        if direction not in (-1, 1):
            raise ValueError('Direction must be -1 or 1')
        if not self.plans:
            return
        previous_cue = self.cue
        if direction == 1 and self.step == self.last_step:
            if self.song + 1 < len(self.plans):
                self.select(self.song + 1)
        elif direction == -1 and self.step == 0:
            if self.song:
                self.select(self.song - 1)
                self.step = self.last_step
        else:
            self.step = max(0, min(self.step + direction, self.last_step))
        if (restart_previous_section and direction == -1 and previous_cue
                and self.cue and self.cue.occurrence_id != previous_cue.occurrence_id):
            occurrence = self.cue.occurrence_id
            while self.step > 1 and self.plans[self.song].cues[self.step - 2].occurrence_id == occurrence:
                self.step -= 1

    def diagnostic(self):
        cue = self.cue
        return (f'song={self.song + 1} step={self.step} '
                f'cue={cue.step_index + 1 if cue else "-"} '
                f'hall={cue.hall_page.index + 1 if cue else "-"} '
                f'stream={cue.stream_page.index + 1 if cue else "-"}')


class StationaryPageWidget:
    """Canvas adapter: update in place, never clear/repaint an unchanged page."""
    def __init__(self, canvas, style, fonts, mode, hall_rows=DEFAULT_HALL_ROWS):
        hall_rows, stream_rows = row_limits(hall_rows)
        self.canvas = canvas
        self.page = None
        limit = hall_rows if mode == 'stationary_hall' else stream_rows
        # Preserve the existing text area when the operator requests more rows.
        scale = min(1, DEFAULT_HALL_ROWS / limit) if mode == 'stationary_hall' else 1
        font = fonts[style['primaryFont']]
        if scale < 1:
            font = font.copy()
            size = font.cget('size')
            font.configure(size=(1 if size > 0 else -1) * max(1, int(abs(size) * scale)))
        self.font = font
        self.items = [canvas.create_text(
            style['x'], style['y'] + row * style['y1'] * scale,
            text='', anchor='n', fill=style['fill'],
            font=font, width=style.get('width', 1800),
        ) for row in range(limit)]

    def show_page(self, page):
        if page is self.page:
            return
        self.page = page
        rows = page.lines if page else ()
        for i, item in enumerate(self.items):
            self.canvas.itemconfigure(item, text=rows[i].text if i < len(rows) else '')

    def switchSource(self, source):
        self.show_page(None)

    def widgetRaise2top(self):
        for item in self.items:
            self.canvas.tag_raise(item)

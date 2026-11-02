"""Read-only originals; validate actual browser-serializer output with current desktop code."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from superpresenter.services.song_repository import SongRepository
from superpresenter.services.presentation_session import WidgetSource
from superpresenter.services.construct_parser import parse_construct, check_expansion

repo = SongRepository()
output = ROOT / 'web-song-editor' / 'test-output'
report = json.loads((output / 'corpus.json').read_text(encoding='utf-8'))
checked = 0
for row in report:
    if 'output' not in row:
        continue
    before = repo.load(row['source'])
    after = repo.load(row['output'])
    if 'song-id' not in before.attributes:
        before.attributes['song-id'] = after.attributes['song-id']
    assert before == after, row['source']
    # Unknown root metadata is not part of dataclass equality for ElementTree nodes.
    import xml.etree.ElementTree as ET
    assert [(i, ET.tostring(e)) for i,e in before.extra_elements] == [(i, ET.tostring(e)) for i,e in after.extra_elements]
    a, b = WidgetSource(row['source']), WidgetSource(row['output'])
    assert a.err == b.err == 0, row['source']
    variants = a.importVariants()
    sections = a.importSections(variants)
    # Compare actual visible content separately from the newly assigned legacy ID.
    old, new = a.importSlide(variants, sections), b.importSlide(variants, sections)
    old.pop('song-id', None); new.pop('song-id', None)
    assert old == new, row['source']
    for repetition in after.repetitions:
        guide = ' '.join(line.strip() for line in repetition.guide.splitlines() if line.strip())
        construct = parse_construct(guide, sections)
        check_expansion(construct, {sid: sum(len(new[v][sid]['lines']) for v in variants) for sid in sections})
    checked += 1
song = repo.load(output / 'new-song.xml')
widget = WidgetSource(str(output / 'new-song.xml'))
assert widget.err == 0 and widget.load_warning is None
assert song.guide == 'v1 r1 v2 r1'
assert song.variants[0].sections[2].lines == ['Změněný refrén < & >']
assert len(parse_construct(song.guide, ['v1','v2','r1']).instructions) == 4
print(f'OK: {checked} real XML roundtrips + new song; SongRepository, WidgetSource, construct parser. No originals written.')
browser = output / 'browser-song.xml'
if browser.exists():
    song = repo.load(browser)
    widget = WidgetSource(str(browser))
    assert widget.err == 0 and widget.load_warning is None
    assert song.guide == 'v1 r1 v2 r1'
    assert song.variants[0].sections[2].lines == ['Změněný refrén']
    parse_construct(song.guide, ['v1', 'v2', 'r1'])
    print('OK: actual Chromium download accepted by current desktop loader.')
else:
    print('NOT CHECKED: actual browser download (run Playwright first).')

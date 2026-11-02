"""Read-only originals; validate actual browser-serializer output with current desktop code."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from superpresenter.services.song_repository import SongRepository
from superpresenter.services.presentation_session import WidgetSource
from superpresenter.services.construct_parser import parse_construct, check_expansion, RepeatGroup, ConstructError

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
    def semantic(e):
        return (e.tag, dict(e.attrib), e.text, [semantic(child) for child in e])
    assert [(i, semantic(e)) for i,e in before.extra_elements] == [(i, semantic(e)) for i,e in after.extra_elements]
    assert before.repetition_locations == after.repetition_locations
    a, b = WidgetSource(row['source']), WidgetSource(row['output'])
    assert a.err == b.err == 0, row['source']
    variants = a.importVariants()
    sections = a.importSections(variants)
    # Compare actual visible content separately from the newly assigned legacy ID.
    old, new = a.importSlide(variants, sections), b.importSlide(variants, sections)
    old.pop('song-id', None); new.pop('song-id', None)
    # Empty title uses the current filename in WidgetSource, not XML semantics.
    if not before.title:
        old.pop('name', None); new.pop('name', None)
    assert old == new, row['source']
    for variant, web_sections in zip(after.variants, row['lines'], strict=True):
        for section in web_sections:
            assert section['lines'] == new[variant.name][section['id']]['lines'], (row['source'], variant.name, section['id'])
    ids = list(dict.fromkeys(s.identifier for v in after.variants for s in v.sections))
    def tree(nodes):
        return [({'children': tree(n.children), 'repeat': n.repeat} if isinstance(n, RepeatGroup) else {
            'section': n.section, 'pinned': n.pinned,
            **({'start': n.start_line} if n.start_line is not None else {}),
            **({'end': n.end_line} if n.end_line is not None else {}),
        }) for n in nodes]
    for repetition, web in zip(after.repetitions, row['guides'], strict=True):
        guide = ' '.join(line.strip() for line in repetition.guide.splitlines() if line.strip())
        try:
            construct = parse_construct(guide, ids)
        except ConstructError:
            assert 'error' in web, (row['source'], guide, web)
            continue
        assert tree(construct.instructions) == web['tree'], (row['source'], guide)
        if not web['diagnostic']:
            check_expansion(construct, {sid: max(len(new[v][sid]['lines']) for v in variants) * len(variants) for sid in sections}, copies=len(variants))
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

advanced = output / 'browser-advanced.xml'
if advanced.exists():
    song = repo.load(advanced)
    assert song.attributes['song-id'] == '11111111-1111-4111-8111-111111111111'
    assert song.main_repetition == 'short'
    assert [v.name for v in song.variants] == ['cz', 'uk', 'english']
    assert song.repetitions[0].name == 'nested' and song.repetition_locations[0][0] == 0
    assert song.repetitions[1].guide == '(v1.1:2)*4'
    assert all(s.identifier != 'r' for v in song.variants for s in v.sections)
    for r in song.repetitions:
        parse_construct(r.guide, ['v1'])
    widget = WidgetSource(str(advanced))
    assert widget.err == 0 and widget.load_warning is None
    print('OK: Chromium multilingual/group edits, default and deletion accepted by desktop.')
legacy = output / 'browser-legacy.xml'
if legacy.exists():
    song = repo.load(legacy)
    assert song.guide == 'V1 missing' and song.variants[0].sections[0].lines == ['Changed']
    print('OK: invalid legacy guide preserved verbatim through browser text edit/export.')

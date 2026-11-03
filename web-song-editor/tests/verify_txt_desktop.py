"""Verify actual TXT → browser XML using the current desktop loader (read-only)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from superpresenter.services.song_repository import SongRepository
from superpresenter.services.presentation_session import WidgetSource

path = ROOT / 'web-song-editor/test-output/browser-txt.xml'
song = SongRepository().load(path)
assert song.title == 'Ukázková píseň'
assert song.guide == 'v1 r1 v2 r1'
assert song.attributes['song-id']
widget = WidgetSource(str(path))
assert widget.err == 0 and widget.load_warning is None
variants = widget.importVariants()
slide = widget.importSlide(variants, widget.importSections(variants))
assert slide[variants[0]]['r1']['lines'] == ['Upravený český refrén.']
assert slide[variants[0]]['v1']['lines'] == ['Žluťoučký kůň.']
assert slide[variants[1]]['v1']['lines'] == ['Український текст']
print('TXT browser XML: SongRepository + WidgetSource OK, guide v1 r1 v2 r1, Czech and identity present.')

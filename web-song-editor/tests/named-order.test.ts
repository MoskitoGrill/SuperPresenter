import { it, expect } from 'vitest';
import { importXml, exportXml } from '../src/xml/songXml';
import { saveNamedOrder } from '../src/ui/namedOrder';

it('overwrites a named nested target transactionally and preserves metadata and unrelated guides', () => {
  const song = importXml('<slide name="Píseň" song-id="11111111-1111-4111-8111-111111111111"><variant name="cz"><section name="v1">A</section><repetition name="kapela 1" custom="keep">v1</repetition></variant><meta flag="x"/><repetition name="default" main="1">(v1)*2</repetition><repetition name="jiné">v1</repetition></slide>');
  const draft = song.selectedRepetition.cloneNode(true) as Element; draft.textContent = 'v1 v1 v1';
  const output = saveNamedOrder(song, song.repetitions.indexOf(song.selectedRepetition), draft, ' kapela 1 ');
  expect(song.repetitions[0].textContent).toBe('v1');
  expect(song.selectedRepetition.textContent).toBe('(v1)*2');
  expect(output.selectedRepetition.parentElement?.tagName).toBe('variant');
  expect(output.selectedRepetition.getAttribute('custom')).toBe('keep');
  expect(output.selectedRepetition.textContent).toBe('v1 v1 v1');
  expect(output.repetitions).toHaveLength(3);
  expect(output.root.querySelector('meta')?.getAttribute('flag')).toBe('x');
  expect(output.id).toBe(song.id);
  expect(importXml(exportXml(output)).selectedRepetition.textContent).toBe('v1 v1 v1');
});

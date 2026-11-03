import { describe, it, expect } from 'vitest';
import { newSong } from '../src/domain/song';
import { exportTxt, parseTxt, songFromTxt, txtTemplate, updateLanguageFromTxt } from '../src/io/songTxt';
import { exportXml, importXml } from '../src/xml/songXml';

const human = 'Název: Ukázková píseň\n\nSloka 1:\nText první sloky.\n\nRefrén:\nText refrénu.\n\nSloka 2:\nText druhé sloky.\n\nRefrén:\n';
describe('simple offline TXT', () => {
  it('recognizes Czech, CRLF/BOM, case, accents, optional colon and repeated empty blocks', () => {
    const p = parseTxt('\uFEFF' + human.replace('Sloka 1:', 'SLOKA 1').replace('Refrén:', 'REFREN').replace(/\n/g, '\r\n') + '\r\nrefren\r\n');
    expect(p.problems).toEqual([]); expect(p.conflicts).toEqual([]);
    expect(p.sections).toHaveLength(3); expect(p.order).toEqual(['v1','r1','v2','r1','r1']);
    expect(songFromTxt(p).title).toBe('Ukázková píseň');
  });
  it('rejects forward/missing empty references and does not split internal blank lines', () => {
    expect(parseTxt('Název: A\nBridge 2:\n\nSloka:\nA\n\nB\n').problems.join()).toContain('neexistující');
    const p = parseTxt('Název: A\nSloka:\nA\n\nB\n');
    expect(p.sections[0].text).toBe('A\n\nB'); expect(p.sections).toHaveLength(1);
    expect(() => songFromTxt(parseTxt('Název: A\nRefrén:\n'))).toThrow();
  });
  it('reports conflicts, explicitly creates variants and preserves the first text', () => {
    const source = human + '\nRefrén:\nJiný refrén\n\nRefrén:\n';
    expect(parseTxt(source).conflicts).toHaveLength(1);
    const p = parseTxt(source, true);
    expect(p.sections.find(s => s.id === 'r1')?.text).toBe('Text refrénu.');
    expect(p.sections.find(s => s.id === 'r2')?.text).toBe('Jiný refrén');
    expect(p.order.slice(-2)).toEqual(['r2','r2']);
    const repeated = parseTxt(source + '\nRefrén\nText refrénu.\n\nRefrén\nJiný refrén\n', true);
    expect(repeated.sections.filter(s => s.id.startsWith('r'))).toHaveLength(2);
    expect(repeated.order.slice(-2)).toEqual(['r1','r2']);
  });
  it('exports plain Czech without headers/colons and keeps identity only on explicit language update', () => {
    const song = songFromTxt(parseTxt(human));
    song.variants[0].setAttribute('name', 'čeština — zkouška');
    song.repetitions[0].setAttribute('name', 'Hlavní pořadí');
    song.sections()[0].textContent = 'Žluťoučký kůň & < >\n\nRefrén:\n\\doslova';
    const text = exportTxt(song);
    expect(text).toContain('\r\n'); expect(text[0]).toBe('\uFEFF');
    expect(text).not.toContain('# SuperPresenter'); expect(text).not.toContain(song.id);
    expect(text).toContain('\r\nSloka 1\r\n');
    expect(text).not.toContain('Název:');
    expect(songFromTxt(parseTxt(text)).id).not.toBe(song.id);
    const next = updateLanguageFromTxt(song, parseTxt(text), 0, 0).song;
    expect(next.id).toBe(song.id); expect(next.sections()[0].textContent).toBe(song.sections()[0].textContent);
    expect(next.variants[0].getAttribute('name')).toBe('čeština — zkouška');
    expect(next.repetitions[0].getAttribute('name')).toBe('Hlavní pořadí');
    expect(importXml(exportXml(next)).id).toBe(song.id);
  });
  it('projects a selected language/order with metadata, but blocks nonrepresentable text/trees', () => {
    const base = () => songFromTxt(parseTxt(human));
    const multilingual = base(); multilingual.addVariant('ukr'); multilingual.addRepetition('jiné');
    multilingual.root.setAttribute('custom', 'x');
    multilingual.sections(multilingual.variants[1]).forEach(s => { s.textContent = 'Український ' + s.getAttribute('name'); });
    const exported = exportTxt(multilingual, 1, 0);
    expect(exported).toContain('Український'); expect(exported).not.toContain('Text první');
    expect(exported).not.toContain('custom');
    for (const change of [
      (s: ReturnType<typeof base>) => { s.repetitions[0].textContent = '(v1 r1)*2'; },
      (s: ReturnType<typeof base>) => s.addSection('v'),
      (s: ReturnType<typeof base>) => { s.sections()[0].textContent = ''; },
    ]) { const song = base(); change(song); expect(() => exportTxt(song)).toThrow('XML'); }
    expect(() => exportTxt(newSong())).toThrow();
  });
  it('accepts attached numbers, case, accents, unnumbered duplicates and a filled empty template', () => {
    for (const heading of ['sloka 1', 'sloka1', 'Sloka 1', 'SLOKA 1', 'Sloka', 'slóka1:']) {
      const p = parseTxt(`Moje píseň\n\n${heading}\nStejný text\n\nSLOKA1\nStejný text\n\nsloka\n`);
      expect(p.problems).toEqual([]); expect(p.conflicts).toEqual([]);
      expect(p.sections).toEqual([{ id: 'v1', text: 'Stejný text' }]); expect(p.order).toEqual(['v1','v1','v1']);
    }
    expect(txtTemplate).not.toContain(':'); expect(txtTemplate).not.toContain('#');
    expect(txtTemplate).toContain('Bridge 1');
    const filled = txtTemplate.replace('Sloka 1', 'Sloka 1\r\nMoje sloka').replace('Refrén 1', 'Refrén 1\r\nMůj refrén').replace('Bridge 1', 'Bridge 1\r\nMůj bridge');
    expect(parseTxt(filled).sections).toHaveLength(3); expect(parseTxt(filled).problems).toEqual([]);
    expect(parseTxt(txtTemplate).problems.length).toBeGreaterThan(0);
    const old = parseTxt('# SuperPresenter TXT 1\n# {"id":"11111111-1111-4111-8111-111111111111","language":"ukr","order":"jiné","main":null}\n' + human);
    expect(songFromTxt(old).id).not.toBe('11111111-1111-4111-8111-111111111111');
    expect(songFromTxt(old).variants[0].getAttribute('name')).toBe('čeština');
  });
  it('updates one language atomically while preserving other languages, metadata and all guides', () => {
    const song = songFromTxt(parseTxt(human)); song.addVariant('ukr');
    const ukrainian = song.variants[1]; song.sections(ukrainian)[0].textContent = 'Український';
    song.sections()[0].setAttribute('custom', 'keep');
    song.root.setAttribute('custom', 'keep');
    song.addSection('b'); song.sections().find(s => s.getAttribute('name') === 'b1')!.textContent = 'Vynechaná část';
    const nested = song.addRepetition('pokročilé'); ukrainian.append(nested); nested.textContent = '(v1 r1)*2'; nested.setAttribute('custom', 'keep');
    const before = exportXml(song);
    const p = parseTxt(human.replace('Text refrénu.', 'Změněný refrén.'));
    const result = updateLanguageFromTxt(song, p, 0, 0);
    expect(result.addedOrder).toBe(false); expect(result.song.id).toBe(song.id);
    expect(exportXml(song)).toBe(before);
    expect(result.song.variants[1].outerHTML).toBe(ukrainian.outerHTML);
    expect(result.song.sections()[0].getAttribute('custom')).toBe('keep');
    expect(result.song.sections().find(s => s.getAttribute('name') === 'b1')!.textContent).toBe('Vynechaná část');
    expect(result.song.repetitions.map(r => r.outerHTML)).toEqual(song.repetitions.map(r => r.outerHTML));
    const changed = updateLanguageFromTxt(song, parseTxt(human + '\nBridge 2\nNový text\n'), 0, 0);
    expect(changed.addedOrder).toBe(true); expect(changed.song.repetitions.at(-1)!.getAttribute('main')).toBeNull();
    expect(changed.song.repetitions.at(-1)!.textContent).toBe('v1 r1 v2 r1 b2');
    expect(changed.song.sections(changed.song.variants[1]).some(s => s.getAttribute('name') === 'b2')).toBe(false);
    expect(changed.song.selectedRepetition.textContent).toBe('v1 r1 v2 r1');
  });
});

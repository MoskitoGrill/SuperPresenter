import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { newSong, presentationLines } from '../src/domain/song';
import { importXml, exportXml } from '../src/xml/songXml';
import { parseSimple } from '../src/construct/simple';
import { parseTree, serializeTree, budget } from '../src/construct/tree';

describe('editor model and safe XML', () => {
  it('shares chorus references, keeps identity and creates an explicit copy', () => {
    const song = newSong(); song.title = 'Zkouška & naděje';
    song.addSection('v'); song.addSection('r');
    song.sections()[0].textContent = 'První sloka';
    song.sections()[1].textContent = 'Druhá sloka';
    song.sections()[2].textContent = 'Změněný refrén < & >';
    song.selectedRepetition.textContent = 'v1 r1 v2 r1';
    const xml = exportXml(song), roundtrip = importXml(xml);
    expect(roundtrip.id).toBe(song.id);
    expect(roundtrip.steps(roundtrip.selectedRepetition)).toEqual(['v1','r1','v2','r1']);
    expect(roundtrip.sections()[2].textContent).toBe('Změněný refrén < & >');
    const copy = song.copy('Vlastní kopie'); expect(copy.id).not.toBe(song.id);
    expect(song.title).toBe('Zkouška & naděje');
    mkdirSync('test-output', { recursive: true }); writeFileSync('test-output/new-song.xml', xml);
  });
  it('preserves unknown metadata, attributes, nested repetition, Unicode and whitespace', () => {
    const song = importXml('<slide name="Píseň" custom="yes"><meta flag="a"><x>inertní &amp; text</x></meta><variant name="український" attr="v"><section name="r" attr="s">  A\n\nБ&#13;C\n</section><repetition name="default" main="YES" extra="r"> r\nr </repetition></variant></slide>');
    const output = exportXml(song), again = importXml(output);
    expect(again.root.querySelector('meta')?.outerHTML).toBe(song.root.querySelector('meta')?.outerHTML);
    expect(again.sections()[0].textContent).toBe('  A\n\nБ\rC\n');
    expect(again.selectedRepetition.parentElement?.tagName).toBe('variant');
    expect(again.selectedRepetition.textContent).toBe(' r\nr ');
    expect(again.root.getAttribute('custom')).toBe('yes');
  });
  it.each([
    '<!DOCTYPE slide><slide/>', '<slide>',
    '<slide song-id="bad"/>',
    '<slide><variant name="x"><section name="v1"><b>x</b></section></variant><repetition name="default">v1</repetition></slide>',
    '<?xml version="1.0" encoding="windows-1250"?><slide/>',
  ])('rejects unsafe or unsupported import: %s', xml => expect(() => importXml(xml)).toThrow());
  it('refuses invalid guides and bounded expansion', () => {
    for (const guide of ['v1 @r1','v1.1','V1','v1*4','', 'v1 '.repeat(5000)]) expect(() => parseSimple(guide,['v1','r1'])).toThrow();
    const song = newSong(); song.sections()[0].textContent = 'a\n'.repeat(4097); expect(song.diagnostics(song.selectedRepetition).join()).toContain('4096'); expect(() => exportXml(song)).not.toThrow();
    expect(() => importXml('<slide><meta><variant><repetition name="hidden">v1</repetition></variant></meta><variant name="x"><section name="v1"/></variant><repetition name="default">v1</repetition></slide>')).toThrow('metadat');
  });
  it('removes every reference, with an atomic rejection if a guide becomes empty', () => {
    const song = newSong(); expect(() => song.removeSection('v1')).toThrow(); expect(song.sections()).toHaveLength(1);
    song.addSection('r'); song.selectedRepetition.textContent = 'v1 r1 v1'; song.removeSection('v1');
    expect(song.steps(song.selectedRepetition)).toEqual(['r1']);
  });
});

it('edits ordered trees, preserves legacy guides and blocks unsafe deletion atomically', () => {
  const song = newSong(); song.addSection('r'); song.sections()[0].textContent = 'A\nB\nC'; song.sections()[1].textContent = 'R';
  const guide = '((v1.1:2) @r1)*3 v1'; song.selectedRepetition.textContent = guide;
  expect(song.diagnostics(song.selectedRepetition)).toEqual([]);
  expect(parseTree(serializeTree(song.tree(song.selectedRepetition)), song.ids)).toEqual(song.tree(song.selectedRepetition));
  expect(importXml(exportXml(song)).selectedRepetition.textContent).toBe(guide);
  song.removeSection('r1'); expect(song.selectedRepetition.textContent).toBe('((v1.1:2)*2)*3 v1');
  song.selectedRepetition.textContent = 'v1 missing'; const before = exportXml(song);
  expect(song.diagnostics(song.selectedRepetition).join()).toContain('missing');
  expect(() => song.removeSection('v1')).toThrow(); expect(exportXml(song)).toBe(before);
  song.title = 'Edit'; expect(importXml(exportXml(song)).selectedRepetition.textContent).toBe('v1 missing');
  expect(() => parseTree('(v1)*999999',song.ids)).toThrow('4096');
  expect(() => parseTree('('.repeat(33) + 'v1' + ')'.repeat(33),song.ids)).toThrow();
  expect(() => budget(parseTree('(v1.1:2)*2049',song.ids))).toThrow();
});

it('keeps nested and duplicate repetitions, main fallback, languages and identities', () => {
  const song = importXml('<slide name="X"><variant name="cz"><section name="v1">X</section><repetition name="same" main="yes">v1</repetition></variant><repetition name="same" main="1">(v1)</repetition></slide>');
  const id = song.id; song.addVariant('uk'); const rep = song.addRepetition('live'); song.setDefault(rep);
  expect(song.selectedRepetition).toBe(rep); expect(song.repetitions[0].parentElement).toBe(song.variants[0]);
  expect(importXml(exportXml(song)).id).toBe(id); expect(song.copy('copy').id).not.toBe(id);
  expect(song.repetitions.map(r=>r.getAttribute('name'))).toEqual(['same','same','live']);
  expect(song.variants[1].getAttribute('name')).toBe('uk');
  rep.removeAttribute('main'); expect(song.selectedRepetition).toBe(song.repetitions[0]);
});

function xmlFiles(path: string): string[] {
  return readdirSync(path, { withFileTypes: true }).flatMap(e => e.isDirectory() ? xmlFiles(join(path,e.name)) : e.name.endsWith('.xml') ? [join(path,e.name)] : []);
}
it('removes a language without losing nested/default/duplicate orders or identity', () => {
  const song = importXml('<slide name="X"><repetition name="same">v1</repetition><variant name="cz"><section name="v1">Keep</section></variant><variant name="uk"><section name="v1">Remove</section><section name="solo">Only here</section><repetition name="same" main="yes" custom="keep"> (v1)*3 </repetition><repetition name="unique">solo</repetition></variant><repetition name="last">v1</repetition></slide>');
  const id = song.id, reps = song.repetitions, main = song.selectedRepetition;
  song.removeVariant(song.variants[1]);
  expect(song.variants).toHaveLength(1); expect(song.sections()[0].textContent).toBe('Keep');
  expect(song.repetitions).toEqual(reps); expect(song.selectedRepetition).toBe(main);
  expect(main.parentElement).toBe(song.root); expect(main.textContent).toBe(' (v1)*3 '); expect(main.getAttribute('custom')).toBe('keep');
  expect(song.diagnostics(reps[2]).join()).toContain('solo');
  const again = importXml(exportXml(song)); expect(again.id).toBe(id);
  expect(again.repetitions.map(r => r.textContent)).toEqual(reps.map(r => r.textContent));
  const before = exportXml(song); expect(() => song.removeVariant(song.variants[0])).toThrow('Poslední'); expect(exportXml(song)).toBe(before);
});
it('classifies the real corpus without touching originals; exports supported songs for Python verification', () => {
  const files = [...xmlFiles(resolve('../songs')), ...xmlFiles(resolve('../Testovací písně'))];
  const report: { source: string; output?: string; reason?: string; guides?: unknown[]; lines?: unknown }[] = [];
  mkdirSync('test-output', { recursive: true });
  for (const [i,path] of files.entries()) {
    let song;
    try { song = importXml(new TextDecoder('utf-8', { fatal: true }).decode(readFileSync(path))); }
    catch (error) { report.push({ source: path, reason: (error as Error).message }); continue; }
    const output = exportXml(song), again = importXml(output);
    expect(again.id).toBe(song.id);
    const semantic = (e: Element): unknown => ({ tag: e.tagName, attributes: Object.fromEntries(Array.from(e.attributes).map(a => [a.name,a.value])), content: e.children.length ? Array.from(e.children).map(semantic) : e.textContent });
    expect(semantic(again.root)).toEqual(semantic(song.root));
    const target = resolve(`test-output/roundtrip-${i}.xml`); writeFileSync(target,output);
    report.push({ source: path, output: target, guides: song.repetitions.map(r => { try { return { tree: song.tree(r), diagnostic: song.diagnostics(r) }; } catch(e) { return { error: (e as Error).message }; } }), lines: song.variants.map(v => song.sections(v).map(s => ({ id: s.getAttribute('name'), lines: presentationLines(s.textContent ?? '') }))) });
  }
  writeFileSync('test-output/corpus.json', JSON.stringify(report,null,2));
  expect(report.filter(r => r.output).length).toBe(files.length);
  console.log(`Corpus: ${report.length} files; ${report.filter(r=>r.output).length} editable, ${report.filter(r=>r.reason).length} safely rejected`);
}, 30000);

import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { newSong } from '../src/domain/song';
import { importXml, exportXml } from '../src/xml/songXml';
import { parseSimple } from '../src/construct/simple';

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
    '<slide><variant name="x"><section name="v1">x</section></variant><repetition name="default">(v1)*2</repetition></slide>',
    '<?xml version="1.0" encoding="windows-1250"?><slide/>',
    '<slide><variant name="x"><section name="v1"/></variant><repetition name="a">v1</repetition><repetition name="a">v1</repetition></slide>',
  ])('rejects unsafe or unsupported import: %s', xml => expect(() => importXml(xml)).toThrow());
  it('refuses invalid guides and bounded expansion', () => {
    for (const guide of ['v1 @r1','v1.1','V1','v1*4','', 'v1 '.repeat(5000)]) expect(() => parseSimple(guide,['v1','r1'])).toThrow();
    const song = newSong(); song.sections()[0].textContent = 'a\n'.repeat(4097); expect(() => exportXml(song)).toThrow();
    expect(() => importXml('<slide><meta><variant><repetition name="hidden">v1</repetition></variant></meta><variant name="x"><section name="v1"/></variant><repetition name="default">v1</repetition></slide>')).toThrow('metadat');
  });
  it('removes every reference, with an atomic rejection if a guide becomes empty', () => {
    const song = newSong(); expect(() => song.removeSection('v1')).toThrow(); expect(song.sections()).toHaveLength(1);
    song.addSection('r'); song.selectedRepetition.textContent = 'v1 r1 v1'; song.removeSection('v1');
    expect(song.steps(song.selectedRepetition)).toEqual(['r1']);
  });
});

function xmlFiles(path: string): string[] {
  return readdirSync(path, { withFileTypes: true }).flatMap(e => e.isDirectory() ? xmlFiles(join(path,e.name)) : e.name.endsWith('.xml') ? [join(path,e.name)] : []);
}
it('classifies the real corpus without touching originals; exports supported songs for Python verification', () => {
  const files = [...xmlFiles(resolve('../songs')), ...xmlFiles(resolve('../Testovací písně'))];
  const report: { source: string; output?: string; reason?: string }[] = [];
  mkdirSync('test-output', { recursive: true });
  for (const [i,path] of files.entries()) {
    let song;
    try { song = importXml(new TextDecoder('utf-8', { fatal: true }).decode(readFileSync(path))); }
    catch (error) { report.push({ source: path, reason: (error as Error).message }); continue; }
    const output = exportXml(song), again = importXml(output);
    expect(again.id).toBe(song.id); expect(again.root.outerHTML).toBe(song.root.outerHTML);
    const target = resolve(`test-output/roundtrip-${i}.xml`); writeFileSync(target,output);
    report.push({ source: path, output: target });
  }
  writeFileSync('test-output/corpus.json', JSON.stringify(report,null,2));
  expect(report.filter(r => r.output).length).toBeGreaterThan(100);
  console.log(`Corpus: ${report.length} files; ${report.filter(r=>r.output).length} editable, ${report.filter(r=>r.reason).length} safely rejected`);
}, 30000);

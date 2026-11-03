import { describe, it, expect } from 'vitest';
import { mkdirSync, writeFileSync } from 'node:fs';
import { zipSync, unzipSync, strToU8, strFromU8 } from 'fflate';
import { docxFromText, docxTemplate, exportDocx, readDocx, DOCX_MAX_BYTES } from '../src/io/songDocx';
import { parseTxt, songFromTxt, updateLanguageFromTxt, txtTemplate } from '../src/io/songTxt';
import { exportXml } from '../src/xml/songXml';

const sample = 'Ukázková píseň\r\n\r\nSloka 1\r\nŽluťoučký kůň & <text>.\r\n\r\nDruhý řádek\r\n\r\nRefrén 1\r\nČeský refrén\r\n\r\nSloka 2\r\nDruhá sloka\r\n\r\nRefrén 1\r\n';
function patchDocument(change: (xml: string) => string) {
  const parts = unzipSync(docxFromText(sample));
  parts['word/document.xml'] = strToU8(change(strFromU8(parts['word/document.xml'])));
  return zipSync(parts);
}
describe('Word DOCX transport using the same song parser as TXT', () => {
  it('roundtrips Czech, XML entities, empty paragraphs, repeated sections and template', () => {
    const song = songFromTxt(parseTxt(sample));
    const bytes = exportDocx(song), result = readDocx(bytes), parsed = parseTxt(result.text);
    expect(parsed.sections).toEqual(parseTxt(sample).sections);
    expect(parsed.order).toEqual(['v1','r1','v2','r1']); expect(parsed.problems).toEqual([]);
    expect(result.text).not.toContain(song.id); expect(result.text).not.toContain('# SuperPresenter');
    expect(parseTxt(readDocx(docxTemplate()).text).order).toEqual(['v1','r1','b1']);
    expect(readDocx(docxTemplate()).text).toBe(txtTemplate.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n').replace(/\n$/, ''));
    mkdirSync('test-output', { recursive: true });
    writeFileSync('test-output/docx-song.docx', bytes); writeFileSync('test-output/docx-template.docx', docxTemplate());
  });
  it('accepts split formatted runs, alternate namespace prefixes, manual line breaks and tabs', () => {
    const bytes = patchDocument(xml => xml.replace('<w:t xml:space="preserve">Sloka 1</w:t>', '<w:rPr><w:b/></w:rPr><w:t>Slo</w:t></w:r><w:r><w:t>ka1</w:t>')
      .replace('<w:t xml:space="preserve">Druhý řádek</w:t>', '<w:t>Druhý</w:t><w:tab/><w:t>řádek</w:t><w:br/><w:t>Pokračování</w:t>')
      .replace(/w:/g, 'x:').replace('xmlns:w=', 'xmlns:x='));
    const p = parseTxt(readDocx(bytes).text);
    expect(p.problems).toEqual([]); expect(p.sections[0].text).toContain('Druhý\třádek\nPokračování');
    expect(p.order).toEqual(['v1','r1','v2','r1']);
  });
  it('reports conflicts and missing references exactly as TXT', () => {
    const p = parseTxt(readDocx(docxFromText(sample + '\nREFREN1\nJiný text\n\nRefren1\n')).text);
    expect(p.conflicts).toHaveLength(1);
    const resolved = parseTxt(readDocx(docxFromText(sample + '\nREFREN1\nJiný text\n\nRefren1\n')).text, true);
    expect(resolved.order.slice(-2)).toEqual(['r2','r2']);
    expect(parseTxt(readDocx(docxFromText('Chyba\n\nBridge1\n')).text).problems.join()).toContain('neexistující');
  });
  it('updates one language and preserves identity, metadata and original orders', () => {
    const song = songFromTxt(parseTxt(sample)); song.addVariant('ukr');
    song.sections(song.variants[1])[0].textContent = 'Український'; song.root.setAttribute('custom', 'keep');
    const original = exportXml(song);
    const p = parseTxt(readDocx(docxFromText(sample.replace('Český refrén', 'Změněný refrén') + '\nRefrén 1\n')).text);
    const result = updateLanguageFromTxt(song, p, 0, 0, 'DOCX');
    expect(result.song.id).toBe(song.id); expect(result.song.root.getAttribute('custom')).toBe('keep');
    expect(result.song.variants[1].outerHTML).toBe(song.variants[1].outerHTML); expect(exportXml(song)).toBe(original);
    expect(result.song.repetitions[0].outerHTML).toBe(song.repetitions[0].outerHTML);
    expect(result.song.repetitions[1].getAttribute('name')).toBe('DOCX');
    expect(result.song.repetitions[1].getAttribute('main')).toBeNull();
  });
  it('rejects unsupported structures, revisions, DTD, malformed XML and automatic numbering', () => {
    for (const extra of ['<w:tbl/>','<w:p><w:r><w:drawing/></w:r></w:p>','<w:p><w:ins/></w:p>','<w:p><w:r><w:fldChar/></w:r></w:p>','<w:p><w:pPr><w:numPr/></w:pPr></w:p>']) {
      expect(() => readDocx(patchDocument(xml => xml.replace('<w:body>', '<w:body>' + extra)))).toThrow();
    }
    expect(() => readDocx(patchDocument(() => '<broken>'))).toThrow('XML');
    expect(() => readDocx(patchDocument(xml => xml.replace('?><w:document', '?><!DOCTYPE document [<!ENTITY test "bad">]><w:document')))).toThrow('DTD');
  });
  it('rejects corrupt/oversize archives and bounds decompression independently of ZIP metadata', () => {
    expect(() => readDocx(strToU8('old .doc'))).toThrow('DOCX');
    expect(() => readDocx(docxTemplate().slice(0, -30))).toThrow('ZIP');
    expect(() => readDocx(new Uint8Array(DOCX_MAX_BYTES + 1))).toThrow('5 MiB');
    expect(() => readDocx(zipSync({ 'unrelated.txt': strToU8('not docx') }))).toThrow('hlavní dokument');
    const bomb = zipSync({ 'word/document.xml': strToU8('a'.repeat(2 * 1024 * 1024)) });
    expect(() => readDocx(bomb)).toThrow('limit');
    const parts = unzipSync(docxFromText(sample)); parts['word/vbaProject.bin'] = new Uint8Array([1]);
    expect(() => readDocx(zipSync(parts))).toThrow('Makra');
  });
  it('warns about extra notes instead of silently dropping them', () => {
    const parts = unzipSync(docxFromText(sample)); parts['word/header1.xml'] = strToU8('<header/>');
    expect(readDocx(zipSync(parts)).warnings.join()).toContain('Záhlaví');
  });
});

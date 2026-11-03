import { Unzip, UnzipInflate, zipSync, strToU8 } from 'fflate';
import type { SongDocument } from '../domain/song';
import { exportTxt, txtTemplate } from './songTxt';

const W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main';
const STRICT_W = 'http://purl.oclc.org/ooxml/wordprocessingml/main';
export const DOCX_MAX_BYTES = 5 * 1024 * 1024;
const XML_LIMIT = 1024 * 1024;
const CONTENT_TYPES = 'http://schemas.openxmlformats.org/package/2006/content-types';
const MAIN_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml';

function xmlPart(bytes: Uint8Array) {
  let text: string;
  try { text = new TextDecoder('utf-8', { fatal: true }).decode(bytes); }
  catch { throw new Error('XML uvnitř DOCX není platné UTF-8. Uložte dokument znovu jako DOCX.'); }
  if (/<!DOCTYPE|<!ENTITY/i.test(text)) throw new Error('DTD a entity uvnitř DOCX nejsou podporovány.');
  const doc = new DOMParser().parseFromString(text, 'application/xml');
  if (doc.querySelector('parsererror')) throw new Error('DOCX obsahuje poškozené XML.');
  const pending: [Element, number][] = [[doc.documentElement, 0]]; let count = 0;
  while (pending.length) {
    const [e, depth] = pending.pop()!;
    if (++count > 30000 || depth > 64) throw new Error('DOCX má příliš složitou strukturu.');
    for (const child of e.children) pending.push([child, depth + 1]);
  }
  return doc;
}

/** Bounded streaming extraction: no archive entry is written to disk or executed. */
export function readDocx(bytes: Uint8Array): { text: string; warnings: string[] } {
  if (bytes.length > DOCX_MAX_BYTES) throw new Error('DOCX je větší než 5 MiB.');
  if (bytes[0] !== 0x50 || bytes[1] !== 0x4b) throw new Error('Soubor není platný DOCX. Starší .doc a dokumenty chráněné heslem nejsou podporovány.');
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let directoryEnd = -1;
  for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 65557); i--) {
    if (view.getUint32(i, true) === 0x06054b50 && i + 22 + view.getUint16(i + 20, true) === bytes.length) { directoryEnd = i; break; }
  }
  if (directoryEnd < 0 || view.getUint32(directoryEnd + 12, true) + view.getUint32(directoryEnd + 16, true) > directoryEnd) throw new Error('DOCX má neúplný nebo poškozený ZIP archiv.');
  const parts = new Map<string, Uint8Array>(), names = new Set<string>(), warnings: string[] = [];
  let failure: Error | undefined;
  try {
    const unzip = new Unzip(file => {
      if (names.has(file.name) || names.size >= 256) throw new Error('DOCX má duplicitní nebo příliš mnoho položek archivu.');
      names.add(file.name);
      if (/vbaProject|encryption/i.test(file.name)) throw new Error('Makra a šifrované dokumenty nejsou podporovány. Použijte běžný DOCX.');
      if (/^word\/(header|footer|footnotes|endnotes|comments)[^/]*\.xml$/i.test(file.name)) warnings.push('Záhlaví, zápatí, poznámky a komentáře dokumentu se do textu písně nepřenášejí.');
      if (file.name === 'word/numbering.xml') warnings.push('Dokument obsahuje definice automatického číslování. Čísla nadpisů musí být napsána přímo v textu; čísla vytvořená stylem se nepřenášejí. Zkontrolujte náhled.');
      if (!['word/document.xml', '[Content_Types].xml'].includes(file.name)) return;
      const limit = file.name === 'word/document.xml' ? XML_LIMIT : 65536;
      if (file.originalSize !== undefined && file.originalSize > limit) throw new Error('Textová část DOCX přesahuje povolený limit.');
      let size = 0; const chunks: Uint8Array[] = [];
      file.ondata = (error, chunk, final) => {
        if (error) { failure = error; file.terminate(); return; }
        size += chunk.length;
        if (size > limit) { failure = new Error('Rozbalený text DOCX přesahuje povolený limit.'); file.terminate(); return; }
        chunks.push(chunk);
        if (final) {
          const output = new Uint8Array(size); let offset = 0;
          for (const c of chunks) { output.set(c, offset); offset += c.length; }
          parts.set(file.name, output);
        }
      };
      file.start();
    });
    unzip.register(UnzipInflate);
    // Limit output allocation per inflate call, including dishonest ZIP sizes.
    for (let offset = 0; offset < bytes.length; offset += 512) {
      unzip.push(bytes.subarray(offset, offset + 512), offset + 512 >= bytes.length);
      if (failure) throw failure;
    }
  } catch (e) { throw new Error('DOCX nelze načíst: ' + (e as Error).message); }
  if (!parts.has('word/document.xml') || !parts.has('[Content_Types].xml')) throw new Error('DOCX neobsahuje úplný hlavní dokument.');
  const types = xmlPart(parts.get('[Content_Types].xml')!);
  if (!Array.from(types.getElementsByTagNameNS(CONTENT_TYPES, 'Override')).some(e => e.getAttribute('PartName') === '/word/document.xml' && e.getAttribute('ContentType') === MAIN_TYPE)) throw new Error('Očekáván běžný Word dokument .docx bez maker.');
  const doc = xmlPart(parts.get('word/document.xml')!), ns = doc.documentElement.namespaceURI;
  if (doc.documentElement.localName !== 'document' || ![W, STRICT_W].includes(ns ?? '')) throw new Error('Nepodporovaný formát Word dokumentu.');
  const body = Array.from(doc.documentElement.children).find(e => e.namespaceURI === ns && e.localName === 'body');
  if (!body) throw new Error('V DOCX chybí tělo dokumentu.');
  const forbidden = new Set(['tbl','drawing','pict','object','altChunk','ins','del','moveFrom','moveTo','rPrChange','pPrChange','fldChar','fldSimple','instrText','footnoteReference','endnoteReference']);
  for (const e of Array.from(body.getElementsByTagName('*'))) {
    if (e.namespaceURI === ns && forbidden.has(e.localName)) throw new Error('DOCX obsahuje tabulky, obrázky, pole, poznámky nebo sledované změny. Pro import použijte prostý text v odstavcích a nejprve přijměte či odmítněte revize ve Wordu.');
  }
  function inline(e: Element): string {
    if (e.namespaceURI !== ns) throw new Error('Nepodporovaný vložený obsah DOCX. Zkopírujte píseň do běžných odstavců.');
    switch (e.localName) {
      case 't': return e.textContent ?? '';
      case 'tab': return '\t';
      case 'br': case 'cr': return '\n';
      case 'noBreakHyphen': return '\u2011';
      case 'softHyphen': return '\u00ad';
      case 'pPr': case 'rPr': case 'bookmarkStart': case 'bookmarkEnd': case 'proofErr':
      case 'commentRangeStart': case 'commentRangeEnd': case 'commentReference': case 'lastRenderedPageBreak': return '';
      case 'hyperlink': warnings.push('Z odkazů se přenáší pouze zobrazený text.'); break;
      case 'p': case 'r': break;
      default: throw new Error(`Nepodporovaný obsah DOCX (${e.localName}). Použijte běžné odstavce s textem.`);
    }
    return Array.from(e.children).map(inline).join('');
  }
  const paragraphs: string[] = [];
  for (const e of body.children) {
    if (e.namespaceURI === ns && e.localName === 'sectPr') continue;
    if (e.namespaceURI !== ns || e.localName !== 'p') throw new Error('DOCX musí obsahovat píseň v běžných odstavcích, bez tabulek a textových polí.');
    if (e.getElementsByTagNameNS(ns!, 'numPr').length) throw new Error('Automatické číslování Wordu není podporováno. Čísla částí napište přímo do nadpisu, např. Sloka 1.');
    paragraphs.push(inline(e));
  }
  const text = paragraphs.join('\n');
  if (strToU8(text).length > XML_LIMIT) throw new Error('Text písně je větší než 1 MiB.');
  return { text, warnings: [...new Set(warnings)] };
}

/** Simple editable Word paragraphs; semantic parsing never depends on styles. */
export function docxFromText(source: string): Uint8Array {
  const lines = source.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').split('\n');
  // TXT has a terminal newline, not an extra empty paragraph after reimport.
  if (lines.at(-1) === '') lines.pop();
  const doc = document.implementation.createDocument(W, 'w:document');
  const node = (name: string, attrs: Record<string, string> = {}) => {
    const e = doc.createElementNS(W, 'w:' + name);
    for (const [key, value] of Object.entries(attrs)) e.setAttributeNS(W, 'w:' + key, value);
    return e;
  };
  const body = node('body'); doc.documentElement.append(body);
  lines.forEach((line, i) => {
    const p = node('p'), properties = node('pPr');
    if (i === 0) properties.append(node('pStyle', { val: 'Title' }));
    properties.append(node('spacing', { after: '0', line: '276', lineRule: 'auto' })); p.append(properties);
    const r = node('r'), t = node('t'); t.setAttributeNS('http://www.w3.org/XML/1998/namespace', 'xml:space', 'preserve'); t.textContent = line;
    r.append(t); p.append(r); body.append(p);
  });
  const section = node('sectPr'); section.append(node('pgSz', { w: '11906', h: '16838' }), node('pgMar', { top: '1134', right: '1134', bottom: '1134', left: '1134', header: '567', footer: '567', gutter: '0' })); body.append(section);
  const styles = `<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="${W}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:color w:val="000000"/><w:sz w:val="24"/></w:rPr></w:rPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:after="120"/></w:pPr><w:rPr><w:b/><w:color w:val="000000"/><w:sz w:val="32"/></w:rPr></w:style></w:styles>`;
  return zipSync({
    '[Content_Types].xml': strToU8(`<?xml version="1.0" encoding="UTF-8"?><Types xmlns="${CONTENT_TYPES}"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="${MAIN_TYPE}"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>`),
    '_rels/.rels': strToU8('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'),
    'word/document.xml': strToU8('<?xml version="1.0" encoding="UTF-8"?>' + new XMLSerializer().serializeToString(doc)),
    'word/_rels/document.xml.rels': strToU8('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'),
    'word/styles.xml': strToU8(styles),
  });
}
export const docxTemplate = () => docxFromText(txtTemplate);
export const exportDocx = (song: SongDocument, language = 0, order = song.repetitions.indexOf(song.selectedRepetition)) => docxFromText(exportTxt(song, language, order));

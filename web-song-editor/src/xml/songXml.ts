import { SongDocument } from '../domain/song';
export const MAX_BYTES = 1024 * 1024; // largest library song: 5588 bytes; generous, bounded first release
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
function unique(names: string[], what: string) {
  if (names.some(s => !s.trim()) || new Set(names).size !== names.length) throw new Error(`${what}: prázdná nebo duplicitní jména zatím nelze bezpečně editovat.`);
}
export function validate(song: SongDocument) {
  if (song.root.tagName !== 'slide' || song.root.namespaceURI) throw new Error('Očekáván kořen slide bez namespace.');
  if (!uuid.test(song.id ?? '')) throw new Error('Neplatné song-id. Identita nebyla nahrazena; opravte ji výslovně v desktopovém editoru nebo v kopii souboru.');
  if (!song.variants.length) throw new Error('Chybí jazyková varianta. Soubor nelze bezpečně editovat.');
  unique(song.variants.map(v => v.getAttribute('name') ?? ''), 'Varianty');
  for (const v of song.variants) {
    if (v.namespaceURI) throw new Error('Namespace jazykové varianty není podporován.');
    if (Array.from(v.children).some(e => !['section','repetition'].includes(e.tagName))) throw new Error('Nepodporovaný element uvnitř varianty.');
    const ids = song.sections(v).map(s => s.getAttribute('name') ?? '');
    unique(ids, 'Části');
    if (ids.some(id => /[ .()@*:\s]/u.test(id))) throw new Error('ID části obsahuje znaky syntaxe pořadí.');
  }
  for (const e of [...song.variants.flatMap(v => song.sections(v)), ...song.repetitions]) {
    if (e.namespaceURI) throw new Error(`Namespace v ${e.tagName} není podporován.`);
    if (e.children.length) throw new Error(`Vnořený obsah v ${e.tagName} není podporován.`);
  }
  // Guides are intentionally not rewritten or rejected here. Invalid legacy
  // guides remain inert text and are diagnosed/locked in the visual editor.
}
export function importXml(text: string): SongDocument {
  if (new TextEncoder().encode(text).length > MAX_BYTES) throw new Error('XML je větší než 1 MiB.');
  if (/<!DOCTYPE/i.test(text)) throw new Error('DTD není podporováno.');
  const encoding = text.match(/^\uFEFF?\s*<\?xml[^?]*encoding\s*=\s*['"]([^'"]+)/i)?.[1];
  if (encoding && !/^utf-?8$/i.test(encoding)) throw new Error(`Kódování ${encoding} není podporováno; převeďte kopii do UTF-8.`);
  const xml = new DOMParser().parseFromString(text, 'application/xml');
  if (xml.querySelector('parsererror')) throw new Error('Neplatné XML. Aktuální píseň zůstává otevřená. Podrobnosti: ' + xml.querySelector('parsererror')!.textContent?.slice(0, 500));
  if (Array.from(xml.childNodes).some(n => n.nodeType === 7)) throw new Error('Instrukce XML mimo kořen nelze v této verzi bezpečně zachovat.');
  if (xml.querySelectorAll('*').length > 10000) throw new Error('XML obsahuje příliš mnoho uzlů.');
  const pending: [Element, number][] = [[xml.documentElement, 1]];
  while (pending.length) {
    const [node, depth] = pending.pop()!;
    if (depth > 64) throw new Error('XML přesahuje limit 64 úrovní vnoření.');
    for (const child of node.children) pending.push([child, depth + 1]);
  }
  // Repetitions inside unknown metadata are ambiguous to the desktop loader.
  for (const r of xml.querySelectorAll('repetition')) {
    const parent = r.parentElement;
    if (parent !== xml.documentElement && !(parent?.tagName === 'variant' && parent.parentElement === xml.documentElement)) throw new Error('Pořadí uvnitř neznámých metadat není podporováno.');
  }
  const song = new SongDocument(xml);
  if (!song.root.hasAttribute('song-id')) song.root.setAttribute('song-id', crypto.randomUUID());
  validate(song);
  return song;
}
export function exportXml(song: SongDocument) {
  validate(song);
  const result = '<?xml version="1.0" encoding="utf-8"?>\n' + new XMLSerializer().serializeToString(song.root).replace(/\r/g, '&#13;');
  // Reparse to catch invalid XML control characters entered into text fields.
  importXml(result);
  return result;
}

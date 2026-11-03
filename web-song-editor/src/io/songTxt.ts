import { newSong, SongDocument } from '../domain/song';
import { validate } from '../xml/songXml';

const fold = (s: string) => s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
function heading(line: string) {
  const m = fold(line.trim()).match(/^(sloka|refren|bridge)\s*(\d*)\s*:$/u) ?? fold(line.trim()).match(/^(sloka|refren|bridge)\s*(\d*)$/u);
  return m && ({ sloka: 'v', refren: 'r', bridge: 'b' }[m[1]]! + (m[2] || '1'));
}
const label = (id: string) => ({ v: 'Sloka', r: 'Refrén', b: 'Bridge' }[id[0]] + ' ' + id.slice(1));
export const txtTemplate = '\uFEFFNázev písně\r\n\r\nSloka 1\r\n\r\nRefrén 1\r\n\r\nBridge 1\r\n';
export interface TxtPreview { title: string; language: string; orderName: string; main: string | null; sections: { id: string; text: string }[]; order: string[]; problems: string[]; conflicts: string[]; resolved: boolean }
/** One blank line next to a heading is a separator; further blank lines are text. */
export function parseTxt(source: string, variants = false): TxtPreview {
  if (new TextEncoder().encode(source).length > 1024 * 1024) throw new Error('TXT je větší než 1 MiB.');
  const lines = source.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').split('\n');
  const p: TxtPreview = { title: '', language: 'čeština', orderName: 'default', main: '1', sections: [], order: [], problems: [], conflicts: [], resolved: variants };
  if (lines[0]?.startsWith('# SuperPresenter TXT')) {
    if (lines.shift() !== '# SuperPresenter TXT 1') throw new Error('Nepodporovaná verze TXT.');
    const metadata = lines.shift();
    if (!metadata?.startsWith('# ')) throw new Error('Chybí technická hlavička TXT.');
    let h;
    try { h = JSON.parse(metadata.slice(2)); } catch { throw new Error('Poškozená technická hlavička TXT.'); }
    if (typeof h.id !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(h.id) || typeof h.language !== 'string' || !h.language.trim() || typeof h.order !== 'string' || !h.order.trim() || !(h.main === null || typeof h.main === 'string')) throw new Error('Neplatná identita nebo metadata TXT. Hlavičku neměňte.');
    // Compatibility only: old headers are readable but never select an identity.
  }
  let current: { id: string; lines: string[] } | undefined;
  const aliases = new Map<string, string>();
  const definitions = new Map<string, { id: string; text: string }[]>();
  // Reserve all written IDs so conflict variants cannot steal a later heading.
  const reserved = new Set(lines.map(heading).filter(Boolean));
  function finish() {
    if (!current) return;
    const body = current.lines;
    if (body[0] === '') body.shift();
    if (body.at(-1) === '') body.pop();
    const text = body.join('\n'), id = current.id;
    const previous = p.sections.find(s => s.id === id);
    const identical = definitions.get(id)?.find(s => s.text === text);
    if (!text.trim()) {
      const target = aliases.get(id) ?? id;
      if (!p.sections.some(s => s.id === target)) p.problems.push(`Prázdná část ${label(id)} odkazuje na dosud neexistující definici.`);
      p.order.push(target);
    } else if (identical) {
      aliases.set(id, identical.id); p.order.push(identical.id);
    } else if (previous && previous.text !== text) {
      p.conflicts.push(`Část ${label(id)} má odlišný text.`);
      if (variants) {
        let n = 1; while (reserved.has(id[0] + n)) n++;
        const next = id[0] + n; reserved.add(next); aliases.set(id, next);
        p.sections.push({ id: next, text }); p.order.push(next);
        definitions.get(id)!.push({ id: next, text });
      } else p.order.push(id);
    } else {
      if (!previous) { p.sections.push({ id, text }); definitions.set(id, [{ id, text }]); }
      aliases.set(id, id); p.order.push(id);
    }
  }
  for (const line of lines) {
    const id = heading(line);
    if (id) { finish(); current = { id, lines: [] }; }
    else if (current) current.lines.push(line.startsWith('\\') ? line.slice(1) : line);
    else if (line.trim()) {
      const title = line.match(/^\s*n[aá]zev\s*:\s*(.*)$/iu);
      if (!p.title) p.title = title ? title[1] : line.trim();
      else p.problems.push(`Nerozpoznaný řádek před první částí: ${line}`);
    }
  }
  finish();
  if (!p.title.trim()) p.problems.push('Chybí název písně na prvním řádku.');
  if (!p.sections.length) p.problems.push('Chybí neprázdná textová část.');
  if (p.order.length > 4096) p.problems.push('Pořadí přesahuje 4096 výskytů.');
  return p;
}
export function songFromTxt(p: TxtPreview): SongDocument {
  if (p.problems.length) throw new Error(p.problems.join('\n'));
  if (p.conflicts.length && !p.resolved) throw new Error('Nejprve výslovně vyřešte odlišné texty stejných částí.');
  const song = newSong(); song.title = p.title;
  const v = song.variants[0]; v.setAttribute('name', p.language); v.replaceChildren();
  for (const s of p.sections) { const e = song.xml.createElement('section'); e.setAttribute('name', s.id); e.textContent = s.text; v.append(e); }
  const r = song.repetitions[0]; r.setAttribute('name', p.orderName); r.textContent = p.order.join(' ');
  if (p.main === null) r.removeAttribute('main'); else r.setAttribute('main', p.main);
  validate(song);
  const errors = song.diagnostics(r); if (errors.length) throw new Error(errors.join('\n'));
  return song;
}
/** Export a selected language/order as an explicitly limited text projection. */
export function exportTxt(song: SongDocument, variantIndex = 0, repetitionIndex = song.repetitions.indexOf(song.selectedRepetition)): string {
  validate(song);
  const fail = () => { throw new Error('Vybraný jazyk a pořadí nelze převést do jednoduchého textového dokumentu (pokročilé pořadí, vlastní ID, nepoužité či prázdné části nebo nepřevoditelný text). Použijte XML.'); };
  const v = song.variants[variantIndex], r = song.repetitions[repetitionIndex];
  if (!v || !r) return fail();
  const tree = song.tree(r);
  const order: string[] = [];
  for (const n of tree) { if ('children' in n || n.pinned || n.start !== undefined || !song.sections(v).some(s => s.getAttribute('name') === n.section)) fail(); else order.push(n.section); }
  if (song.sections(v).some(s => !/^[vrb][0-9]+$/.test(s.getAttribute('name')!) || !order.includes(s.getAttribute('name')!) || !s.textContent?.trim() || /[\r]|^\n|\n$/.test(s.textContent))) fail();
  if (!song.title.trim() || /[\r\n]/.test(song.title) || !r.getAttribute('name')?.trim()) fail();
  if (heading(song.title) || /^\s*n[aá]zev\s*:/iu.test(song.title)) fail();
  const out = [song.title, ''];
  const seen = new Set<string>();
  for (const id of order) {
    out.push(label(id));
    if (!seen.has(id)) out.push(...song.sections(v).find(s => s.getAttribute('name') === id)!.textContent!.split('\n').map(l => heading(l) || l.startsWith('\\') ? '\\' + l : l));
    seen.add(id); out.push('');
  }
  const result = out.join('\n');
  const check = parseTxt(result);
  if (check.title !== song.title || check.problems.length || check.conflicts.length || check.sections.some(s => s.text !== song.sections(v).find(e => e.getAttribute('name') === s.id)?.textContent)) fail();
  return '\uFEFF' + result.replace(/\n/g, '\r\n');
}

/** Clone first: edits preserve identity, metadata, omitted sections and every order. */
export function updateLanguageFromTxt(current: SongDocument, p: TxtPreview, variantIndex: number, repetitionIndex: number, orderLabel = 'TXT') {
  const imported = songFromTxt(p);
  const next = new SongDocument(current.xml.cloneNode(true) as XMLDocument);
  const v = next.variants[variantIndex];
  if (!v) throw new Error('Vyberte existující jazyk.');
  for (const s of imported.sections()) {
    const existing = next.sections(v).find(e => e.getAttribute('name') === s.getAttribute('name'));
    if (existing) existing.textContent = s.textContent;
    else v.append(next.xml.importNode(s, true));
  }
  const order = p.order.join(' '), selected = next.repetitions[repetitionIndex];
  // A changed TXT order becomes a new non-default order; never overwrite trees.
  let matches = false;
  if (selected) {
    try { matches = next.tree(selected).every(n => !('children' in n) && !n.pinned && n.start === undefined) && next.tree(selected).map(n => 'children' in n ? '' : n.section).join(' ') === order; } catch { /* keep invalid imported guide */ }
  }
  let addedOrder = false;
  if (!matches) {
    let name = orderLabel; let n = 2;
    while (next.repetitions.some(r => r.getAttribute('name') === name)) name = orderLabel + ' ' + n++;
    const r = next.addRepetition(name); r.textContent = order; addedOrder = true;
  }
  validate(next);
  return { song: next, addedOrder };
}


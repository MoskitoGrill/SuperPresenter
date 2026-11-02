import { parseSimple } from '../construct/simple';
import { parseTree, serializeTree, removeReferences, leaves, budget, risky, type Node } from '../construct/tree';

export class SongDocument {
  constructor(public xml: XMLDocument) {}
  get root() { return this.xml.documentElement; }
  get variants() { return Array.from(this.root.children).filter(e => e.tagName === 'variant'); }
  get repetitions() { return Array.from(this.root.querySelectorAll('repetition')); }
  sections(variant = this.variants[0]) { return Array.from(variant.children).filter(e => e.tagName === 'section'); }
  steps(rep: Element) { return parseSimple(rep.textContent ?? '', this.sections().map(e => e.getAttribute('name')!)); }
  get ids() { return [...new Set(this.variants.flatMap(v => this.sections(v).map(s => s.getAttribute('name')!)))]; }
  tree(rep: Element) { return parseTree(rep.textContent ?? '', this.ids); }
  diagnostics(rep: Element): string[] {
    try {
      const tree = this.tree(rep), messages: string[] = [];
      if (risky(tree)) messages.push('Historická konstrukce s nulou nebo prázdnou skupinou: zachována, vizuální úprava uzamčena.');
      for (const v of this.variants) for (const s of leaves(tree)) {
        const section = this.sections(v).find(e => e.getAttribute('name') === s.section);
        if (!section) messages.push(`V jazyce „${v.getAttribute('name')}“ chybí část ${s.section}. Desktop používá průnik částí vybraných jazyků.`);
        else if (s.start !== undefined && (s.end ?? s.start) > presentationLines(section.textContent ?? '').length) messages.push(`Část ${s.section}, jazyk „${v.getAttribute('name')}“: výběr přesahuje počet prezentačních řádků.`);
      }
      const lengths = new Map(this.ids.map(id => [id, Math.max(...this.variants.map(v => presentationLines(this.sections(v).find(s => s.getAttribute('name') === id)?.textContent ?? '').length)) * this.variants.length]));
      budget(tree, lengths, this.variants.length);
      return [...new Set(messages)];
    } catch (error) { return [(error as Error).message]; }
  }
  saveTree(rep: Element, tree: Node[]) {
    const text = serializeTree(tree); parseTree(text, this.ids);
    const old = rep.textContent; rep.textContent = text;
    const errors = this.diagnostics(rep);
    if (errors.length) { rep.textContent = old; throw new Error(errors.join('\n')); }
  }
  addVariant(name: string) {
    if (!name.trim() || this.variants.some(v => v.getAttribute('name') === name)) throw new Error('Zadejte neprázdný, jedinečný název jazyka.');
    const v = this.xml.createElement('variant'); v.setAttribute('name', name);
    for (const id of this.ids) { const s = this.xml.createElement('section'); s.setAttribute('name', id); v.append(s); }
    this.root.append(v); return v;
  }
  removeVariant(variant: Element) {
    if (!this.variants.includes(variant)) throw new Error('Tato jazyková varianta již neexistuje.');
    if (this.variants.length <= 1) throw new Error('Poslední jazykovou variantu nelze odebrat. Píseň musí mít alespoň jeden jazyk.');
    // Keep each repetition object, attributes, guide and global traversal order.
    // A language deletion must never implicitly delete a named/default order.
    for (const repetition of Array.from(variant.children).filter(e => e.tagName === 'repetition')) this.root.insertBefore(repetition, variant);
    variant.remove();
  }
  addRepetition(name: string) {
    if (!name.trim() || this.repetitions.some(r => r.getAttribute('name') === name)) throw new Error('Zadejte neprázdné, jedinečné jméno pořadí.');
    const r = this.xml.createElement('repetition'); r.setAttribute('name', name); r.textContent = this.ids[0] ?? ''; this.root.append(r); return r;
  }
  setDefault(rep: Element) { for (const r of this.repetitions) r.removeAttribute('main'); rep.setAttribute('main', '1'); }
  get selectedRepetition() { return this.repetitions.find(r => /^(1|true|yes)$/i.test(r.getAttribute('main') ?? '')) ?? this.repetitions.find(r => r.getAttribute('name') === 'default') ?? this.repetitions[0]; }
  get id() { return this.root.getAttribute('song-id')!; }
  get title() { return this.root.getAttribute('name') ?? ''; }
  set title(value: string) { this.root.setAttribute('name', value); }
  copy(title: string) {
    const copy = new SongDocument(this.xml.cloneNode(true) as XMLDocument);
    copy.title = title;
    copy.root.setAttribute('song-id', crypto.randomUUID());
    return copy;
  }
  addSection(prefix: string) {
    let n = 1;
    while (this.ids.includes(prefix + n)) n++;
    const id = prefix + n;
    for (const variant of this.variants) {
      const section = this.xml.createElement('section');
      section.setAttribute('name', id);
      variant.append(section);
    }
    return id;
  }
  removeSection(id: string) {
    // Compute every guide first, before mutating anything.
    if (this.repetitions.some(r => this.diagnostics(r).length)) throw new Error('Část nelze odebrat: některé pořadí je uzamčené nebo neplatné. Nejprve výslovně opravte či nahraďte toto pořadí; původní data zůstala zachována.');
    const changes = this.repetitions.filter(r => leaves(this.tree(r)).some(s => s.section === id)).map(r => [r, removeReferences(this.tree(r), id)] as const);
    if (changes.some(([, steps]) => !steps.length)) throw new Error('Odstranění by vyprázdnilo pořadí. Nejprve přidejte do pořadí jinou část.');
    for (const v of this.variants) this.sections(v).find(s => s.getAttribute('name') === id)?.remove();
    for (const [r, steps] of changes) r.textContent = serializeTree(steps);
  }
}

/** Mirrors WidgetSource's physical lines / clearEmpties (see differential tests). */
export function presentationLines(text: string) { return text.trim().split(/\r\n|[\n\r\v\f\u001c-\u001e\u0085\u2028\u2029]/u).map(s => s.replace(/\uFEFF/g, '').replace(/^[ \t]+/u, '')).filter(Boolean); }

export function newSong(): SongDocument {
  const doc = document.implementation.createDocument(null, 'slide');
  const song = new SongDocument(doc);
  song.title = 'Nová píseň';
  song.root.setAttribute('song-id', crypto.randomUUID());
  const variant = doc.createElement('variant');
  variant.setAttribute('name', 'čeština');
  song.root.append(variant);
  song.addSection('v');
  const rep = doc.createElement('repetition');
  rep.setAttribute('name', 'default'); rep.setAttribute('main', '1'); rep.textContent = 'v1';
  song.root.append(rep);
  return song;
}

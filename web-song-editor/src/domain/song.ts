import { parseSimple } from '../construct/simple';

export class SongDocument {
  constructor(public xml: XMLDocument) {}
  get root() { return this.xml.documentElement; }
  get variants() { return Array.from(this.root.children).filter(e => e.tagName === 'variant'); }
  get repetitions() { return Array.from(this.root.querySelectorAll('repetition')); }
  sections(variant = this.variants[0]) { return Array.from(variant.children).filter(e => e.tagName === 'section'); }
  steps(rep: Element) { return parseSimple(rep.textContent ?? '', this.sections().map(e => e.getAttribute('name')!)); }
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
    while (this.sections().some(s => s.getAttribute('name') === prefix + n)) n++;
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
    const changes = this.repetitions.map(r => [r, this.steps(r).filter(s => s !== id)] as const);
    if (changes.some(([, steps]) => !steps.length)) throw new Error('Odstranění by vyprázdnilo pořadí. Nejprve přidejte do pořadí jinou část.');
    for (const v of this.variants) this.sections(v).find(s => s.getAttribute('name') === id)?.remove();
    for (const [r, steps] of changes) r.textContent = steps.join(' ');
  }
}

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

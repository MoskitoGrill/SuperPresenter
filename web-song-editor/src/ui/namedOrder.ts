import { SongDocument } from '../domain/song';

/** Apply the working order by exact name, without changing the source document. */
export function saveNamedOrder(song: SongDocument, sourceIndex: number, draft: Element, value: string) {
  const result = new SongDocument(song.xml.cloneNode(true) as XMLDocument);
  const name = value.trim() || 'default';
  const source = result.repetitions[sourceIndex];
  const matches = result.repetitions.filter(r => r.getAttribute('name') === name);
  if (matches.length > 1 && source?.getAttribute('name') !== name) {
    throw new Error(`XML obsahuje více opakování „${name}“. Nelze bezpečně určit, které nahradit. Zvolte jiný název.`);
  }
  let target = source?.getAttribute('name') === name ? source : matches[0];
  if (!target) {
    target = result.xml.importNode(draft, true); target.setAttribute('name', name);
    target.removeAttribute('main'); result.root.append(target);
    // The UI's empty initial default is a placeholder, not another arrangement.
    if (source?.getAttribute('name') === 'default' && !source.textContent?.trim() && Array.from(source.attributes).every(a => ['name', 'main'].includes(a.name))) source.remove();
  }
  target.textContent = draft.textContent;
  if (target !== source || !source) result.setDefault(target);
  return result;
}

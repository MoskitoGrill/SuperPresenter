import { newSong, type SongDocument } from '../domain/song';
import { exportXml } from '../xml/songXml';
import { openFile, download } from '../io/files';
import './style.css';

let song = newSong(), dirty = true, variantIndex = 0, repetitionIndex = 0;
let original: { song: SongDocument; dirty: boolean } | undefined;
const app = document.querySelector<HTMLElement>('#app')!;
function el<K extends keyof HTMLElementTagNameMap>(tag: K, text = '') {
  const e = document.createElement(tag); e.textContent = text; return e;
}
function button(text: string, action: () => void, disabled = false) {
  const b = el('button', text); b.type = 'button'; b.disabled = disabled;
  b.onclick = () => { try { action(); } catch (e) { alert(String((e as Error).message)); } }; return b;
}
function field(caption: string, value: string, change: (value: string) => void, multiline = false) {
  const label = el('label', caption); const input = multiline ? el('textarea') : el('input');
  input.value = value; input.oninput = () => { change(input.value); dirty = true; status(); preview(); };
  label.append(input); return label;
}
function mayReplace(discardOriginal = false) { return !(dirty || (discardOriginal && original?.dirty)) || confirm('Nahrazované koncepty obsahují změny, které nebyly staženy. Zahodit je a pokračovat?'); }
function replace(next: SongDocument, changed: boolean) { song = next; dirty = changed; variantIndex = 0; repetitionIndex = song.repetitions.indexOf(song.selectedRepetition); render(); }
function move<T>(list: T[], index: number, delta: number) { [list[index], list[index + delta]] = [list[index + delta], list[index]]; return list; }
function status() { document.querySelector('#state')!.textContent = `${dirty ? 'Změny nebyly staženy' : 'XML staženo / načteno'} · ID: ${song.id}${original ? ' · Pracujete s kopií; původní koncept je dostupný tlačítkem.' : ''}`; }
function preview() {
  const area = document.querySelector('#preview')!; area.replaceChildren();
  const variant = song.variants[variantIndex];
  for (const id of song.steps(song.repetitions[repetitionIndex])) {
    const section = song.sections(variant).find(s => s.getAttribute('name') === id)!;
    area.append(el('h3', id), el('pre', section.textContent ?? ''));
  }
}
function render() {
  app.replaceChildren(el('h1', 'Editor písní SuperPresenter'));
  const nav = el('nav');
  nav.append(button('Nová píseň', () => { if (mayReplace(true)) { original = undefined; replace(newSong(), true); } }));
  const file = el('input'); file.type = 'file'; file.accept = '.xml,application/xml,text/xml'; file.setAttribute('aria-label', 'Otevřít XML');
  file.onchange = async () => {
    const selected = file.files?.[0]; file.value = ''; if (!selected) return;
    try {
      // Parsing is transactional: invalid input never replaces the current draft.
      const next = await openFile(selected);
      if (mayReplace(true)) { original = undefined; replace(next, true); }
    } catch (e) { alert((e as Error).message); }
  };
  nav.append(file, button('Stáhnout XML', () => { download(exportXml(song), song.title); dirty = false; status(); }), button('Vytvořit kopii', () => {
    const title = prompt('Název nové kopie (původní koncept zůstane dostupný):', song.title + ' (kopie)');
    if (!title?.trim()) return;
    if (title.trim() === song.title.trim()) throw new Error('Zadejte vlastní název kopie odlišný od původního.');
    if (original) throw new Error('Nejprve se vraťte k původnímu konceptu. Lze držet jednu kopii současně.');
    const copy = song.copy(title.trim()); original = { song, dirty }; replace(copy, true);
  }));
  if (original) nav.append(button('Vrátit původní koncept', () => {
    if (!mayReplace()) return; const saved = original!; original = undefined; replace(saved.song, saved.dirty);
  }));
  app.append(nav, el('p', 'Stažení XML nepřepíše původní soubor. Stažený soubor musíte sami umístit do knihovny SuperPresenteru a případně nahradit původní soubor.'), el('p', 'Staršímu XML bez song-id přidělíme identitu konceptu. Pro další úpravy otevírejte stažený soubor s ID. Prohlížeč může přidat číslo k názvu souboru.'), Object.assign(el('p'), { id: 'state' }));
  app.append(field('Název písně', song.title, value => { song.title = value; }));
  const vlabel = el('label', 'Jazyková varianta'); const vselect = el('select');
  song.variants.forEach((v,i) => { const opt = el('option', v.getAttribute('name')!); opt.value = String(i); vselect.append(opt); });
  vselect.value = String(variantIndex); vselect.onchange = () => { variantIndex = Number(vselect.value); render(); }; vlabel.append(vselect); app.append(vlabel);
  const variant = song.variants[variantIndex];
  app.append(field('Název varianty', variant.getAttribute('name')!, value => variant.setAttribute('name', value)));
  app.append(el('h2', 'Části — text se sdílí ve všech výskytech pořadí'));
  const sections = song.sections(variant);
  sections.forEach((section,i) => {
    const id = section.getAttribute('name')!; const card = el('section');
    card.append(field(id, section.textContent ?? '', value => { section.textContent = value; }, true));
    for (const delta of [-1,1]) card.append(button(delta < 0 ? 'Část nahoru' : 'Část dolů', () => {
      for (const v of song.variants) {
        const nodes = song.sections(v), current = nodes.find(s => s.getAttribute('name') === id)!;
        const otherId = sections[i + delta].getAttribute('name');
        const other = nodes.find(s => s.getAttribute('name') === otherId)!;
        if (delta < 0) v.insertBefore(current, other); else v.insertBefore(other, current);
      }
      dirty = true; render();
    }, i + delta < 0 || i + delta >= sections.length));
    card.append(button('Odebrat část', () => {
      const count = song.repetitions.reduce((n,r) => n + song.steps(r).filter(s => s === id).length, 0);
      if (confirm(`Odebrat ${id} ze všech ${song.variants.length} variant a odstranit ${count} odkazů ve všech pořadích?`)) { song.removeSection(id); dirty = true; render(); }
    })); app.append(card);
  });
  for (const [label,prefix] of [['Sloka','v'],['Refrén','r'],['Bridge','b'],['Vlastní blok','s']]) app.append(button(`Přidat: ${label}`, () => {
    let chosen = prefix;
    if (prefix === 's') { const value = prompt('Název vlastního typu (písmena, čísla, pomlčka):', 'solo'); if (!value) return; if (!/^[\p{L}\p{N}_-]+$/u.test(value)) throw new Error('Použijte písmena, čísla, podtržítko nebo pomlčku.'); chosen = value; }
    song.addSection(chosen); dirty = true; render();
  }));
  app.append(el('h2', 'Pořadí přehrávání'));
  const rlabel = el('label', 'Pojmenované pořadí'); const rselect = el('select');
  song.repetitions.forEach((r,i) => { const opt = el('option', r.getAttribute('name')!); opt.value = String(i); rselect.append(opt); });
  rselect.value = String(repetitionIndex); rselect.onchange = () => { repetitionIndex = Number(rselect.value); render(); }; rlabel.append(rselect); app.append(rlabel);
  const rep = song.repetitions[repetitionIndex], steps = song.steps(rep);
  function saveSteps(next: string[]) { rep.textContent = next.join(' '); dirty = true; render(); }
  steps.forEach((id,i) => {
    const row = el('div', `${i+1}. ${id} `);
    for (const delta of [-1,1]) row.append(button(delta < 0 ? 'Výskyt nahoru' : 'Výskyt dolů', () => saveSteps(move([...steps],i,delta)), i + delta < 0 || i + delta >= steps.length));
    row.append(button('Odebrat výskyt', () => saveSteps(steps.filter((_,j) => j !== i)), steps.length <= 1)); app.append(row);
  });
  for (const s of sections) { const id = s.getAttribute('name')!; app.append(button(`Zařadit ${id}`, () => saveSteps([...steps,id]))); }
  app.append(el('h2', 'Náhled výsledného pořadí'), Object.assign(el('div'), { id: 'preview' })); status(); preview();
}
window.addEventListener('beforeunload', event => { if (dirty || original?.dirty) { event.preventDefault(); event.returnValue = ''; } });
render();

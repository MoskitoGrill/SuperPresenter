import { newSong, presentationLines, type SongDocument } from '../domain/song';
import { exportXml, importXml } from '../xml/songXml';
import { leaves, type Node } from '../construct/tree';
import { openFile, readUtf8, openDocx, download } from '../io/files';
import { exportTxt, parseTxt, songFromTxt, txtTemplate, updateLanguageFromTxt } from '../io/songTxt';
import { exportDocx, docxTemplate } from '../io/songDocx';
import './style.css';

let song = newSong(), dirty = true, variantIndex = 0, repetitionIndex = 0;
let original: { song: SongDocument; dirty: boolean } | undefined;
const storageKey = 'superpresenter-song-draft-v1';
let storageMessage = '', recoveryFailed = false;
function persist() {
  if (recoveryFailed) return;
  try {
    const xml = (s: SongDocument) => new XMLSerializer().serializeToString(s.root).replace(/\r/g, '&#13;');
    localStorage.setItem(storageKey, JSON.stringify({ version: 1, xml: xml(song), dirty, variantIndex, repetitionIndex, original: original && { xml: xml(original.song), dirty: original.dirty } }));
    storageMessage = 'Koncept je v místním úložišti tohoto prohlížeče.';
  } catch { storageMessage = 'Místní obnova není dostupná (úložiště je plné nebo zakázané). Stáhněte XML.'; }
}
try {
  const raw = localStorage.getItem(storageKey);
  if (raw) {
    const saved = JSON.parse(raw);
    if (saved.version !== 1) throw new Error('Neznámá verze konceptu');
    const next = importXml(saved.xml), previous = saved.original && importXml(saved.original.xml);
    song = next; dirty = !!saved.dirty;
    variantIndex = Math.max(0, Math.min(Math.trunc(Number(saved.variantIndex)) || 0, song.variants.length - 1));
    repetitionIndex = Math.max(0, Math.min(Math.trunc(Number(saved.repetitionIndex)) || 0, song.repetitions.length - 1));
    if (previous) original = { song: previous, dirty: !!saved.original.dirty };
    storageMessage = 'Rozpracovaná práce byla obnovena.';
  }
} catch { recoveryFailed = true; storageMessage = 'Uložený koncept nelze načíst. Nebyl přepsán; stáhněte zálohu tlačítkem níže.'; }
const app = document.querySelector<HTMLElement>('#app')!;
function el<K extends keyof HTMLElementTagNameMap>(tag: K, text = '') {
  const e = document.createElement(tag); e.textContent = text; return e;
}
function button(text: string, action: () => void, disabled = false) {
  const b = el('button', text); b.type = 'button'; b.disabled = disabled;
  b.onclick = () => { try { action(); } catch (e) { alert(String((e as Error).message)); render(); } }; return b;
}
function field(caption: string, value: string, change: (value: string) => void, multiline = false) {
  const label = el('label', caption); const input = multiline ? el('textarea') : el('input');
  input.value = value; input.oninput = () => { change(input.value); dirty = true; status(); preview(); };
  label.append(input); return label;
}
function mayReplace(discardOriginal = false) { return !(dirty || (discardOriginal && original?.dirty)) || confirm('Nahrazované koncepty obsahují změny, které nebyly staženy. Zahodit je a pokračovat?'); }
function replace(next: SongDocument, changed: boolean) { song = next; dirty = changed; variantIndex = 0; repetitionIndex = song.repetitions.indexOf(song.selectedRepetition); render(); }
function move<T>(list: T[], index: number, delta: number) { [list[index], list[index + delta]] = [list[index + delta], list[index]]; return list; }
function status() {
  persist();
  document.querySelector('#state')!.textContent = `${dirty ? 'Změny nebyly staženy' : 'XML staženo / načteno'} · ID: ${song.id}${original ? ' · Pracujete s kopií; původní koncept je dostupný tlačítkem.' : ''}`;
  document.querySelector('#storage')!.textContent = storageMessage + ' Nejde o sdílené ani trvalé uložení. Vymazání dat prohlížeče nebo změna adresy webu koncept znepřístupní. Pro uchování stáhněte XML.';
}
function preview() {
  const area = document.querySelector('#preview')!; area.replaceChildren();
  const variant = song.variants[variantIndex];
  const rep = song.repetitions[repetitionIndex];
  if (!rep) { area.append(el('p', 'Soubor nemá pořadí. Je zachován beze změny; můžete výslovně přidat nové pořadí.')); return; }
  const errors = song.diagnostics(rep);
  if (errors.length) { area.append(el('p', errors.join('\n'))); return; }
  function show(nodes: Node[]) {
    for (const node of nodes) {
      if ('children' in node) { for (let i = 0; i < node.repeat; i++) show(node.children); }
      else {
        const section = song.sections(variant).find(s => s.getAttribute('name') === node.section)!;
        const text = node.start === undefined ? section.textContent ?? '' : presentationLines(section.textContent ?? '').slice(node.start - 1, node.end ?? node.start).join('\n');
        area.append(el('h3', node.section + (node.pinned ? ' — připojit k předchozímu bloku' : '')), el('pre', text));
      }
    }
  }
  show(song.tree(rep));
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
  nav.append(file, button('Stáhnout XML', () => {
    const warnings = song.repetitions.flatMap((r,i) => song.diagnostics(r).map(message => `${i+1}. ${r.getAttribute('name')}: ${message}`));
    if (warnings.length && !confirm('XML zachová problematická pořadí; jejich přehrání nemusí fungovat.\n' + warnings.join('\n') + '\nStáhnout beze změny těchto pořadí?')) return;
    download(exportXml(song), song.title); dirty = false; status();
  }), button('Vytvořit kopii', () => {
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
  for (const format of ['TXT', 'DOCX'] as const) {
    const txtFile = el('input'); txtFile.type = 'file'; txtFile.accept = format === 'TXT' ? '.txt,text/plain' : '.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document'; txtFile.setAttribute('aria-label', `Importovat ${format}`);
    const txtPreview = el('section'); txtPreview.setAttribute('aria-label', `Náhled importu ${format}`);
    txtFile.onchange = async () => {
      const selected = txtFile.files?.[0]; txtFile.value = ''; if (!selected) return;
      txtPreview.replaceChildren();
      try {
        const converted = format === 'DOCX' ? await openDocx(selected) : { text: await readUtf8(selected), warnings: [] };
        const source = converted.text;
        function show(resolve = false) {
          const p = parseTxt(source, resolve); txtPreview.replaceChildren(el('h2', `Náhled importu ${format}`), el('p', p.title));
          if (format === 'DOCX') txtPreview.append(el('p', 'Z Wordu se přenášejí texty a pořadí částí. Písma, barvy, styly a rozložení stránek se nepřenášejí.'));
          for (const warning of converted.warnings) txtPreview.append(el('p', warning));
          for (const s of p.sections) txtPreview.append(el('h3', s.id), el('pre', s.text));
          txtPreview.append(el('p', 'Pořadí: ' + p.order.join(' → ')));
          for (const problem of p.problems) txtPreview.append(el('p', problem));
          for (const conflict of p.conflicts) txtPreview.append(el('p', conflict + (resolve ? ' Vytvořena číslovaná varianta; následující prázdné odkazy míří na ni.' : ' Import je do vyřešení blokován.')));
          if (p.conflicts.length && !resolve) txtPreview.append(button('Vyřešit odlišné texty vytvořením variant', () => show(true)));
          const blocked = !!p.problems.length || (!!p.conflicts.length && !resolve);
          const sameTitle = (a: string, b: string) => a.normalize('NFC').trim().toLocaleLowerCase('cs') === b.normalize('NFC').trim().toLocaleLowerCase('cs');
          const known = [song, ...(original ? [original.song] : [])];
          const matches = known.filter(s => sameTitle(s.title, p.title));
          txtPreview.append(el('p', matches.length ? 'Píseň se stejným názvem už je otevřená. Chcete upravit její jazyk, nebo vytvořit novou píseň s jiným názvem?' : 'Import vytvoří novou píseň. Shodu názvu kontrolujeme jen s otevřeným konceptem a jeho případným originálem; knihovnu na disku web neprohledává.'));
          for (const target of matches) {
            const langLabel = el('label', 'Jazyk pro přepsání textů'), language = el('select');
            language.setAttribute('aria-label', target === song ? 'Jazyk pro přepsání textů' : 'Jazyk původní písně pro přepsání');
            target.variants.forEach((v, i) => { const o = el('option', v.getAttribute('name')!); o.value = String(i); language.append(o); });
            language.value = String(target === song ? variantIndex : 0); langLabel.append(language); txtPreview.append(langLabel);
            txtPreview.append(el('p', `Nahradí se texty odpovídajících částí pouze zvoleného jazyka. Ostatní jazyky, vynechané části, všechna původní pořadí, metadata i identita zůstanou zachované. Nové části mohou v jiných jazycích chybět. Změněné pořadí z ${format} se přidá jako nové pořadí ${format}; výchozí se nezmění.`));
            txtPreview.append(button(target === song ? 'Přepsat texty vybraného jazyka' : 'Přepsat texty jazyka původní písně', () => {
              const index = Number(language.value);
              const result = updateLanguageFromTxt(target, p, index, target === song ? repetitionIndex : target.repetitions.indexOf(target.selectedRepetition), format);
              if (!confirm(`Přepsat texty jazyka „${target.variants[index].getAttribute('name')}“ písně „${target.title}“?${result.addedOrder ? ` Pořadí z ${format} bude přidáno jako nové, původní pořadí zůstanou.` : ''}`)) return;
              if (!mayReplace(true)) return;
              original = undefined; replace(result.song, true); variantIndex = index; render();
            }, blocked));
          }
          const newLanguageLabel = el('label', 'Jazyk nové písně'), newLanguage = el('input');
          newLanguage.setAttribute('aria-label', 'Jazyk nové písně'); newLanguage.value = 'čeština'; newLanguageLabel.append(newLanguage);
          txtPreview.append(newLanguageLabel, button(matches.length ? 'Vytvořit novou s jiným názvem' : 'Importovat jako novou píseň', () => {
            let title = p.title;
            if (matches.length) {
              const answer = prompt('Název nové písně:', p.title + ' (nová)'); if (!answer?.trim()) return;
              title = answer.trim();
              if (known.some(s => sameTitle(s.title, title))) throw new Error('Zadejte nový název odlišný od otevřených písní.');
            }
            const next = songFromTxt({ ...p, title, language: newLanguage.value.trim() });
            if (!mayReplace(true)) return;
            original = undefined; replace(next, true);
          }, blocked), button(`Zrušit import ${format}`, () => txtPreview.replaceChildren()));
        }
        show();
      } catch (e) { alert((e as Error).message); }
    };
    const txtExport = el('section');
    app.append(button(`Stáhnout ${format}`, () => {
      txtExport.replaceChildren(el('h2', `Stažení ${format}`));
      const language = el('select'), order = el('select');
      language.setAttribute('aria-label', `Jazyk pro ${format}`); order.setAttribute('aria-label', `Pořadí pro ${format}`);
      song.variants.forEach((v, i) => { const o = el('option', v.getAttribute('name')!); o.value = String(i); language.append(o); });
      song.repetitions.forEach((r, i) => { const o = el('option', `${i + 1}. ${r.getAttribute('name')}`); o.value = String(i); order.append(o); });
      language.value = String(variantIndex); order.value = String(repetitionIndex);
      const languageLabel = el('label', `Jazyk pro ${format}`); languageLabel.append(language);
      const orderLabel = el('label', `Pořadí pro ${format}`); orderLabel.append(order);
      txtExport.append(languageLabel, orderLabel, el('p', `${format} obsahuje jen název, texty vybraného jazyka a vybrané jednoduché pořadí. Neobsahuje identitu, další jazyky a pořadí ani metadata. Plnou zálohu stáhněte jako XML. Pro návrat změn ponechte stejný název a otevřenou původní píseň.`));
      if (format === 'DOCX') txtExport.append(el('p', 'Ve Wordu upravujte běžné odstavce. Formátování se při návratu nepřebírá; nepoužívejte tabulky, textová pole ani automatické číslování nadpisů.'));
      txtExport.append(button(`Stáhnout vybraný jazyk do ${format}`, () => {
        const index = Number(language.value);
        const text = format === 'TXT' ? exportTxt(song, index, Number(order.value)) : exportDocx(song, index, Number(order.value));
        download(text, song.title + ' - ' + song.variants[index].getAttribute('name'), format.toLowerCase()); txtExport.replaceChildren();
      }), button(`Zrušit stažení ${format}`, () => txtExport.replaceChildren()));
    }), button(`Stáhnout prázdnou ${format} šablonu`, () => download(format === 'TXT' ? txtTemplate : docxTemplate(), 'sablona-pisne', format.toLowerCase())), txtFile,
    el('p', `${format} pro ${format === 'TXT' ? 'Poznámkový blok' : 'Word'}: název na prvním řádku, potom Sloka 1, Refrén 1, Bridge 1 a texty. Dvojtečky nejsou potřeba. Před importem se zobrazí náhled.`), txtExport, txtPreview);
  }
  app.append(field('Název písně', song.title, value => { song.title = value; }));
  app.append(Object.assign(el('p'), { id: 'storage' }));
  if (recoveryFailed) app.append(button('Stáhnout zálohu konceptu', () => { download(localStorage.getItem(storageKey) ?? '', 'zaloha-konceptu', 'json'); }), button('Povolit nový místní koncept', () => { if (confirm('Přepsat nečitelnou zálohu? Nejprve ji stáhněte.')) { recoveryFailed = false; status(); } }));
  const vlabel = el('label', 'Jazyková varianta'); const vselect = el('select');
  vselect.setAttribute('aria-label', 'Jazyková varianta');
  song.variants.forEach((v,i) => { const opt = el('option', v.getAttribute('name')!); opt.value = String(i); vselect.append(opt); });
  vselect.value = String(variantIndex); vselect.onchange = () => { variantIndex = Number(vselect.value); render(); }; vlabel.append(vselect); app.append(vlabel);
  const variant = song.variants[variantIndex];
  app.append(button('Přejmenovat jazyk', () => {
    const name = prompt('Název jazyka:', variant.getAttribute('name') ?? ''); if (!name) return;
    if (!name.trim() || song.variants.some(v => v !== variant && v.getAttribute('name') === name)) throw new Error('Zadejte neprázdný jedinečný název.');
    variant.setAttribute('name', name); dirty = true; render();
  }));
  app.append(button('Přidat jazyk', () => { const name = prompt('Název nového jazyka (texty budou prázdné):'); if (!name) return; const v = song.addVariant(name); variantIndex = song.variants.indexOf(v); dirty = true; render(); }));
  app.append(button('Odebrat jazyk', () => {
    const nested = Array.from(variant.children).filter(e => e.tagName === 'repetition');
    const remainingIds = new Set(song.variants.filter(v => v !== variant).flatMap(v => song.sections(v).map(s => s.getAttribute('name'))));
    const lostIds = song.sections(variant).map(s => s.getAttribute('name')!).filter(id => !remainingIds.has(id));
    const warning = lostIds.length ? `\nČásti ${lostIds.join(', ')} nejsou v žádném jiném jazyce. Odkazy na ně zůstanou zachovány, ale příslušná pořadí budou uzamčena s chybou chybějící části.` : '';
    if (!confirm(`Odebrat jazyk „${variant.getAttribute('name')}“ a všech jeho ${song.sections(variant).length} textů? Ostatní jazyky zůstanou zachovány.\n${nested.length} pořadí uvnitř tohoto jazyka bude přesunuto ke společným pořadím; jejich obsah, vzájemné pořadí a výchozí označení se zachovají.${warning}\nPro zálohu textů nejprve stáhněte XML.`)) return;
    const selected = song.repetitions[repetitionIndex];
    song.removeVariant(variant);
    variantIndex = Math.min(variantIndex, song.variants.length - 1);
    repetitionIndex = song.repetitions.indexOf(selected);
    dirty = true; render();
  }, song.variants.length <= 1));
  app.append(el('p', 'Každý jazyk má vlastní text. Nový jazyk dostane stejné části s prázdnými texty. Názvy jazyků se automaticky nepřekládají.'));
  app.append(el('h2', 'Části — text se sdílí ve všech výskytech pořadí'));
  const sections = song.sections(variant);
  sections.forEach((section,i) => {
    const id = section.getAttribute('name')!; const card = el('section');
    card.append(field(id, section.textContent ?? '', value => { section.textContent = value; }, true));
    for (const delta of [-1,1]) card.append(button(delta < 0 ? 'Část nahoru' : 'Část dolů', () => {
      const other = sections[i + delta];
      if (delta < 0) variant.insertBefore(section, other); else variant.insertBefore(other, section);
      dirty = true; render();
    }, i + delta < 0 || i + delta >= sections.length));
    card.append(button('Odebrat část', () => {
      if (song.repetitions.some(r => song.diagnostics(r).length)) throw new Error('Mazání je blokováno: nejprve opravte nebo nahraďte uzamčená pořadí. Nelze bezpečně určit všechny odkazy.');
      const impacts = song.repetitions.map((r,i) => `${i+1}. ${r.getAttribute('name')}: ${leaves(song.tree(r)).filter(s => s.section === id).length} odkazů (uvnitř skupin se mohou opakovat)`).join('\n');
      if (confirm(`Odebrat ${id} ze všech ${song.variants.length} variant? Odstraní se odkazy a vyprázdněné skupiny:\n${impacts}`)) { song.removeSection(id); dirty = true; render(); }
    })); app.append(card);
  });
  for (const [label,prefix] of [['Sloka','v'],['Refrén','r'],['Bridge','b'],['Vlastní blok','s']]) app.append(button(`Přidat: ${label}`, () => {
    let chosen = prefix;
    if (prefix === 's') { const value = prompt('Název vlastního typu (písmena, čísla, pomlčka):', 'solo'); if (!value) return; if (!/^[\p{L}\p{N}_-]+$/u.test(value)) throw new Error('Použijte písmena, čísla, podtržítko nebo pomlčku.'); chosen = value; }
    song.addSection(chosen); dirty = true; render();
  }));
  app.append(el('h2', 'Pořadí přehrávání'));
  const rlabel = el('label', 'Pojmenované pořadí'); const rselect = el('select');
  rselect.setAttribute('aria-label', 'Pojmenované pořadí');
  song.repetitions.forEach((r,i) => { const opt = el('option', `${i+1}. ${r.getAttribute('name') ?? '(bez jména)'}${r === song.selectedRepetition ? ' — výchozí' : ''}${r.parentElement === song.root ? '' : ' — uvnitř jazyka'}`); opt.value = String(i); rselect.append(opt); });
  rselect.value = String(repetitionIndex); rselect.onchange = () => { repetitionIndex = Number(rselect.value); render(); }; rlabel.append(rselect); app.append(rlabel);
  const rep = song.repetitions[repetitionIndex];
  app.append(button('Znovu ověřit pořadí po změně textů', () => render()));
  app.append(button('Přidat pojmenované pořadí', () => { const name = prompt('Jméno nového pořadí:'); if (!name) return; const r = song.addRepetition(name); repetitionIndex = song.repetitions.indexOf(r); dirty = true; render(); }));
  if (!rep) {
    app.append(el('p', 'Import nemá žádné pořadí; žádné nebylo automaticky doplněno.'), Object.assign(el('div'), { id: 'preview' })); status(); preview(); return;
  }
  app.append(button('Přejmenovat pořadí', () => {
    const name = prompt('Nové jedinečné jméno pořadí:', rep.getAttribute('name') ?? ''); if (!name) return;
    if (song.repetitions.some(r => r !== rep && r.getAttribute('name') === name)) throw new Error('Toto jméno již existuje.');
    rep.setAttribute('name', name); dirty = true; render();
  }), button('Nastavit jako výchozí', () => {
    if (!confirm('Nastavit toto pořadí jako jediné výchozí? Případná ostatní označení main budou odstraněna.')) return;
    song.setDefault(rep); dirty = true; render();
  }));
  const names = song.repetitions.map(r => r.getAttribute('name'));
  if (new Set(names).size !== names.length || names.some(n => !n?.trim()) || song.repetitions.filter(r => /^(1|true|yes)$/i.test(r.getAttribute('main') ?? '')).length > 1) app.append(el('p', 'Import obsahuje shodná/prázdná jména nebo více výchozích pořadí. Všechna jsou zachována a odlišena číslem a umístěním. Výběr: první main, jinak default, jinak první. Přejmenování a nastavení výchozího je výslovné.'));
  const errors = song.diagnostics(rep);
  if (errors.length) {
    app.append(el('p', 'Importované pořadí je uzamčené. Texty lze upravit a XML stáhnout se zachovaným původním pořadím. ' + errors.join('\n')), el('pre', rep.textContent ?? ''));
    app.append(button('Sestavit náhradní pořadí', () => {
      if (!confirm('Nahradit celé vybrané pořadí první částí? Původní výraz se tím z tohoto konceptu odstraní. Pro jeho uchování nejprve stáhněte XML.')) return;
      song.saveTree(rep, [{ section: song.ids[0], pinned: false }]); dirty = true; render();
    }, !song.ids.length));
  } else {
    const tree = song.tree(rep);
    function save() { song.saveTree(rep, tree); dirty = true; render(); }
    function edit(nodes: Node[], parent: HTMLElement) {
      nodes.forEach((node,i) => {
        const row = el('fieldset'); row.append(el('legend', 'children' in node ? 'Opakovaná skupina' : `Část ${node.section}`));
        for (const delta of [-1,1]) row.append(button(delta < 0 ? 'Výskyt nahoru' : 'Výskyt dolů', () => { move(nodes,i,delta); save(); }, i + delta < 0 || i + delta >= nodes.length));
        row.append(button('Odebrat výskyt', () => { nodes.splice(i,1); save(); }, nodes.length <= 1));
        row.append(button('Opakovat tento blok', () => { nodes[i] = { children: [node], repeat: 2 }; save(); }));
        row.append(button('Seskupit s následujícím', () => { nodes.splice(i,2,{ children: [node,nodes[i+1]], repeat: 2 }); save(); }, i === nodes.length - 1));
        const numeric = (caption: string, value: number, apply: (n: number) => void) => {
          const label = el('label', caption), input = el('input'); input.type = 'number'; input.min = '1'; input.max = '4096'; input.value = String(value);
          input.onchange = () => { try { const n = Number(input.value); if (!Number.isInteger(n) || n < 1 || n > 4096) throw new Error('Zadejte celé číslo 1 až 4096.'); apply(n); save(); } catch(e) { alert((e as Error).message); render(); } }; label.append(input); row.append(label);
        };
        if ('children' in node) {
          numeric('Počet opakování', node.repeat, n => { node.repeat = n; });
          row.append(button('Zrušit skupinu (ponechat jeden průchod)', () => { nodes.splice(i,1,...node.children); save(); }));
          edit(node.children,row);
        } else {
          const label = el('label', 'Připojit k předchozímu bloku při volné kapacitě'), check = el('input'); check.type = 'checkbox'; check.checked = node.pinned;
          check.onchange = () => { node.pinned = check.checked; save(); }; label.append(check); row.append(label);
          row.append(button(node.start === undefined ? 'Vybrat řádky' : 'Použít celou část', () => { if (node.start === undefined) node.start = 1; else { delete node.start; delete node.end; } save(); }));
          if (node.start !== undefined) {
            numeric('Od řádku (po odstranění prázdných řádků)', node.start, n => { node.start = n; });
            numeric('Do řádku (včetně; stejné číslo = jeden řádek)', node.end ?? node.start, n => { if (n === node.start) delete node.end; else node.end = n; });
          }
        }
        parent.append(row);
      });
      for (const id of song.ids) parent.append(button(`Zařadit ${id}`, () => { nodes.push({ section: id, pinned: false }); save(); }));
    }
    edit(tree,app);
  }
  app.append(el('p', 'Skupiny zachovávají své hranice i vnoření. Náhled ukazuje posloupnost, nikoli stránkování a styly projektoru; připojení závisí na jeho kapacitě.'));
  app.append(el('h2', 'Náhled výsledného pořadí'), Object.assign(el('div'), { id: 'preview' })); status(); preview();
}
window.addEventListener('beforeunload', event => { if (dirty || original?.dirty) { event.preventDefault(); event.returnValue = ''; } });
render();

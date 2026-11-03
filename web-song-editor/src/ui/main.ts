import { newSong, presentationLines, type SongDocument } from '../domain/song';
import { exportXml, importXml } from '../xml/songXml';
import { leaves, removeReferences, serializeTree, type Node, type Step } from '../construct/tree';
import { openFile, readUtf8, openDocx, download } from '../io/files';
import { exportTxt, parseTxt, songFromTxt, txtTemplate, updateLanguageFromTxt } from '../io/songTxt';
import { exportDocx, docxTemplate } from '../io/songDocx';
import './style.css';
import { orderBuilder } from './orderBuilder';
import { saveNamedOrder } from './namedOrder';

function emptySong() { const song = newSong(); song.selectedRepetition.textContent = ''; return song; }
let song = emptySong(), dirty = true, variantIndex = 0, repetitionIndex = 0;
let orderDraft!: Element, orderName = '';
let restoredOrder: { name: string; guide: string } | undefined;
function resetOrder() {
  const source = song.repetitions[repetitionIndex] ?? song.selectedRepetition;
  orderDraft = source?.cloneNode(true) as Element ?? song.xml.createElement('repetition');
  orderName = source?.getAttribute('name') ?? '';
  if (orderName === 'default') orderName = '';
}
function currentSong() { return saveNamedOrder(song, repetitionIndex, orderDraft, orderName); }
let original: { song: SongDocument; dirty: boolean } | undefined;
let lineSelections: Step[][] = [];
const storageKey = 'superpresenter-song-draft-v1';
let storageMessage = '', recoveryFailed = false;
let feedback = '';
let focusedControl: { name: string; index: number } | undefined;
function controlName(control: Element) {
  return control.getAttribute('aria-label') ?? control.closest('label')?.firstChild?.textContent ?? '';
}
function detailsKey(details: HTMLDetailsElement) {
  return `${details.closest('fieldset')?.dataset.orderPath ?? ''}:${details.querySelector('summary')?.textContent}`;
}
function sectionName(id: string) {
  const match = /^([vrb])(\d*)$/.exec(id);
  return match ? `${({ v: 'Sloka', r: 'Refrén', b: 'Bridge' } as Record<string, string>)[match[1]]}${match[2] ? ' ' + match[2] : ''}` : id;
}
function announce(message: string) {
  feedback = message;
  const area = document.querySelector('#feedback'); if (area) area.textContent = message;
}
function persist() {
  if (recoveryFailed) return;
  try {
    const xml = (s: SongDocument) => new XMLSerializer().serializeToString(s.root).replace(/\r/g, '&#13;');
    localStorage.setItem(storageKey, JSON.stringify({ version: 1, xml: xml(song), dirty, variantIndex, repetitionIndex, lineSelections, orderName, orderDraftGuide: orderDraft?.textContent, original: original && { xml: xml(original.song), dirty: original.dirty } }));
    if (!storageMessage.includes('obnovena')) storageMessage = 'Koncept je v místním úložišti tohoto prohlížeče.';
  } catch { storageMessage = 'Místní obnova není dostupná (úložiště je plné nebo zakázané). Stáhněte XML.'; }
}
try {
  const raw = localStorage.getItem(storageKey);
  if (raw) {
    const saved = JSON.parse(raw);
    if (saved.version !== 1) throw new Error('Neznámá verze konceptu');
    const next = importXml(saved.xml), previous = saved.original && importXml(saved.original.xml);
    song = next; dirty = !!saved.dirty;
    if (typeof saved.orderName === 'string' && typeof saved.orderDraftGuide === 'string' && saved.orderDraftGuide.length <= 16384) restoredOrder = { name: saved.orderName, guide: saved.orderDraftGuide };
    if (Array.isArray(saved.lineSelections)) {
      lineSelections = saved.lineSelections.slice(0, 4096).filter((group: unknown): group is Step[] => Array.isArray(group) && group.length > 0 && group.length <= 4096 && group.every(s =>
        s && song.ids.includes(s.section) && Number.isInteger(s.start) && s.start >= 1 && s.start <= 4096 &&
        (s.end === undefined || (Number.isInteger(s.end) && s.end >= s.start && s.end <= 4096))
      )).map((group: Step[]) => group.map(s => ({ section: s.section, start: s.start, ...(s.end === undefined ? {} : { end: s.end }), pinned: false })));
    }
    variantIndex = Math.max(0, Math.min(Math.trunc(Number(saved.variantIndex)) || 0, song.variants.length - 1));
    repetitionIndex = Math.max(0, Math.min(Math.trunc(Number(saved.repetitionIndex)) || 0, song.repetitions.length - 1));
    if (previous) original = { song: previous, dirty: !!saved.original.dirty };
    storageMessage = 'Rozpracovaná práce byla obnovena.';
  }
} catch { recoveryFailed = true; storageMessage = 'Uložený koncept nelze načíst. Nebyl přepsán; stáhněte zálohu tlačítkem níže.'; }
resetOrder();
if (restoredOrder) { orderName = restoredOrder.name; orderDraft.textContent = restoredOrder.guide; }
const app = document.querySelector<HTMLElement>('#app')!;
function el<K extends keyof HTMLElementTagNameMap>(tag: K, text = '') {
  const e = document.createElement(tag); e.textContent = text; return e;
}
function button(text: string, action: () => void, disabled = false) {
  const b = el('button', text); b.type = 'button'; b.disabled = disabled;
  b.onclick = () => {
    const index = Array.from(app.querySelectorAll('button')).filter(e => e.textContent === text).indexOf(b);
    try { action(); } catch (e) { alert(String((e as Error).message)); render(); }
    if (!b.isConnected && document.activeElement === document.body) {
      const next = Array.from(app.querySelectorAll('button')).filter(e => e.textContent === text)[index];
      if (next && !next.disabled) next.focus({ preventScroll: true });
    }
  }; return b;
}
function field(caption: string, value: string, change: (value: string) => void, multiline = false) {
  const label = el('label', caption); const input = multiline ? el('textarea') : el('input');
  input.value = value; input.oninput = () => { change(input.value); dirty = true; status(); preview(); };
  label.append(input); return label;
}
function mayReplace(discardOriginal = false) { return !(dirty || (discardOriginal && original?.dirty)) || confirm('Nahrazované koncepty obsahují změny, které nebyly staženy. Zahodit je a pokračovat?'); }
function replace(next: SongDocument, changed: boolean) { feedback = ''; lineSelections = []; song = next; dirty = changed; variantIndex = 0; repetitionIndex = song.repetitions.indexOf(song.selectedRepetition); resetOrder(); render(); }
function status() {
  persist();
  app.dataset.songId = song.id;
  document.querySelector('#recovery-status')!.textContent = storageMessage;
}
function preview() {
  const area = document.querySelector('#preview')!; area.replaceChildren();
  const variant = song.variants[variantIndex];
  const rep = orderDraft;
  if (!rep) { area.append(el('p', 'Soubor nemá pořadí. Je zachován beze změny; můžete výslovně přidat nové pořadí.')); return; }
  if (!rep.textContent?.trim()) { area.append(el('p', 'Přidejte části do pořadí přehrávání.')); return; }
  const errors = song.diagnostics(rep);
  if (errors.length) { area.append(el('p', errors.join('\n'))); return; }
  function show(nodes: Node[]) {
    for (const node of nodes) {
      if ('children' in node) { for (let i = 0; i < node.repeat; i++) show(node.children); }
      else {
        const section = song.sections(variant).find(s => s.getAttribute('name') === node.section)!;
        const text = node.start === undefined ? section.textContent ?? '' : presentationLines(section.textContent ?? '').slice(node.start - 1, node.end ?? node.start).join('\n');
        area.append(el('h3', sectionName(node.section) + (node.pinned ? ' — připojit k předchozímu bloku' : '')), el('pre', text));
      }
    }
  }
  show(song.tree(rep));
}
function render() {
  const active = document.activeElement;
  focusedControl = active?.matches('input, select, textarea') ? {
    name: controlName(active),
    index: Array.from(app.querySelectorAll('input, select, textarea')).filter(e => controlName(e) === controlName(active)).indexOf(active),
  } : undefined;
  const expanded = new Map(Array.from(app.querySelectorAll('details')).map(d => [detailsKey(d), d.open]));
  app.replaceChildren(el('h1', 'Baptisté Šumperk: Editor písní'));
  const nav = el('nav');
  nav.append(button('Nová píseň', () => { if (mayReplace(true)) { original = undefined; replace(emptySong(), true); } }));
  const file = el('input'); file.type = 'file'; file.accept = '.xml,application/xml,text/xml'; file.setAttribute('aria-label', 'Otevřít XML');
  file.onchange = async () => {
    const selected = file.files?.[0]; file.value = ''; if (!selected) return;
    try {
      // Parsing is transactional: invalid input never replaces the current draft.
      const next = await openFile(selected);
      if (mayReplace(true)) { original = undefined; replace(next, true); }
    } catch (e) { alert((e as Error).message); }
  };
  file.hidden = true;
  const open = button('Otevřít', () => file.click());
  const xmlDownload = button('XML', () => {
    downloads.open = false; downloads.querySelector('summary')?.focus();
    const output = currentSong();
    const warnings = output.repetitions.flatMap((r,i) => output.diagnostics(r).map(message => `${i+1}. ${r.getAttribute('name')}: ${message}`));
    if (warnings.length && !confirm('XML zachová problematická pořadí; jejich přehrání nemusí fungovat.\n' + warnings.join('\n') + '\nStáhnout beze změny těchto pořadí?')) return;
    download(exportXml(output), song.title);
    song = output; repetitionIndex = song.repetitions.indexOf(song.selectedRepetition); resetOrder(); dirty = false; render();
    announce('XML předáno prohlížeči ke stažení. Původní soubor na disku se nezměnil.');
    app.querySelector<HTMLElement>('.export-menu > summary')?.focus({ preventScroll: true });
  });
  if (original) nav.append(button('Vrátit původní koncept', () => {
    if (!mayReplace()) return; const saved = original!; original = undefined; replace(saved.song, saved.dirty);
  }));
  nav.append(open, file);
  app.append(nav);
  nav.className = 'main-actions';
  app.append(Object.assign(el('p', feedback), { id: 'feedback', role: 'status' }), Object.assign(el('p'), { id: 'recovery-status', role: 'status' }));
  const transfers = el('div'); transfers.className = 'transfers'; app.append(transfers);
  const importArea = el('div'); importArea.id = 'import-area'; app.append(importArea);
  const importers = {} as Record<'TXT' | 'DOCX', (selected: File) => Promise<void>>;
  const importFile = el('input'); importFile.type = 'file'; importFile.hidden = true;
  importFile.accept = '.txt,.docx,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  importFile.setAttribute('aria-label', 'Importovat TXT nebo Word');
  importFile.onchange = async () => {
    const selected = importFile.files?.[0]; importFile.value = ''; if (!selected) return;
    if (!/\.(txt|docx)$/i.test(selected.name)) { alert('Vyberte soubor TXT nebo Word (.docx).'); return; }
    importArea.querySelectorAll('section').forEach(s => s.replaceChildren());
    await importers[/\.docx$/i.test(selected.name) ? 'DOCX' : 'TXT'](selected);
  };
  nav.append(button('Importovat', () => importFile.click()), importFile);
  const templates = el('details'); templates.className = 'template-menu';
  const templateOptions = el('div'); templateOptions.className = 'template-options';
  templates.append(el('summary', 'Stáhnout šablonu'), templateOptions); nav.append(templates);
  templates.onkeydown = event => {
    if (event.key === 'Escape') { templates.open = false; templates.querySelector('summary')?.focus(); }
  };
  const downloads = el('details'); downloads.className = 'template-menu export-menu';
  const downloadOptions = el('div'); downloadOptions.className = 'template-options';
  downloadOptions.append(xmlDownload);
  downloads.append(el('summary', 'Stáhnout'), downloadOptions); nav.append(downloads);
  const save = button('Uložit', () => {}, true);
  save.className = 'database-save';
  save.title = 'Ukládání do společné databáze zatím není dostupné.';
  nav.append(save);
  downloads.onkeydown = event => {
    if (event.key === 'Escape') { downloads.open = false; downloads.querySelector('summary')?.focus(); }
  };
  for (const format of ['TXT', 'DOCX'] as const) {
    const txtPreview = el('section'); txtPreview.setAttribute('aria-label', `Náhled importu ${format}`);
    importArea.append(txtPreview);
    importers[format] = async (selected: File) => {
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
              const targetDocument = target === song ? currentSong() : target;
              const result = updateLanguageFromTxt(targetDocument, p, index, targetDocument.repetitions.indexOf(targetDocument.selectedRepetition), format);
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
        txtPreview.tabIndex = -1; txtPreview.focus();
      } catch (e) { alert((e as Error).message); }
    };
    const txtExport = el('dialog'); txtExport.className = 'export-dialog'; txtExport.setAttribute('aria-label', `Stažení ${format}`); transfers.append(txtExport);
    txtExport.onclose = () => downloads.querySelector('summary')?.focus();
    downloadOptions.append(button(format, () => {
      downloads.open = false;
      txtExport.replaceChildren(el('h2', `Stažení ${format}`));
      const language = el('select');
      language.setAttribute('aria-label', `Jazyk pro ${format}`);
      song.variants.forEach((v, i) => { const o = el('option', v.getAttribute('name')!); o.value = String(i); language.append(o); });
      language.value = String(variantIndex);
      const languageLabel = el('label', `Jazyk pro ${format}`); languageLabel.append(language);
      txtExport.append(languageLabel, el('p', `${format} obsahuje jen název, texty vybraného jazyka a právě sestavené jednoduché pořadí. Neobsahuje identitu, další jazyky a pořadí ani metadata. Plnou zálohu stáhněte jako XML. Pro návrat změn ponechte stejný název a otevřenou původní píseň.`));
      if (format === 'DOCX') txtExport.append(el('p', 'Ve Wordu upravujte běžné odstavce. Formátování se při návratu nepřebírá; nepoužívejte tabulky, textová pole ani automatické číslování nadpisů.'));
      txtExport.append(button(`Stáhnout vybraný jazyk do ${format}`, () => {
        const index = Number(language.value);
        const output = currentSong(), selected = output.repetitions.indexOf(output.selectedRepetition);
        const text = format === 'TXT' ? exportTxt(output, index, selected) : exportDocx(output, index, selected);
        download(text, song.title + ' - ' + song.variants[index].getAttribute('name'), format.toLowerCase()); txtExport.close(); txtExport.replaceChildren(); announce(`${format} předáno prohlížeči ke stažení. Úplnou zálohu uchovejte v XML.`);
      }), button(`Zrušit stažení ${format}`, () => txtExport.close()));
      txtExport.showModal();
    }));
    templateOptions.append(button(format === 'TXT' ? 'TXT' : 'Word', () => {
      download(format === 'TXT' ? txtTemplate : docxTemplate(), 'sablona-pisne', format.toLowerCase());
      templates.open = false; templates.querySelector('summary')?.focus();
    }));
  }
  const titleField = field('Název písně', song.title, value => { song.title = value; });
  titleField.querySelector('input')!.placeholder = 'Zadejte název písně'; app.append(titleField);
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
  sections.forEach(section => {
    const id = section.getAttribute('name')!; const card = el('section');
    card.className = 'text-card'; card.dataset.section = id;
    const header = el('div'); header.className = 'text-card-header';
    const remove = button('×', () => {
      if (orderDraft.textContent?.trim() && song.diagnostics(orderDraft).length) throw new Error('Mazání je blokováno: nejprve opravte uzamčené pořadí. Nelze bezpečně určit odkazy.');
      if (song.repetitions.some(r => r.textContent?.trim() && song.diagnostics(r).length)) throw new Error('Mazání je blokováno: nejprve opravte nebo nahraďte uzamčená pořadí. Nelze bezpečně určit všechny odkazy.');
      const impacts = song.repetitions.map((r,i) => `${i+1}. ${r.getAttribute('name')}: ${r.textContent?.trim() ? leaves(song.tree(r)).filter(s => s.section === id).length : 0} odkazů (uvnitř skupin se mohou opakovat)`).join('\n');
      if (confirm(`Odebrat ${id} ze všech ${song.variants.length} variant? Odstraní se odkazy a vyprázdněné skupiny:\n${impacts}`)) {
        const next = orderDraft.textContent?.trim() ? removeReferences(song.tree(orderDraft), id) : [];
        song.removeSection(id); orderDraft.textContent = serializeTree(next); dirty = true; render();
      }
    });
    remove.setAttribute('aria-label', `Odebrat část: ${sectionName(id)}`);
    header.append(el('h3', sectionName(id)), remove);
    card.append(header, field(sectionName(id), section.textContent ?? '', value => { section.textContent = value; }, true));
    app.append(card);
  });
  for (const [label,prefix] of [['Sloka','v'],['Refrén','r'],['Bridge','b']]) app.append(button(label, () => {
    const id = song.addSection(prefix); dirty = true; render();
    app.querySelector<HTMLTextAreaElement>(`[data-section="${CSS.escape(id)}"] textarea`)?.focus();
  }));
  app.append(el('h2', 'Pořadí přehrávání'));
  const rep = orderDraft;
  const nameField = field('Název opakování', orderName, value => { orderName = value; });
  nameField.querySelector('input')!.placeholder = 'default'; app.append(nameField);
  const errors = rep.textContent?.trim() ? song.diagnostics(rep) : [];
  if (errors.length) {
    app.append(el('p', 'Importované pořadí je uzamčené. Texty lze upravit a XML stáhnout se zachovaným původním pořadím. ' + errors.join('\n')), el('pre', rep.textContent ?? ''));
    app.append(button('Sestavit náhradní pořadí', () => {
      if (!confirm('Nahradit celé vybrané pořadí první částí? Původní výraz se tím z tohoto konceptu odstraní. Pro jeho uchování nejprve stáhněte XML.')) return;
      song.saveTree(rep, [{ section: song.ids[0], pinned: false }]); dirty = true; render();
    }, !song.ids.length));
  } else {
    const tree = rep.textContent?.trim() ? song.tree(rep) : [];
    app.append(orderBuilder(song, variant, tree, next => {
      if (next.length) song.saveTree(rep, next); else rep.textContent = '';
      dirty = true; render();
    }, lineSelections));
  }
  const result = el('details'); result.className = 'result'; result.id = 'result';
  result.append(el('summary', 'Náhled výsledného pořadí'), Object.assign(el('div'), { id: 'preview' }));
  app.append(result); arrange(expanded); status(); preview();
}
function arrange(expanded: Map<string, boolean>) {
  const children = Array.from(app.children);
  const title = children.findIndex(e => e.tagName === 'LABEL' && e.textContent === 'Název písně');
  const order = children.findIndex(e => e.tagName === 'H2' && e.textContent === 'Pořadí přehrávání');
  const previewHeading = children.findIndex(e => e.id === 'result');
  if (title < 0 || order < 0) return;
  children[title].classList.add('song-title');
  const transfers = app.querySelector('.transfers');
  app.insertBefore(children[title], transfers);
  const workspace = el('div'); workspace.className = 'workspace';
  const writing = el('div'); writing.className = 'writing'; writing.id = 'writing';
  const sequence = el('div'); sequence.className = 'sequence'; sequence.id = 'sequence';
  for (const child of children.slice(title + 1, order)) writing.append(child);
  const boundary = previewHeading < 0 ? children.length - 1 : previewHeading;
  for (const child of children.slice(order, boundary)) sequence.append(child);
  for (const child of children.slice(boundary)) sequence.append(child);
  const languageTools = el('details'); languageTools.id = 'language-tools'; languageTools.append(el('summary', 'Správa jazyků'));
  const languageChildren = Array.from(writing.children);
  const languageStart = languageChildren.findIndex(e => e.tagName === 'BUTTON' && e.textContent === 'Přejmenovat jazyk');
  const languageEnd = languageChildren.findIndex(e => e.tagName === 'H2');
  if (languageStart >= 0 && languageEnd > languageStart) {
    writing.insertBefore(languageTools, languageChildren[languageStart]);
    for (const child of languageChildren.slice(languageStart, languageEnd)) languageTools.append(child);
  }
  workspace.append(writing, sequence); app.append(workspace);
  const footer = el('footer'); footer.className = 'page-footer';
  footer.append(el('p', 'Společná knihovna zatím není zavedena. Změny se do SuperPresenteru automaticky nepředávají. Písně zpracovává pouze váš prohlížeč; přenos proveďte ručně stažením XML.'));
  footer.append(el('p', 'Místní koncept není záloha. Pravidelně stahujte XML; vymazání dat prohlížeče nebo změna adresy může obnovu znemožnit.'));
  const recovery = app.querySelector('#recovery-status'); if (recovery) footer.append(recovery);
  const languages = el('div'); languages.id = 'languages'; languages.className = 'languages';
  languages.append(el('h2', 'Jazyky'));
  const languageLabel = writing.querySelector('select[aria-label="Jazyková varianta"]')?.closest('label');
  if (languageLabel) languages.append(languageLabel);
  languages.append(languageTools); footer.append(languages); app.append(footer);
  app.querySelectorAll('details').forEach(d => { d.open = expanded.get(detailsKey(d)) ?? false; });
  if (focusedControl) {
    const { name, index } = focusedControl;
    const next = Array.from(app.querySelectorAll<HTMLElement>('input, select, textarea')).filter(e => controlName(e) === name)[index];
    next?.focus({ preventScroll: true });
  }
}
window.addEventListener('beforeunload', event => { if (dirty || original?.dirty) { event.preventDefault(); event.returnValue = ''; } });
document.addEventListener('click', event => {
  app.querySelectorAll<HTMLDetailsElement>('.template-menu').forEach(menu => {
    if (menu.open && event.target instanceof globalThis.Node && !menu.contains(event.target)) menu.open = false;
  });
});
render();

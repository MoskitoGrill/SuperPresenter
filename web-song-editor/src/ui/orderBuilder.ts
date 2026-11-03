import { presentationLines, type SongDocument } from '../domain/song';
import { leaves, type Node, type Step } from '../construct/tree';

const names: Record<string, string> = { v: 'Sloka', r: 'Refrén', b: 'Bridge' };
function name(id: string): string {
  const match = /^([vrb])(\d*)$/.exec(id);
  return match ? names[match[1]] + (match[2] ? ' ' + match[2] : '') : id;
}
function element<K extends keyof HTMLElementTagNameMap>(tag: K, text = '') {
  const node = document.createElement(tag); node.textContent = text; return node;
}
function action(text: string, run: () => void) {
  const button = element('button', text); button.type = 'button';
  button.onclick = () => { try { run(); } catch (error) { alert((error as Error).message); } }; return button;
}

export function orderBuilder(song: SongDocument, variant: Element, tree: Node[], change: (next: Node[]) => void, selections: Step[][]) {
  const root = element('div'); root.className = 'order-builder';
  const available = element('div'); available.className = 'available-parts';
  available.append(element('h3', 'Části k přidání'), element('p', 'Kliknutím přidáte část na konec.'));
  const sequence = element('div'); sequence.className = 'chosen-order';
  sequence.append(element('h3', 'Sestavené pořadí'), element('p', 'Přetáhněte část na nové místo. Klávesnicí: Alt + ↑ / ↓.'));
  const list = element('ol'); list.className = 'order-list'; sequence.append(list);
  function apply(next: Node[], focusIndex?: number) {
    change(next);
    if (focusIndex !== undefined) document.querySelector<HTMLElement>(`.order-list > li:nth-child(${focusIndex + 1}) .order-handle`)?.focus();
  }
  function move(from: number, to: number) {
    if (to < 0 || to >= tree.length || from === to) return;
    const next = structuredClone(tree); const [item] = next.splice(from, 1); next.splice(to, 0, item); apply(next, to);
  }
  const selectionKey = (steps: Step[]) => JSON.stringify(steps.map(s => [s.section, s.start, s.end ?? s.start]));
  function remember(steps: Step[]) {
    if (selections.some(s => selectionKey(s) === selectionKey(steps))) return false;
    selections.push(steps.map(s => ({ ...s, pinned: false }))); return true;
  }
  // Imported row ranges become reusable too, without changing their XML.
  for (const step of leaves(tree)) if (step.start !== undefined && !selections.some(group => group.some(s => selectionKey([s]) === selectionKey([step])))) remember([step]);
  for (const section of song.sections(variant)) {
    const id = section.getAttribute('name')!;
    available.append(action(name(id), () => {
      apply([...tree, { section: id, pinned: false }]);
      Array.from(document.querySelectorAll<HTMLButtonElement>('.available-parts > button')).find(b => b.textContent === name(id))?.focus({ preventScroll: true });
    }));
  }

  function rowsDialog(existing?: { step: Step; index: number }) {
    const dialog = element('dialog'); dialog.className = 'lines-dialog';
    const title = element('h2', existing ? 'Změnit výběr řádků' : 'Přidat vybrané řádky'); title.id = 'lines-dialog-title';
    dialog.setAttribute('aria-labelledby', title.id);
    const label = element('label', 'Část písně'), select = element('select');
    select.setAttribute('aria-label', 'Část písně');
    for (const section of song.sections(variant)) {
      const option = element('option', name(section.getAttribute('name')!)); option.value = section.getAttribute('name')!; select.append(option);
    }
    if (existing) select.value = existing.step.section;
    label.append(select);
    const lines = element('div'); lines.className = 'line-options';
    const error = element('p'); error.role = 'alert';
    const selected = new Set<number>();
    const submit = action(existing ? 'Použít vybrané řádky' : 'Přidat do pořadí', () => {
      const indices = [...selected].sort((a, b) => a - b);
      if (!indices.length) return;
      const steps: Step[] = [];
      for (const index of indices) {
        const previous = steps.at(-1);
        if (previous && (previous.end ?? previous.start!) === index - 1) previous.end = index;
        else steps.push({ section: select.value, start: index, pinned: false });
      }
      if (existing) steps[0].pinned = existing.step.pinned;
      const next = structuredClone(tree);
      if (existing) next.splice(existing.index, 1, ...steps); else next.push(...steps);
      const added = remember(steps);
      try { change(next); dialog.close(); }
      catch (e) { if (added) selections.pop(); error.textContent = (e as Error).message; }
    });
    let paint: { pointer: number; anchor: number; add: boolean; before: Set<number> } | undefined;
    let suppressPointerClick = false;
    function syncSelection() {
      lines.querySelectorAll<HTMLInputElement>('input').forEach(check => { check.checked = selected.has(Number(check.dataset.line)); });
      submit.disabled = !selected.size;
    }
    function paintThrough(end: number) {
      if (!paint) return;
      selected.clear(); paint.before.forEach(n => selected.add(n));
      for (let n = Math.min(paint.anchor, end); n <= Math.max(paint.anchor, end); n++) {
        if (paint.add) selected.add(n); else selected.delete(n);
      }
      syncSelection();
    }
    lines.onpointerdown = event => {
      if (event.pointerType !== 'mouse' || event.button !== 0 || !(event.target instanceof Element)) return;
      const row = event.target.closest<HTMLElement>('[data-line-row]'); if (!row) return;
      event.preventDefault();
      const anchor = Number(row.dataset.lineRow);
      paint = { pointer: event.pointerId, anchor, add: !selected.has(anchor), before: new Set(selected) };
      suppressPointerClick = true;
      row.querySelector('input')?.focus({ preventScroll: true });
      lines.setPointerCapture(event.pointerId); paintThrough(anchor);
    };
    lines.onpointermove = event => {
      if (!paint || paint.pointer !== event.pointerId) return;
      const row = document.elementFromPoint(event.clientX, event.clientY)?.closest<HTMLElement>('[data-line-row]');
      if (row && lines.contains(row)) paintThrough(Number(row.dataset.lineRow));
    };
    lines.onpointerup = event => {
      if (paint?.pointer !== event.pointerId) return;
      paint = undefined; lines.releasePointerCapture(event.pointerId);
    };
    lines.onpointercancel = () => {
      if (paint) { selected.clear(); paint.before.forEach(n => selected.add(n)); paint = undefined; syncSelection(); }
    };
    // Pointer selection is applied above; cancel the label's extra checkbox toggle.
    // Keyboard/assistive clicks (detail=0), and touch scrolling keep native behavior.
    lines.addEventListener('click', event => {
      if (!suppressPointerClick || event.detail === 0) return;
      event.preventDefault(); suppressPointerClick = false; queueMicrotask(syncSelection);
    }, true);
    function showLines() {
      paint = undefined; suppressPointerClick = false;
      selected.clear(); error.textContent = ''; lines.replaceChildren(); submit.disabled = true;
      const text = song.sections(variant).find(s => s.getAttribute('name') === select.value)?.textContent ?? '';
      const texts = presentationLines(text);
      if (!texts.length) lines.append(element('p', 'Tato část zatím nemá text. Nejdříve jej napište.'));
      texts.forEach((text, i) => {
        const row = element('label'); const check = element('input'); check.type = 'checkbox';
        const number = i + 1;
        row.dataset.lineRow = String(number); check.dataset.line = String(number);
        check.checked = !!existing && select.value === existing.step.section && (existing.step.start === undefined || (number >= existing.step.start && number <= (existing.step.end ?? existing.step.start)));
        if (check.checked) selected.add(number);
        check.onchange = () => { if (check.checked) selected.add(number); else selected.delete(number); submit.disabled = !selected.size; };
        row.append(check, element('span', text)); lines.append(row);
      });
      submit.disabled = !selected.size;
    }
    select.onchange = showLines; showLines();
    dialog.append(title, label, element('p', 'Klikněte na řádek nebo podržte myš a táhněte přes více řádků. Tažení od označeného řádku výběr ruší. Prázdné řádky se při přehrávání vynechávají.'), lines, error, submit, action('Zrušit', () => dialog.close()));
    dialog.onclose = () => { dialog.remove(); document.querySelector<HTMLButtonElement>('.add-lines')?.focus(); };
    document.body.append(dialog); dialog.showModal();
  }
  const addLines = action('Řádky', () => rowsDialog()); addLines.className = 'add-lines'; available.append(addLines);
  if (selections.length) {
    const shortcuts = element('div'); shortcuts.className = 'saved-line-selections';
    shortcuts.append(element('h3', 'Vybrané řádky'));
    selections.forEach((steps, index) => {
      const section = steps[0].section;
      const text = `${name(section)} · řádky ${steps.map(s => s.start + (s.end !== undefined && s.end !== s.start ? '–' + s.end : '')).join(', ')}`;
      const count = presentationLines(song.sections(variant).find(s => s.getAttribute('name') === section)?.textContent ?? '').length;
      const button = action(text, () => {
        apply([...tree, ...structuredClone(steps)]);
        document.querySelector<HTMLButtonElement>(`[data-line-selection="${index}"]`)?.focus({ preventScroll: true });
      });
      button.dataset.lineSelection = String(index);
      button.disabled = !steps.every(s => (s.end ?? s.start ?? 0) <= count);
      if (button.disabled) button.title = 'Výběr přesahuje současný text tohoto jazyka. Upravte jej přes Řádky.';
      shortcuts.append(button);
    });
    available.append(shortcuts);
  }
  let dragged: number | undefined;
  tree.forEach((node, index) => {
    const row = element('li'); row.dataset.index = String(index); row.draggable = true;
    const text = 'children' in node ? `Skupina · ${node.repeat}×` : name(node.section) + (node.start === undefined ? '' : ` · řádky ${node.start}${node.end ? '–' + node.end : ''}`) + (node.pinned ? ' · připojená' : '');
    const handle = action('↕ ' + text, () => { if (!('children' in node)) document.querySelector<HTMLTextAreaElement>(`[data-section="${CSS.escape(node.section)}"] textarea`)?.focus(); });
    handle.className = 'order-handle'; handle.setAttribute('aria-description', 'Přetáhněte pro přesun; Alt + šipka nahoru/dolů pro klávesnici. Kliknutím upravíte sdílený text.');
    handle.onkeydown = event => {
      if (event.altKey && ['ArrowUp', 'ArrowDown'].includes(event.key)) { event.preventDefault(); move(index, index + (event.key === 'ArrowUp' ? -1 : 1)); }
    };
    row.ondragstart = event => { dragged = index; event.dataTransfer!.effectAllowed = 'move'; event.dataTransfer!.setData('text/plain', String(index)); row.classList.add('dragging'); };
    row.ondragend = () => { dragged = undefined; root.querySelectorAll('.drop-before, .drop-after, .dragging').forEach(e => e.classList.remove('drop-before', 'drop-after', 'dragging')); };
    row.ondragover = event => {
      if (dragged === undefined) return;
      event.preventDefault(); event.dataTransfer!.dropEffect = 'move';
      const after = event.clientY >= row.getBoundingClientRect().top + row.offsetHeight / 2;
      const marker = after ? 'drop-after' : 'drop-before';
      if (!row.classList.contains(marker)) {
        root.querySelectorAll('.drop-before, .drop-after').forEach(e => e.classList.remove('drop-before', 'drop-after'));
        row.classList.add(marker);
      }
    };
    row.ondrop = event => {
      event.preventDefault(); if (dragged === undefined) return;
      const after = event.clientY >= row.getBoundingClientRect().top + row.offsetHeight / 2;
      const insertion = index + (after ? 1 : 0); const target = insertion - (dragged < insertion ? 1 : 0);
      try { move(dragged, target); } catch (e) { alert((e as Error).message); }
    };
    const remove = action('×', () => apply(tree.filter((_, i) => i !== index), Math.min(index, tree.length - 2)));
    remove.setAttribute('aria-label', `Odebrat výskyt ${index + 1}: ${text}`);
    row.append(handle, remove);
    if (!('children' in node) && node.start !== undefined) row.append(action('Řádky', () => rowsDialog({ step: node, index })));
    if ('children' in node) row.append(element('small', 'Skupina z XML se přesouvá jako celek.'));
    list.append(row);
  });
  if (!tree.length) list.append(element('li', 'Začněte kliknutím na část vlevo.'));
  root.append(available, sequence); return root;
}

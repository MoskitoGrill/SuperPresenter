/** Ordered grammar matching desktop construct_parser; never expand before budgeting. */
export type Step = { section: string; start?: number; end?: number; pinned: boolean };
export type Group = { children: Node[]; repeat: number };
export type Node = Step | Group;
export function parseTree(guide: string, ids: string[]): Node[] {
  if (guide.length > 16384) throw new Error('Pořadí přesahuje 16384 znaků.');
  const text = guide.split(/\r\n|[\n\r\v\f\u001c-\u001e\u0085\u2028\u2029]/u).map(s => s.trim()).filter(Boolean).join(' ');
  let pos = 0;
  const frames: Node[][] = [[]];
  const spaces = () => { while (text[pos] === ' ') pos++; };
  const fail = (message: string): never => { throw new Error(`${message} (pozice ${pos + 1}).`); };
  const number = () => {
    spaces(); const start = pos;
    while (/[0-9]/.test(text[pos] ?? '') && pos < text.length) pos++;
    const n = Number(text.slice(start, pos));
    if (start === pos || !Number.isSafeInteger(n)) fail('Očekáváno bezpečné celé číslo');
    return n;
  };
  while (pos < text.length) {
    spaces(); if (pos === text.length) break;
    if (text[pos] === '(') {
      if (frames.length > 32) fail('Příliš hluboké skupiny (limit 32)');
      frames.push([]); pos++;
    } else if (text[pos] === ')') {
      if (frames.length === 1) fail('Přebývající uzavírací závorka');
      const children = frames.pop()!; pos++; spaces(); let repeat = 2;
      if (text[pos] === '*') { pos++; repeat = number(); }
      frames.at(-1)!.push({ children, repeat });
    } else {
      const pinned = text[pos] === '@'; if (pinned) { pos++; spaces(); }
      const start = pos;
      while (pos < text.length && !' .()'.includes(text[pos])) pos++;
      const section = text.slice(start, pos);
      if (!ids.includes(section)) fail(`Neznámá část „${section}“; názvy rozlišují velikost písmen`);
      const node: Step = { section, pinned }; spaces();
      if (text[pos] === '.') {
        pos++; node.start = number(); spaces();
        if (text[pos] === ':') { pos++; node.end = number(); if (node.end <= node.start) fail('Konec rozsahu musí být větší než začátek'); }
      }
      if (pinned && node.start === 0) fail('Připojení vyžaduje řádek od 1');
      frames.at(-1)!.push(node);
    }
  }
  if (frames.length !== 1) fail('Neuzavřená skupina');
  if (!frames[0].length) fail('Prázdné pořadí');
  budget(frames[0]); return frames[0];
}
export function budget(nodes: Node[], lengths?: Map<string, number>, copies = 1): number {
  let total = 0;
  for (const n of nodes) {
    const cost = 'children' in n ? Math.max(1, budget(n.children, lengths, copies)) * n.repeat
      : n.start !== undefined ? ((n.end ?? n.start) - n.start + 1) * copies : lengths?.get(n.section) ?? 1;
    total += Math.max(1, cost);
    if (total > 4096) throw new Error('Pořadí překračuje limit 4096 řádků/kroků.');
  }
  return total;
}
export function serializeTree(nodes: Node[]): string {
  return nodes.map(n => 'children' in n ? `(${serializeTree(n.children)})*${n.repeat}`
    : `${n.pinned ? '@' : ''}${n.section}${n.start === undefined ? '' : '.' + n.start + (n.end === undefined ? '' : ':' + n.end)}`).join(' ');
}
export function leaves(nodes: Node[]): Step[] { return nodes.flatMap(n => 'children' in n ? leaves(n.children) : [n]); }
export function removeReferences(nodes: Node[], id: string): Node[] {
  return nodes.flatMap<Node>(n => {
    if (!('children' in n)) return n.section === id ? [] : [n];
    const children = removeReferences(n.children, id); return children.length ? [{ ...n, children }] : [];
  });
}
export function risky(nodes: Node[]): boolean {
  return nodes.some(n => 'children' in n ? !n.repeat || !n.children.length || risky(n.children) : n.start === 0);
}

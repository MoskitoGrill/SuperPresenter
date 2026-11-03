/** First-stage subset. Never rewrite a construct we do not understand. */
export function parseSimple(guide: string, ids: string[]): string[] {
  if (guide.length > 16384) throw new Error('Pořadí přesahuje limit 16384 znaků.');
  const normalized = guide.split('\n').map(s => s.trim()).filter(Boolean).join(' ');
  const steps = normalized.split(' ').filter(Boolean);
  if (!steps.length || steps.length > 4096) throw new Error('Prázdné nebo příliš dlouhé pořadí.');
  for (const step of steps) {
    if (!ids.includes(step) || /[ .()@*:\s]/u.test(step)) {
      throw new Error(`Pořadí obsahuje nepodporovanou konstrukci nebo neznámou část „${step}“. Tento základ umí pouze posloupnost celých částí. Použijte desktopový editor; soubor nebyl změněn.`);
    }
  }
  return steps;
}

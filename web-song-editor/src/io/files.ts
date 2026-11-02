import { MAX_BYTES, importXml } from '../xml/songXml';
export async function openFile(file: File) {
  if (file.size > MAX_BYTES) throw new Error('Soubor je větší než 1 MiB.');
  let text: string;
  try { text = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer()); }
  catch { throw new Error('Soubor není platné UTF-8. Převeďte kopii do UTF-8.'); }
  return importXml(text);
}
export function download(text: string, title: string) {
  const url = URL.createObjectURL(new Blob([text], { type: 'application/xml;charset=utf-8' }));
  const a = document.createElement('a'); a.href = url;
  a.download = (title.replace(/[<>:"/\\|?*\x00-\x1f]/g, '_').trim() || 'pisen') + '.xml';
  a.click(); setTimeout(() => URL.revokeObjectURL(url), 10000);
}

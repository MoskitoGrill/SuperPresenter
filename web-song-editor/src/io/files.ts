import { MAX_BYTES, importXml } from '../xml/songXml';
import { DOCX_MAX_BYTES, readDocx } from './songDocx';
export async function openFile(file: File) {
  return importXml(await readUtf8(file));
}
export async function readUtf8(file: File) {
  if (file.size > MAX_BYTES) throw new Error('Soubor je větší než 1 MiB.');
  let text: string;
  try { text = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer()); }
  catch { throw new Error('Soubor není platné UTF-8. Převeďte kopii do UTF-8.'); }
  return text;
}
export async function openDocx(file: File) {
  if (!/\.docx$/i.test(file.name)) throw new Error('Vyberte Word dokument .docx. Starší .doc není podporován.');
  if (file.size > DOCX_MAX_BYTES) throw new Error('DOCX je větší než 5 MiB.');
  return readDocx(new Uint8Array(await file.arrayBuffer()));
}
export function download(text: string | Uint8Array, title: string, extension = 'xml') {
  const data = typeof text === 'string' ? text : new Uint8Array(text).buffer;
  const url = URL.createObjectURL(new Blob([data], { type: extension === 'docx' ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' : extension === 'txt' ? 'text/plain;charset=utf-8' : extension === 'json' ? 'application/json;charset=utf-8' : 'application/xml;charset=utf-8' }));
  const a = document.createElement('a'); a.href = url;
  a.download = (title.replace(/[<>:"/\\|?*\x00-\x1f]/g, '_').trim() || 'pisen') + '.' + extension;
  a.click(); setTimeout(() => URL.revokeObjectURL(url), 10000);
}

import { readdirSync, readFileSync, lstatSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = new URL('../dist/', import.meta.url);
const files = [];
function walk(dir, prefix = '') {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name), relative = prefix + name;
    if (lstatSync(path).isSymbolicLink()) throw Error(`Symlink: ${relative}`);
    if (lstatSync(path).isDirectory()) walk(path, relative + '/');
    else files.push(relative);
  }
}
walk(fileURLToPath(root));
if (!files.includes('index.html')) throw Error('Missing index.html');
for (const file of files) {
  if (file !== 'index.html' && !/^assets\/index-[\w-]+\.(js|css)$/.test(file)) throw Error(`Unexpected public file: ${file}`);
}
const html = readFileSync(new URL('index.html', root), 'utf8');
if (!html.includes('./assets/') || /(?:src|href)="\//.test(html)) throw Error('Non-relative asset URL');
console.log('Public artifact allowlist OK:', files.join(', '));

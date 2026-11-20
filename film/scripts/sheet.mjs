// CHARACTER SHEET RENDERER: node scripts/sheet.mjs <id>  ->  library/characters/<id>/sheet.png (+ .json boxes)
// Draws film/src/characters/<id>.ts (its exported `draw`) with its sheet.json through src/characters/sheetScene.ts.
import fs from 'node:fs';
import path from 'node:path';
import { FILM, bundleDraw, renderToPng } from './lib/page.mjs';

const id = process.argv[2];
if (!id || !/^[a-z0-9_]+$/.test(id)) { console.error('usage: node scripts/sheet.mjs <id>'); process.exit(2); }
const lib = path.join(FILM, '..', 'library', 'characters', id);
const sheet = JSON.parse(fs.readFileSync(path.join(lib, 'sheet.json'), 'utf8'));
// a tiny entry module: this character's draw() + the sheet layout
const entry = path.join(FILM, 'out', `sheet-entry-${id}.ts`);
fs.mkdirSync(path.dirname(entry), { recursive: true });
fs.writeFileSync(entry, `import { draw } from '../src/characters/${id}';\nimport { drawSheet } from '../src/characters/sheetScene';\n` +
  `export const sheetDraw = () => drawSheet(draw, ${JSON.stringify(sheet)});\n`);
try {
  const js = await bundleDraw(path.relative(FILM, entry), 'sheetDraw', 'f()');
  const { elements } = await renderToPng({ js, arg: 0, outPng: path.join(lib, 'sheet.png') });
  console.log(`${path.join(lib, 'sheet.png')}: ${elements.length} tagged elements`);
} finally { fs.rmSync(entry, { force: true }); }

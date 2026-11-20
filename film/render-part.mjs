// ============================================================================================================
// PART RENDERER: renders ONE frame range of a composition to an mp4 (used on GitHub runners, Kaggle and,
// for small smoke tests only, the laptop).
//   node render-part.mjs <composition> <fromFrame> <toFrame> <outDir>
// Writes  <outDir>/part-<from>-<to>.mp4   (h264, yuv420p, crf 18)
//         <outDir>/timing-<from>-<to>.json  {from, to, seconds, started, ended, concurrency, host}
// CONCURRENCY env = how many browser tabs render frames at once (default: number of CPU cores).
// ============================================================================================================
import { bundle } from '@remotion/bundler';
import { renderMedia, selectComposition } from '@remotion/renderer';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const [comp, fromS, toS, outDir = path.join(here, 'out')] = process.argv.slice(2);
if (!comp || fromS === undefined || toS === undefined) {
  console.error('usage: node render-part.mjs <composition> <from> <to> <outDir>');
  process.exit(2);
}
const from = Number(fromS), to = Number(toS);
const concurrency = Number(process.env.CONCURRENCY || os.cpus().length);
fs.mkdirSync(outDir, { recursive: true });

const started = Date.now() / 1000;
// 1. bundle the React project once (webpack) so headless Chrome can load it
const serveUrl = await bundle({ entryPoint: path.join(here, 'src', 'index.ts'), publicDir: path.join(here, 'public') });
// 2. look up the composition (size, fps, length)
const composition = await selectComposition({ serveUrl, id: comp });
// 3. render just our frame range
const outFile = path.join(outDir, `part-${from}-${to}.mp4`);
let lastPct = -10;
await renderMedia({
  composition, serveUrl, codec: 'h264', crf: 18, pixelFormat: 'yuv420p', imageFormat: 'jpeg', jpegQuality: 95,
  frameRange: [from, to], outputLocation: outFile, concurrency,
  onProgress: ({ progress }) => {                                    // a line every 10% so logs show it's alive
    const pct = Math.floor(progress * 100);
    if (pct >= lastPct + 10) { lastPct = pct; console.log(`[${comp} ${from}-${to}] ${pct}%`); }
  },
});
const ended = Date.now() / 1000;
const timing = { from, to, seconds: ended - started, started, ended, concurrency, host: os.hostname() };
fs.writeFileSync(path.join(outDir, `timing-${from}-${to}.json`), JSON.stringify(timing));
console.log(`done ${outFile} in ${timing.seconds.toFixed(1)} s`);

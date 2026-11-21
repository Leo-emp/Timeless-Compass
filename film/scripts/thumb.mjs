// THUMBNAIL: render one variant of a job's freshly drawn thumbnail (spec 6.9) to a png.
//   node scripts/thumb.mjs <slug> <a|b> <out.png>
// The job module film/src/jobs/<slug>/thumb.ts exports:
//   THUMB_SIZE = { w, h }            1280x720 for long videos, 1080x1920 for Shorts
//   WORDS = { a: [...], b: [...] }   the words each variant draws (the checker counts THESE; max 3)
//   THUMBS = { a: () => svg, b: () => svg }
// Last stdout line = JSON {"words": [...], "w": .., "h": ..} for `tc thumb`.
import fs from 'node:fs';
import path from 'node:path';
import { FILM, bundleDraw, renderToPng } from './lib/page.mjs';

const [slug, variant, outPng] = process.argv.slice(2);
if (!slug || !/^[a-z0-9_]+$/.test(slug) || !['a', 'b'].includes(variant) || !outPng) {
  console.error('usage: node scripts/thumb.mjs <slug> <a|b> <out.png>');
  process.exit(2);
}
const entry = path.join(FILM, 'out', `thumb-${slug}-${process.pid}.ts`);
fs.mkdirSync(path.dirname(entry), { recursive: true });
// one bundle exposes the drawing (as __draw) and the size + words (as a JSON string the page hands back)
fs.writeFileSync(entry, `import { THUMBS, THUMB_SIZE, WORDS } from '../src/jobs/${slug}/thumb';\n` +
  `export const draw = (v: string) => THUMBS[v as 'a' | 'b']();\n` +
  `export const meta = (v: string) => JSON.stringify({ words: WORDS[v as 'a' | 'b'], w: THUMB_SIZE.w, h: THUMB_SIZE.h });\n`);
try {
  // read size + words first (a tiny Node-side eval of the same bundle), then render at that size
  const metaJs = await bundleDraw(path.relative(FILM, entry), 'meta', 'f(t)');
  const win = {};
  new Function('window', metaJs)(win);
  const info = JSON.parse(win.__draw(variant));
  const js = await bundleDraw(path.relative(FILM, entry), 'draw', 'f(t)');
  await renderToPng({ js, arg: variant, outPng, W: info.w, H: info.h });
  console.log(JSON.stringify(info));
} finally { fs.rmSync(entry, { force: true }); }

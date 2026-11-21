// JOB STILL: render one frame of a job's film (plan + fresh scenes) to a png + element boxes, for the still gate.
//   node scripts/jobstill.mjs <slug> <frame> <out.png>
import fs from 'node:fs';
import path from 'node:path';
import { FILM, bundleDraw, renderToPng } from './lib/page.mjs';

const [slug, frameS, outPng] = process.argv.slice(2);
if (!slug || !/^[a-z0-9_]+$/.test(slug) || frameS === undefined || !outPng) { console.error('usage: node scripts/jobstill.mjs <slug> <frame> <out.png>'); process.exit(2); }
const entry = path.join(FILM, 'out', `jobstill-${slug}.ts`);
fs.mkdirSync(path.dirname(entry), { recursive: true });
fs.writeFileSync(entry, `import plan from '../src/jobs/${slug}/plan.json';\nimport { SCENES } from '../src/jobs/${slug}/scenes';\n` +
  `import { frameAt } from '../src/film/sequence';\nexport const draw = (f: number) => frameAt(f, plan as any, SCENES);\n`);
try {
  const js = await bundleDraw(path.relative(FILM, entry), 'draw', 'f(t)');
  const plan = JSON.parse(fs.readFileSync(path.join(FILM, 'src', 'jobs', slug, 'plan.json'), 'utf8'));
  // the still is the job's own frame size (1920x1080 long, 1080x1920 Shorts)
  const { elements } = await renderToPng({ js, arg: Number(frameS), outPng, W: plan.width ?? 1920, H: plan.height ?? 1080 });
  console.log(`${outPng}: ${elements.length} tagged elements`);
} finally { fs.rmSync(entry, { force: true }); }

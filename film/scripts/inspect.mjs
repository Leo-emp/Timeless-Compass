// ============================================================================================================
// SCENE INSPECTOR: render ONE moment of a scene to a still AND read the on-screen box of every tagged element
// (data-role = face / hand / prop / text / textbox / fg, and character parts data-char/data-part/data-fill), so
// `python -m tc still` can check geometry and character colours exactly as the viewer sees them.
//   node scripts/inspect.mjs <module.ts> <exportName> <t seconds> <out.png> [--w 1920] [--h 1080]
// Writes out.png and out.json = {"w","h","arg","elements":[{"role","id","holds","grip","acting","char","part","fill","box","order"}]}
// Laptop-only tool (the self-check runs on the laptop, spec 6.6). Drawing code: scripts/lib/page.mjs.
// ============================================================================================================
import { bundleDraw, renderToPng } from './lib/page.mjs';

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const [mod, exportName, tS, outPng] = args;
if (!mod || !exportName || tS === undefined || !outPng) {
  console.error('usage: node scripts/inspect.mjs <module.ts> <exportName> <t> <out.png> [--w 1920 --h 1080]');
  process.exit(2);
}
const js = await bundleDraw(mod, exportName, 'f(t)');
const { elements } = await renderToPng({ js, arg: Number(tS), W: Number(opt('--w', 1920)), H: Number(opt('--h', 1080)), outPng });
console.log(`${outPng}: ${elements.length} tagged elements`);

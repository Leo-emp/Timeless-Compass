// ============================================================================================================
// SHARED PAGE RENDERER for the laptop tools (inspector, character sheets): bundle a TypeScript export with esbuild,
// draw it in headless Edge/Chrome, read every tagged element's on-screen box (+ grip, character part colours) and
// save a screenshot. Used by scripts/inspect.mjs and scripts/sheet.mjs.
// ============================================================================================================
import { build } from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const here = path.dirname(fileURLToPath(import.meta.url));
export const FILM = path.join(here, '..', '..');

/** Bundle `import { <exportName> as f } from <module>` into a browser script that sets window.__draw = f. */
export async function bundleDraw(modulePath, exportName, wrap = 'f') {
  const entry = path.resolve(FILM, modulePath).split(path.sep).join('/');
  const res = await build({
    stdin: { contents: `import { ${exportName} as f } from ${JSON.stringify(entry)}; window.__draw = (t) => ${wrap};`, resolveDir: FILM, loader: 'ts' },
    bundle: true, write: false, format: 'iife', platform: 'browser',
  });
  return res.outputFiles[0].text;
}

/** Draw window.__draw(arg) at W x H, return {elements}, save outPng (+ .json next to it). */
export async function renderToPng({ js, arg, W = 1920, H = 1080, outPng }) {
  // 2. a page with the bundled fonts and an empty svg
  const fontUrl = 'file:///' + path.join(FILM, 'public', 'fonts', 'Cinzel.ttf').split(path.sep).join('/');
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
  @font-face { font-family: 'Cinzel'; src: url('${fontUrl}'); font-weight: 400 900; }
  html,body{margin:0;background:#000} svg{display:block}</style></head><body>
  <svg id="s" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg"></svg></body></html>`;
  const tmpHtml = path.join(FILM, 'out', `page-${process.pid}.html`);
  fs.mkdirSync(path.dirname(tmpHtml), { recursive: true });
  fs.writeFileSync(tmpHtml, html);
  
  const exe = process.env.PUPPETEER_EXECUTABLE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
  const browser = await puppeteer.launch({ executablePath: exe, headless: true, args: ['--allow-file-access-from-files'] });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: W, height: H });
    await page.goto('file:///' + tmpHtml.split(path.sep).join('/'));
    await page.addScriptTag({ content: js });
    await page.evaluate(async (arg) => {
      document.getElementById('s').innerHTML = window.__draw(arg);
      await document.fonts.load('700 27px Cinzel');   // the card must be measured in its real font
      await document.fonts.ready;
    }, arg);
    // 3. screen boxes of every tagged element, in document order (later = drawn on top)
    const elements = await page.evaluate(() => {
      const out = [];
      document.querySelectorAll('[data-role], [data-char]').forEach((el, order) => {
        const r = el.getBoundingClientRect();                 // screen box after all transforms
        out.push({ role: el.getAttribute('data-role'), id: el.getAttribute('data-id'), holds: el.getAttribute('data-holds'), acting: el.getAttribute('data-acting'),
                   char: el.getAttribute('data-char'), part: el.getAttribute('data-part'), fill: el.getAttribute('data-fill'),
                   box: [r.x, r.y, r.width, r.height], order });
      });
      // grip: does the hand really sit ON the prop's shape (stroke or fill), not just inside its bounding box?
      // Test the hand centre and 8 points around it (within the fist) against every shape of the held prop.
      const svg = document.getElementById('s');
      out.forEach((e, i) => {
        if (e.role !== 'hand' || !e.holds) return;
        const prop = document.querySelector(`[data-role="prop"][data-id="${e.holds}"]`);
        if (!prop) return;
        const [x, y, w, h] = e.box, cx = x + w / 2, cy = y + h / 2, r = Math.min(w, h) * 0.4;
        const shapes = prop.querySelectorAll('path, line, circle, ellipse, rect, polygon, polyline');
        let hit = false;
        for (let k = 0; k <= 8 && !hit; k++) {
          const a = (k / 8) * Math.PI * 2, px = cx + (k ? r * Math.cos(a) : 0), py = cy + (k ? r * Math.sin(a) : 0);
          for (const sh of shapes) {
            const m = sh.getScreenCTM(); if (!m) continue;
            const pt = svg.createSVGPoint(); pt.x = px; pt.y = py;
            const local = pt.matrixTransform(m.inverse());               // screen point -> the shape's own units
            if (sh.isPointInStroke(local) || sh.isPointInFill(local)) { hit = true; break; }
          }
        }
        out[i].grip = hit;
      });
      return out;
    });
    await page.screenshot({ path: outPng });
    fs.writeFileSync(outPng.replace(/\.png$/i, '.json'), JSON.stringify({ w: W, h: H, arg, elements }, null, 1));
    return { elements };
  } finally {
    await browser.close();
    fs.rmSync(tmpHtml, { force: true });
  }
}

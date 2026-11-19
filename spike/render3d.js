// Spike renderer for WebGL pages (throwaway): waits for window.ready, calls window.draw(t) per frame,
// screenshots, joins frames into an mp4 with ffmpeg.
// Usage: node render3d.js test3d.html 8 24 [stillTime]
//   with stillTime: renders only that one moment to <page>_<t>.png (quick check)
const path = require('path'), fs = require('fs'), { execFileSync } = require('child_process');
const puppeteer = require('C:/Users/User/jobpilot-marketing/node_modules/puppeteer-core');
const [, , page = 'test3d.html', secs = '8', fps = '24', still] = process.argv;

(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: 'new',
    args: ['--allow-file-access-from-files', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--use-angle=default'],
  });
  const tab = await browser.newPage();
  tab.on('console', m => console.log('page:', m.text()));
  tab.on('pageerror', e => console.log('page error:', e.message));
  await tab.setViewport({ width: 1920, height: 1080 });
  await tab.goto('file:///' + path.join(__dirname, page).replace(/\\/g, '/'));
  await tab.waitForFunction('window.ready === true', { timeout: 180000 });
  if (still !== undefined) {
    for (const t of still.split(',')) { await tab.evaluate(t => window.draw(t), +t);
      await tab.screenshot({ path: path.join(__dirname, `${page.replace('.html', '')}_${t}.png`) }); console.log('still', t); }
    return browser.close();
  }
  const dir = path.join(__dirname, 'frames3d'); fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir);
  const N = Math.round(+secs * +fps), t0 = Date.now();
  for (let i = 0; i < N; i++) {
    await tab.evaluate(t => window.draw(t), i / +fps);
    await tab.screenshot({ path: path.join(dir, `f${String(i).padStart(4, '0')}.png`) });
    if (i % 24 === 0) console.log(`frame ${i}/${N}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  await browser.close();
  const out = path.join(__dirname, page.replace('.html', '.mp4'));
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', fps, '-i', path.join(dir, 'f%04d.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', out]);
  console.log('done ->', out);
})();

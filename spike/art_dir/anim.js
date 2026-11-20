// Render an animated scene page to mp4: calls window.draw(t) per frame in headless Edge, screenshots, ffmpeg joins.
// Usage: node anim.js scene.html out.mp4 seconds fps
const path = require('path'), fs = require('fs'), { execFileSync } = require('child_process');
const puppeteer = require('C:/Users/User/jobpilot-marketing/node_modules/puppeteer-core');
const [, , page, out, secs = '8', fps = '24'] = process.argv;
const N = Math.round(+secs * +fps), dir = path.join(__dirname, 'frames_' + path.basename(page, '.html'));
fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir);
(async () => {
  const b = await puppeteer.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: 'new', args: ['--allow-file-access-from-files'] });
  const tab = await b.newPage(); await tab.setViewport({ width: 1920, height: 1080 });
  await tab.goto('file:///' + path.resolve(page).split(path.sep).join('/'), { waitUntil: 'networkidle0' });
  for (let i = 0; i < N; i++) {
    await tab.evaluate(t => window.draw(t), i / +fps);                 // redraw the whole scene at time t
    await tab.screenshot({ path: path.join(dir, `f${String(i).padStart(4, '0')}.png`) });
    if (i % 48 === 0) console.log(`frame ${i}/${N}`);
  }
  await b.close();
  execFileSync('ffmpeg', ['-y', '-v', 'error', '-framerate', fps, '-i', path.join(dir, 'f%04d.png'), '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', out]);
  console.log('done', out);
})();

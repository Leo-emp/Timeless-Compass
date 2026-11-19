// Spike renderer (throwaway): opens an animated scene page in headless Edge,
// calls window.draw(t) for every frame, screenshots it, then ffmpeg joins the frames into an mp4.
// Usage: node render_anim.js anim_test.html 5 24
const path = require('path');
const fs = require('fs');
const { execFileSync } = require('child_process');
// borrow puppeteer-core already installed in another project on this machine (spike only)
const puppeteer = require('C:/Users/User/jobpilot-marketing/node_modules/puppeteer-core');

const [, , page = 'anim_test.html', secs = '5', fps = '24'] = process.argv;
const N = Math.round(+secs * +fps);
const dir = path.join(__dirname, 'frames');
fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir);

(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    headless: 'new', args: ['--allow-file-access-from-files', '--disable-gpu'],
  });
  const tab = await browser.newPage();
  await tab.setViewport({ width: 1080, height: 1920 });
  await tab.goto('file:///' + path.join(__dirname, page).replace(/\\/g, '/'), { waitUntil: 'networkidle0' });
  await tab.evaluate(() => document.fonts.ready);                    // titles need the fonts loaded
  for (let i = 0; i < N; i++) {
    await tab.evaluate(t => window.draw(t), i / +fps);                // redraw the scene at this moment
    await tab.screenshot({ path: path.join(dir, `f${String(i).padStart(4, '0')}.png`) });
    if (i % 24 === 0) console.log(`frame ${i}/${N}`);
  }
  await browser.close();
  const outFile = path.join(__dirname, page.replace('.html', '.mp4'));
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', fps, '-i', path.join(dir, 'f%04d.png'),
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', outFile]);
  console.log('done ->', outFile);
})();

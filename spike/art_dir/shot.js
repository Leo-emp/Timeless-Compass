// Screenshot one HTML page to PNG with headless Edge (spike helper).
// Usage: node shot.js page.html out.png 1920 1080
const path = require('path');
const puppeteer = require('C:/Users/User/jobpilot-marketing/node_modules/puppeteer-core');
const [, , page, out, w = '1920', h = '1080'] = process.argv;
(async () => {
  const b = await puppeteer.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: 'new', args: ['--allow-file-access-from-files'] });
  const t = await b.newPage();
  await t.setViewport({ width: +w, height: +h });
  await t.goto('file:///' + path.resolve(page).split(path.sep).join('/'), { waitUntil: 'networkidle0' });
  await t.screenshot({ path: out });
  await b.close();
})();

const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const args = process.argv.slice(2);
  const get = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
  const times = (get('times', '') || '').split(',').filter(Boolean).map(Number);
  const from = +get('from', 0), to = +get('to', -1), step = +get('step', 1);
  const fps = +get('fps', 30), W = +get('w', 1920), out = get('out', '/tmp/frames');
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox', '--disable-dev-shm-usage'] });
  const p = await b.newPage({ viewport: { width: W, height: Math.round(W * 9 / 16) }, deviceScaleFactor: 1 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto(`http://localhost:8731/index.html?w=${W}`, { waitUntil: 'load' });
  await p.waitForFunction('window.__ready === true', { timeout: 60000 });
  if (errs.length) { console.log('PAGE ERRORS:', errs.slice(0, 4)); await b.close(); process.exit(1); }
  const t0 = Date.now();
  if (times.length) {
    for (const t of times) {
      await p.evaluate(tt => window.renderAt(tt), t);
      await p.screenshot({ path: `${out}/t_${String(Math.round(t * 100)).padStart(5, '0')}.png` });
    }
  } else {
    for (let f = from; f <= to; f += step) {
      const file = `${out}/f_${String(f).padStart(5, '0')}.png`;
      if (fs.existsSync(file) && fs.statSync(file).size > 3000) continue;
      await p.evaluate(tt => window.renderAt(tt), f / fps);
      await p.screenshot({ path: file });
      if ((f - from) % 30 === 0) console.log('frame', f, ((Date.now() - t0) / 1000).toFixed(1) + 's');
    }
  }
  console.log('done', ((Date.now() - t0) / 1000).toFixed(1) + 's', 'errors:', errs.length ? errs.slice(0, 3) : 'none');
  await b.close();
})();

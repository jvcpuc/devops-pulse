import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';

const EV = path.resolve('evidence');
const projRoot = path.resolve('.');

async function shot(page, file, url, opts = {}) {
  console.log('->', file, url);
  await page.goto(url, { waitUntil: opts.waitUntil || 'networkidle', timeout: opts.timeout || 60000 });
  if (opts.wait) await page.waitForTimeout(opts.wait);
  if (opts.before) await opts.before(page);
  await page.screenshot({ path: path.join(EV, file), fullPage: opts.fullPage !== false });
  console.log('   saved', file);
}

(async () => {
  fs.mkdirSync(EV, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();

  // 01 - API health
  await shot(page, '01-api-health.png', 'http://127.0.0.1:8000/health', { fullPage: false });

  // 01b - API pulse JSON
  await shot(page, '01-api.png', 'http://127.0.0.1:8000/api/pulse?hours=24', { wait: 1500 });

  // 10 - Dashboard (local file)
  const dash = 'file:///' + path.join(projRoot, 'dashboard', 'index.html').replace(/\\/g, '/');
  await shot(page, '10-dashboard.png', dash, { wait: 2500, timeout: 90000 });

  // n8n
  await shot(page, '03-n8n-etapa1.png', 'http://127.0.0.1:5678', { wait: 3000, timeout: 90000, fullPage: false });

  // Evolution Manager
  await shot(page, '07-evolution-manager.png', 'http://127.0.0.1:8080', { wait: 3000, fullPage: false });

  // 13 - GitHub public repo (commits / actions overview)
  await shot(page, '13-github.png', 'https://github.com/n8n-io/n8n', { wait: 4000, timeout: 90000, fullPage: false });
  await shot(page, '13-github-actions.png', 'https://github.com/n8n-io/n8n/actions', { wait: 4000, timeout: 90000, fullPage: false });
  await shot(page, '13-github-pulls.png', 'https://github.com/n8n-io/n8n/pulls', { wait: 4000, timeout: 90000, fullPage: false });

  // 04 - Ollama tags JSON
  await shot(page, '04-ollama.png', 'http://127.0.0.1:11434/api/tags', { wait: 1000 });

  await browser.close();
  console.log('done');
})().catch((e) => {
  console.error(e);
  process.exit(1);
});

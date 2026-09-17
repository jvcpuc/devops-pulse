import { chromium } from 'playwright';
import path from 'path';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await page.goto('http://127.0.0.1:8000/dashboard/sqlite.html', { waitUntil: 'networkidle', timeout: 30000 }).catch(async () => {
    // fallback file URL if static server not available
    await page.goto('file:///' + path.resolve('dashboard/sqlite.html').replace(/\\/g, '/'), { waitUntil: 'networkidle', timeout: 30000 });
  });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join('evidence', '06b-sqlite-grid.png'), fullPage: true });
  console.log('saved evidence/06b-sqlite-grid.png');
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });

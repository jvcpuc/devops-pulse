const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  // Try owner email from DB dump first via env
  const email = process.env.N8N_EMAIL || 'admin@example.com';
  const pass = process.env.N8N_PASS || '';

  await page.goto('http://127.0.0.1:5678/signin', { waitUntil: 'networkidle', timeout: 60000 });
  await page.screenshot({ path: path.join('evidence', '03-n8n-signin.png') });

  if (pass) {
    await page.fill('input[type="email"], input[name="email"]', email);
    await page.fill('input[type="password"], input[name="password"]', pass);
    await page.click('button[type="submit"]');
    await page.waitForTimeout(4000);
    await page.screenshot({ path: path.join('evidence', '03-n8n-after-login.png'), fullPage: false });

    // open etapa 1 workflow search
    await page.goto('http://127.0.0.1:5678/workflow/wOLIY6YnqeEo8asC', { waitUntil: 'networkidle', timeout: 90000 }).catch(()=>{});
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join('evidence', '03-n8n-etapa1.png'), fullPage: false });

    await page.goto('http://127.0.0.1:5678/workflow/81YWZzdYxP7upBL2', { waitUntil: 'networkidle', timeout: 90000 }).catch(()=>{});
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join('evidence', '07-n8n-etapa2.png'), fullPage: false });
  }

  await browser.close();
  console.log('done');
})();

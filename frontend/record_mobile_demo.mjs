import { chromium, devices } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const outDir = path.resolve('./demo-output');
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  ...devices['iPhone 14 Pro'],
  locale: 'zh-CN',
  timezoneId: 'Asia/Shanghai',
  recordVideo: {
    dir: outDir,
    size: { width: 393, height: 852 }
  }
});

const page = await context.newPage();

await page.route('**/v3/chat', async (route) => {
  await new Promise((r) => setTimeout(r, 900));
  const payload = {
    data: {
      messages: [
        {
          type: 'answer',
          content:
            'AIRON：建议你将预算向高意向搜索和短视频倾斜 18%，并启动分层召回提升复购。'
        }
      ]
    }
  };

  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(payload)
  });
});

await page.goto('http://127.0.0.1:8091/?demo=1', { waitUntil: 'networkidle' });
await page.waitForTimeout(16500);

await context.close();
await browser.close();

const videos = fs
  .readdirSync(outDir)
  .filter((file) => file.endsWith('.webm'))
  .map((file) => ({
    file,
    mtime: fs.statSync(path.join(outDir, file)).mtimeMs
  }))
  .sort((a, b) => b.mtime - a.mtime);

if (!videos.length) {
  throw new Error('No recorded video found.');
}

const src = path.join(outDir, videos[0].file);
const dst = path.join(outDir, 'mobile-keynote.webm');
if (src !== dst) {
  fs.copyFileSync(src, dst);
}

console.log(dst);

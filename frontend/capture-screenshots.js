import { chromium } from '@playwright/test';
import { existsSync, mkdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { installSyntheticApi, installSyntheticSession } from './synthetic-screenshot-fixtures.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const BASE_URL = 'https://127.0.0.1:5173';
const SCREENSHOT_DIR = join(__dirname, '..', 'docs', 'screenshots');
const VIEWPORT = { width: 1920, height: 1080 };

const pages = [
  { path: '/', filename: '01-dashboard.png', description: 'Synthetic dashboard' },
  { path: '/register', filename: '02-face-registration.png', description: 'Synthetic face registration' },
  { path: '/faces', filename: '03-face-list.png', description: 'Synthetic face list' },
];

async function captureScreenshots() {
  if (process.env.FACERECO_SYNTHETIC_DOCS !== '1') {
    console.error('Refusing screenshot capture: set FACERECO_SYNTHETIC_DOCS=1 to use synthetic data only.');
    process.exitCode = 1;
    return;
  }

  if (!existsSync(SCREENSHOT_DIR)) mkdirSync(SCREENSHOT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({
      viewport: VIEWPORT,
      deviceScaleFactor: 1,
      ignoreHTTPSErrors: true,
    });
    const page = await context.newPage();
    await installSyntheticSession(page, 'ko');
    await installSyntheticApi(page);

    for (const pageConfig of pages) {
      console.log(`Capturing ${pageConfig.description}`);
      await page.goto(`${BASE_URL}${pageConfig.path}`, { waitUntil: 'networkidle' });
      await page.screenshot({
        path: join(SCREENSHOT_DIR, pageConfig.filename),
        fullPage: false,
      });
    }

    await context.close();
    console.log('Synthetic screenshots captured successfully.');
  } finally {
    await browser.close();
  }
}

captureScreenshots().catch(() => {
  console.error('Synthetic screenshot capture failed.');
  process.exitCode = 1;
});

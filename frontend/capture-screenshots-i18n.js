import { chromium } from '@playwright/test';
import { existsSync, mkdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { installSyntheticApi, installSyntheticSession } from './synthetic-screenshot-fixtures.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const BASE_URL = 'https://127.0.0.1:5173';
const SCREENSHOTS_DIR = join(__dirname, '..', 'docs', 'screenshots');
const VIEWPORT = { width: 1920, height: 1080 };

const languages = [
  { code: 'en', locale: 'en-US', dir: 'en' },
  { code: 'ko', locale: 'ko-KR', dir: 'kr' },
];

const pages = [
  { path: '/', filename: '01-dashboard.png' },
  { path: '/register', filename: '02-face-registration.png' },
  { path: '/faces', filename: '03-face-list.png' },
];

async function captureScreenshots() {
  if (process.env.FACERECO_SYNTHETIC_DOCS !== '1') {
    console.error('Refusing screenshot capture: set FACERECO_SYNTHETIC_DOCS=1 to use synthetic data only.');
    process.exitCode = 1;
    return;
  }

  const browser = await chromium.launch({ headless: true });
  try {
    for (const language of languages) {
      const languageDir = join(SCREENSHOTS_DIR, language.dir);
      if (!existsSync(languageDir)) mkdirSync(languageDir, { recursive: true });

      const context = await browser.newContext({
        viewport: VIEWPORT,
        deviceScaleFactor: 1,
        locale: language.locale,
        ignoreHTTPSErrors: true,
      });
      const page = await context.newPage();
      await installSyntheticSession(page, language.code);
      await installSyntheticApi(page);

      for (const pageConfig of pages) {
        await page.goto(`${BASE_URL}${pageConfig.path}`, { waitUntil: 'networkidle' });
        await page.screenshot({
          path: join(languageDir, pageConfig.filename),
          fullPage: false,
        });
      }

      await context.close();
      console.log(`Synthetic ${language.code} screenshots captured.`);
    }
  } finally {
    await browser.close();
  }
}

captureScreenshots().catch(() => {
  console.error('Synthetic i18n screenshot capture failed.');
  process.exitCode = 1;
});

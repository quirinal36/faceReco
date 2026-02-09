/**
 * Playwright Screenshot Capture Script with i18n Support
 *
 * This script captures screenshots of all pages in both English and Korean
 * for documentation purposes.
 */

import { chromium } from '@playwright/test';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync, mkdirSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Configuration
const BASE_URL = 'http://localhost:5173';
const SCREENSHOTS_DIR = join(__dirname, '..', 'docs', 'screenshots');
const VIEWPORT = { width: 1920, height: 1080 };

// Language configurations
const languages = [
  {
    code: 'en',
    name: 'English',
    dir: 'en',
    localStorage: { 'i18nextLng': 'en' }
  },
  {
    code: 'kr',
    name: 'Korean',
    dir: 'kr',
    localStorage: { 'i18nextLng': 'kr' }
  }
];

// Page configurations
const pages = [
  {
    name: 'dashboard',
    path: '/',
    filename: '01-dashboard.png',
    description: 'Dashboard - Real-time face monitoring'
  },
  {
    name: 'face-registration',
    path: '/face-registration',
    filename: '02-face-registration.png',
    description: 'Face Registration - Add new faces'
  },
  {
    name: 'face-list',
    path: '/face-list',
    filename: '03-face-list.png',
    description: 'Face List - Manage registered faces'
  }
];

async function captureScreenshots() {
  console.log('🚀 Starting i18n screenshot capture...\n');

  // Launch browser
  const browser = await chromium.launch({ headless: true });

  try {
    for (const language of languages) {
      console.log(`\n📸 Capturing screenshots for: ${language.name} (${language.code})`);
      console.log('='.repeat(60));

      // Create language-specific directory
      const langDir = join(SCREENSHOTS_DIR, language.dir);
      if (!existsSync(langDir)) {
        mkdirSync(langDir, { recursive: true });
        console.log(`📁 Created directory: ${langDir}`);
      }

      // Create context with language set
      const context = await browser.newContext({
        viewport: VIEWPORT,
        deviceScaleFactor: 1,
        locale: language.code === 'kr' ? 'ko-KR' : 'en-US'
      });

      const page = await context.newPage();

      // Set localStorage for i18next
      await page.goto(BASE_URL);
      await page.evaluate((storage) => {
        for (const [key, value] of Object.entries(storage)) {
          localStorage.setItem(key, value);
        }
      }, language.localStorage);

      // Capture screenshots for each page
      for (const pageConfig of pages) {
        const url = `${BASE_URL}${pageConfig.path}`;
        console.log(`\n   📷 ${pageConfig.description}`);
        console.log(`      URL: ${url}`);

        await page.goto(url, { waitUntil: 'networkidle' });

        // Wait for content to load and language to be applied
        await page.waitForTimeout(2000);

        const screenshotPath = join(langDir, pageConfig.filename);
        await page.screenshot({
          path: screenshotPath,
          fullPage: false
        });

        console.log(`      ✅ Saved: ${language.dir}/${pageConfig.filename}`);
      }

      await context.close();
      console.log(`\n✨ Completed ${language.name} screenshots!`);
    }

    console.log('\n' + '='.repeat(60));
    console.log('✨ All screenshots captured successfully!');
    console.log(`📂 Screenshots saved in:`);
    for (const language of languages) {
      console.log(`   - ${join(SCREENSHOTS_DIR, language.dir)}`);
    }

  } catch (error) {
    console.error('\n❌ Error capturing screenshots:', error.message);
    throw error;
  } finally {
    await browser.close();
  }
}

// Run the script
captureScreenshots()
  .then(() => {
    console.log('\n🎉 Screenshot capture completed!');
    process.exit(0);
  })
  .catch((error) => {
    console.error('\n💥 Failed to capture screenshots:', error);
    process.exit(1);
  });

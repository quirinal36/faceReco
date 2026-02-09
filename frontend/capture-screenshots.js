/**
 * Playwright Screenshot Capture Script
 *
 * This script captures screenshots of all pages in the Face Recognition System
 * frontend application for documentation purposes.
 */

import { chromium } from '@playwright/test';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync, mkdirSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Configuration
const BASE_URL = 'http://localhost:5173';
const SCREENSHOT_DIR = join(__dirname, '..', 'docs', 'screenshots');
const VIEWPORT = { width: 1920, height: 1080 };

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
  console.log('🚀 Starting screenshot capture...');

  // Create screenshot directory if it doesn't exist
  if (!existsSync(SCREENSHOT_DIR)) {
    mkdirSync(SCREENSHOT_DIR, { recursive: true });
    console.log(`📁 Created directory: ${SCREENSHOT_DIR}`);
  }

  // Launch browser
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 1
  });
  const page = await context.newPage();

  console.log(`🌐 Connecting to: ${BASE_URL}`);

  try {
    // Capture screenshots for each page
    for (const pageConfig of pages) {
      const url = `${BASE_URL}${pageConfig.path}`;
      console.log(`\n📸 Capturing: ${pageConfig.description}`);
      console.log(`   URL: ${url}`);

      await page.goto(url, { waitUntil: 'networkidle' });

      // Wait a bit for any animations or dynamic content
      await page.waitForTimeout(2000);

      const screenshotPath = join(SCREENSHOT_DIR, pageConfig.filename);
      await page.screenshot({
        path: screenshotPath,
        fullPage: false
      });

      console.log(`   ✅ Saved: ${pageConfig.filename}`);
    }

    console.log('\n✨ All screenshots captured successfully!');
    console.log(`📂 Screenshots saved in: ${SCREENSHOT_DIR}`);

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

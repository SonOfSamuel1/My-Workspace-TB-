#!/usr/bin/env node

/**
 * Cloudflare Pages Settings Verification Script
 * Purpose: Verify and update compatibility settings for Cloudflare Pages
 * Created: 2025-12-03
 */

const { chromium } = require('playwright');
const fs = require('fs').promises;

const CONFIG = {
  cdpEndpoint: 'http://127.0.0.1:9222',
  outputDir: './cloudflare-automation-output',
  targetUrl: 'https://dash.cloudflare.com/b88c78c7542c29614c07bfe30e204759/pages/view/ynab-transaction-reviewer/settings/functions',
  settings: {
    compatibilityDate: '2024-01-01',
    compatibilityFlags: 'nodejs_compat'
  }
};

async function captureScreenshot(page, name) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
  const filename = `${CONFIG.outputDir}/${timestamp}-${name}.png`;
  await fs.mkdir(CONFIG.outputDir, { recursive: true });
  await page.screenshot({ path: filename, fullPage: true });
  console.log(`  Screenshot: ${filename}`);
  return filename;
}

async function verifyCloudflareSettings() {
  let browser = null;
  let page = null;

  try {
    console.log('Connecting to Chrome via CDP...\n');
    browser = await chromium.connectOverCDP(CONFIG.cdpEndpoint);
    const defaultContext = browser.contexts()[0];
    page = defaultContext.pages()[0] || await defaultContext.newPage();

    console.log('Navigating to Functions settings...');
    await page.goto(CONFIG.targetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(2000);

    await captureScreenshot(page, '01-initial-page');

    // Close any open modals
    console.log('\nClosing any open modals...');
    try {
      const closeButton = page.locator('button:has-text("Cancel"), button[aria-label="Close"]').first();
      if (await closeButton.isVisible({ timeout: 2000 })) {
        await closeButton.click();
        await page.waitForTimeout(500);
      }
    } catch (e) {
      // No modal to close
    }

    // Click on Runtime in the left sidebar
    console.log('Clicking on Runtime section...');
    const runtimeSelectors = [
      'text=Runtime',
      'a:has-text("Runtime")',
      'button:has-text("Runtime")',
      '[data-testid="runtime-section"]'
    ];

    let clicked = false;
    for (const selector of runtimeSelectors) {
      try {
        const element = page.locator(selector).first();
        if (await element.isVisible({ timeout: 2000 })) {
          await element.click();
          clicked = true;
          console.log('  Clicked Runtime section');
          break;
        }
      } catch (e) {
        continue;
      }
    }

    await page.waitForTimeout(2000);
    await captureScreenshot(page, '02-runtime-section');

    // Look for the Runtime configuration table
    console.log('\nLooking for compatibility settings...');

    // Check current values
    const compatDateText = await page.locator('text=Compatibility date').first().isVisible().catch(() => false);
    const compatFlagsText = await page.locator('text=Compatibility flags').first().isVisible().catch(() => false);

    if (compatDateText && compatFlagsText) {
      console.log('\nFound compatibility settings! Checking current values...');

      // Try to read current values from the table
      const dateRow = page.locator('text=Compatibility date').locator('xpath=ancestor::tr | ancestor::div[contains(@class, "row")]').first();
      const flagsRow = page.locator('text=Compatibility flags').locator('xpath=ancestor::tr | ancestor::div[contains(@class, "row")]').first();

      try {
        const currentDate = await dateRow.locator('text=/Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec/').first().textContent({ timeout: 3000 });
        const currentFlags = await flagsRow.locator('text=/nodejs_compat|nodejs_als/').first().textContent({ timeout: 3000 });

        console.log(`\nCurrent settings:`);
        console.log(`  Compatibility date: ${currentDate ? currentDate.trim() : 'Not found'}`);
        console.log(`  Compatibility flags: ${currentFlags ? currentFlags.trim() : 'Not found'}`);

        // Check if values match what we want
        const dateMatches = currentDate && currentDate.includes('Jan 1, 2024');
        const flagsMatch = currentFlags && currentFlags.includes('nodejs_compat');

        if (dateMatches && flagsMatch) {
          console.log('\n='.repeat(70));
          console.log('SUCCESS: Settings are already correctly configured!');
          console.log('='.repeat(70));
          console.log(`  Compatibility date: ${CONFIG.settings.compatibilityDate} (Jan 1, 2024)`);
          console.log(`  Compatibility flags: ${CONFIG.settings.compatibilityFlags}`);
          console.log('='.repeat(70));
          await captureScreenshot(page, '03-verified-correct');
          return;
        } else {
          console.log('\nSettings need to be updated. Looking for edit buttons...');
        }
      } catch (e) {
        console.log('\nCould not read current values. Will attempt to edit...');
      }

      // Look for edit buttons
      const editButtons = page.locator('button:has-text("Edit"), a:has-text("Edit"), button[aria-label*="Edit"]');
      const editCount = await editButtons.count();

      console.log(`\nFound ${editCount} edit button(s)`);

      if (editCount > 0) {
        console.log('\nNOTE: Settings can be edited via the edit buttons on the page.');
        console.log('Since the UI is complex, please manually click the edit buttons and update:');
        console.log(`  1. Compatibility date: ${CONFIG.settings.compatibilityDate}`);
        console.log(`  2. Compatibility flags: ${CONFIG.settings.compatibilityFlags}`);
        await captureScreenshot(page, '04-edit-buttons-found');
      }

    } else {
      console.log('\nWARNING: Could not find compatibility settings on this page.');
      console.log('Current URL:', page.url());
      await captureScreenshot(page, '03-settings-not-found');
    }

  } catch (error) {
    console.error('\nError:', error.message);
    if (page) {
      await captureScreenshot(page, 'error');
      console.error('Current URL:', page.url());
    }
    throw error;
  } finally {
    console.log('\nKeeping Chrome session open...');
  }
}

if (require.main === module) {
  verifyCloudflareSettings()
    .then(() => process.exit(0))
    .catch(() => process.exit(1));
}

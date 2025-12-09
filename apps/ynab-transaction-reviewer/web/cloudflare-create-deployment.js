#!/usr/bin/env node

/**
 * Playwright Automation Script - Cloudflare Pages Create New Deployment
 * Purpose: Create a new deployment from the Cloudflare Pages dashboard
 * Created: 2025-12-03
 *
 * Usage:
 * node cloudflare-create-deployment.js
 *
 * Note: This creates a new deployment rather than retrying an existing one,
 * as Cloudflare Pages doesn't offer "retry" for successful deployments.
 */

const { chromium } = require('playwright');
const fs = require('fs').promises;

const CONFIG = {
  cdpEndpoint: 'http://127.0.0.1:9222',
  targetUrl: 'https://dash.cloudflare.com/b88c78c7542c29614c07bfe30e204759/pages/view/ynab-transaction-reviewer',
  outputDir: './cloudflare-screenshots',
  timeout: 30000,
};

async function captureScreenshot(page, name) {
  try {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const filename = `${CONFIG.outputDir}/${name}-${timestamp}.png`;
    await fs.mkdir(CONFIG.outputDir, { recursive: true });
    await page.screenshot({ path: filename, fullPage: true });
    console.log(`Screenshot: ${filename}`);
    return filename;
  } catch (e) {
    console.log('Could not capture screenshot:', e.message);
    return null;
  }
}

async function createDeployment() {
  let browser = null;
  let page = null;

  try {
    console.log('Starting Cloudflare Pages deployment creation...\n');

    // Connect to existing Chrome
    console.log('Connecting to Chrome via CDP...');
    browser = await chromium.connectOverCDP(CONFIG.cdpEndpoint);
    const defaultContext = browser.contexts()[0];
    page = defaultContext.pages()[0] || await defaultContext.newPage();
    console.log('Connected to Chrome\n');

    // Navigate to Cloudflare Pages project
    console.log('Navigating to Cloudflare Pages dashboard...');
    await page.goto(CONFIG.targetUrl, {
      waitUntil: 'domcontentloaded',
      timeout: CONFIG.timeout
    });

    await page.waitForTimeout(4000);
    await captureScreenshot(page, '01-initial-page');

    // Look for "Create deployment" button
    console.log('\nLooking for "Create deployment" button...');

    const createDeploymentSelectors = [
      'button:has-text("Create deployment")',
      'a:has-text("Create deployment")',
      '[data-testid="create-deployment"]',
    ];

    let createButton = null;
    for (const selector of createDeploymentSelectors) {
      try {
        const button = page.locator(selector).first();
        if (await button.isVisible({ timeout: 2000 })) {
          createButton = button;
          console.log(`Found "Create deployment" button with selector: ${selector}`);
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (!createButton) {
      throw new Error('Could not find "Create deployment" button');
    }

    // Click the button
    console.log('Clicking "Create deployment"...');
    await createButton.click();
    await page.waitForTimeout(2000);
    await captureScreenshot(page, '02-after-create-click');

    // Wait for deployment creation dialog/page
    console.log('\nWaiting for deployment creation form...');
    await page.waitForTimeout(2000);

    // Look for confirmation or submit button
    const submitSelectors = [
      'button:has-text("Create deployment")',  // Confirmation button
      'button:has-text("Deploy")',
      'button:has-text("Confirm")',
      'button[type="submit"]',
    ];

    let submitButton = null;
    for (const selector of submitSelectors) {
      try {
        const button = page.locator(selector).first();
        if (await button.isVisible({ timeout: 3000 })) {
          submitButton = button;
          const buttonText = await button.textContent();
          console.log(`Found submit button: "${buttonText?.trim()}" with selector: ${selector}`);
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (submitButton) {
      console.log('Confirming deployment creation...');
      await submitButton.click();
      await page.waitForTimeout(3000);
      await captureScreenshot(page, '03-deployment-created');

      console.log('\n✓ New deployment created successfully!');
      console.log('The deployment should now be processing with your project settings.');
      console.log('Check the dashboard to monitor deployment progress.');

    } else {
      console.log('\nNote: Could not find explicit submit button.');
      console.log('The deployment may have been created automatically,');
      console.log('or you may need to fill out additional form fields.');
      await captureScreenshot(page, '03-form-state');
      console.log('Please check the screenshot to see current state.');
    }

    // Final screenshot
    await page.waitForTimeout(2000);
    await captureScreenshot(page, '04-final-state');

    console.log('\n=== SUMMARY ===');
    console.log(`Screenshots saved to: ${CONFIG.outputDir}/`);
    console.log('\nNext steps:');
    console.log('1. Check the Cloudflare dashboard for the new deployment');
    console.log('2. Monitor build logs to ensure nodejs_compat is being applied');
    console.log('3. Verify the deployment completes successfully');

  } catch (error) {
    console.error('\nError:', error.message);
    if (page) {
      await captureScreenshot(page, 'error');
      console.log(`Current URL: ${page.url()}`);
    }
    throw error;

  } finally {
    console.log('\nBrowser session kept open');
  }
}

if (require.main === module) {
  createDeployment()
    .then(() => {
      console.log('\nScript completed');
      process.exit(0);
    })
    .catch(error => {
      console.error('\nScript failed:', error.message);
      process.exit(1);
    });
}

module.exports = { createDeployment };

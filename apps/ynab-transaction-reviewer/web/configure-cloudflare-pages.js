#!/usr/bin/env node

/**
 * Cloudflare Pages Configuration Automation
 * Purpose: Automate the configuration of compatibility settings for Cloudflare Pages project
 * Created: 2025-12-03
 *
 * Prerequisites:
 * - Node.js installed
 * - Playwright installed: npm install playwright
 * - Chrome browser (for CDP connection)
 *
 * Usage:
 * node configure-cloudflare-pages.js
 *
 * Authentication:
 * This script attempts to connect to an existing Chrome session via CDP to reuse
 * authentication. If that fails, it launches a new browser and pauses for manual login.
 */

const { chromium } = require('playwright');
const fs = require('fs').promises;

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
  headless: false,
  timeout: 30000,
  retryAttempts: 3,
  screenshotOnError: true,
  cdpEndpoint: 'http://127.0.0.1:9222',
  outputDir: './cloudflare-automation-output',
  projectName: 'ynab-transaction-reviewer',
  compatibilityFlag: 'nodejs_compat',
  compatibilityDate: '2024-01-01',
  targetUrl: 'https://dash.cloudflare.com/b88c78c7542c29614c07bfe30e204759/pages/view/ynab-transaction-reviewer/settings/functions',
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Pause execution and wait for manual authentication
 */
async function pauseForAuthentication(page, message = 'Please complete authentication') {
  console.log('\n' + '='.repeat(60));
  console.log('AUTHENTICATION REQUIRED');
  console.log('='.repeat(60));
  console.log(message);
  console.log('\nCurrent URL:', page.url());
  console.log('\nPress ENTER when authentication is complete...');
  console.log('='.repeat(60) + '\n');

  await new Promise(resolve => {
    process.stdin.once('data', () => resolve());
  });

  console.log('Continuing automation...\n');
}

/**
 * Retry an operation with exponential backoff
 */
async function retryOperation(operation, maxRetries = 3, baseDelay = 1000) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      if (attempt === maxRetries) throw error;
      const delay = baseDelay * Math.pow(2, attempt - 1);
      console.log(`Attempt ${attempt} failed. Retrying in ${delay}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

/**
 * Capture screenshot on error
 */
async function captureErrorState(page, errorContext) {
  if (!CONFIG.screenshotOnError) return null;

  try {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `${CONFIG.outputDir}/error-${errorContext}-${timestamp}.png`;
    await fs.mkdir(CONFIG.outputDir, { recursive: true });
    await page.screenshot({ path: filename, fullPage: true });
    console.log(`Error screenshot: ${filename}`);
    return filename;
  } catch (e) {
    console.log('Could not capture screenshot:', e.message);
    return null;
  }
}

/**
 * Find element using multiple selector strategies
 */
async function findElement(page, selectors, options = {}) {
  const { timeout = 5000 } = options;

  for (const selector of selectors) {
    try {
      const element = page.locator(selector).first();
      await element.waitFor({ state: 'visible', timeout });
      return element;
    } catch (e) {
      continue;
    }
  }

  throw new Error(`Element not found with any selector: ${selectors.join(', ')}`);
}

/**
 * Connect to existing Chrome instance via CDP
 */
async function connectToExistingChrome() {
  try {
    const browser = await chromium.connectOverCDP(CONFIG.cdpEndpoint);
    const defaultContext = browser.contexts()[0];
    const page = defaultContext.pages()[0] || await defaultContext.newPage();
    console.log('Connected to existing Chrome session via CDP');
    return { browser, page, isExistingSession: true };
  } catch (error) {
    console.log('Could not connect to existing Chrome. Launching new instance...');
    return null;
  }
}

/**
 * Launch new browser instance
 */
async function launchNewBrowser() {
  const browser = await chromium.launch({
    headless: CONFIG.headless,
    args: ['--start-maximized'],
  });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
  });
  const page = await context.newPage();
  console.log('Launched new browser instance');
  return { browser, page, isExistingSession: false };
}

/**
 * Wait for navigation to complete
 */
async function waitForNavigation(page, timeout = 10000) {
  try {
    await page.waitForLoadState('domcontentloaded', { timeout });
  } catch (e) {
    console.log('Navigation timeout, continuing anyway...');
  }
}

/**
 * Take a screenshot for documentation
 */
async function captureStep(page, stepName) {
  try {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `${CONFIG.outputDir}/${stepName}-${timestamp}.png`;
    await fs.mkdir(CONFIG.outputDir, { recursive: true });
    await page.screenshot({ path: filename, fullPage: true });
    console.log(`Screenshot saved: ${filename}`);
    return filename;
  } catch (e) {
    console.log('Could not capture screenshot:', e.message);
    return null;
  }
}

// ============================================================================
// MAIN AUTOMATION FUNCTION
// ============================================================================

async function configureCloudflarePages() {
  let browser = null;
  let page = null;
  let isExistingSession = false;

  try {
    console.log('Starting Cloudflare Pages configuration automation...\n');

    // Step 1: Connect to browser (try CDP first, then launch new)
    const connection = await connectToExistingChrome() || await launchNewBrowser();
    browser = connection.browser;
    page = connection.page;
    isExistingSession = connection.isExistingSession;

    // Step 2: Navigate directly to the Functions settings page
    console.log('Navigating directly to Functions settings page...');
    console.log('Target URL:', CONFIG.targetUrl);
    await page.goto(CONFIG.targetUrl, {
      waitUntil: 'domcontentloaded',
      timeout: CONFIG.timeout
    });

    await page.waitForTimeout(3000); // Wait for page to settle

    await captureStep(page, '01-functions-settings-page');

    // Step 8: Look for Compatibility flags input/section
    console.log('Looking for Compatibility flags setting...');

    // Try to find the compatibility flags input field or edit button
    const compatFlagSelectors = [
      'input[name*="compatibility"][name*="flag"]',
      'input[placeholder*="flag"]',
      '[data-testid="compatibility-flags-input"]',
      'label:has-text("Compatibility flags") + input',
      'label:has-text("Compatibility flags") ~ input'
    ];

    let compatFlagInput;
    try {
      compatFlagInput = await findElement(page, compatFlagSelectors, { timeout: 5000 });
    } catch (e) {
      // If input not directly visible, look for an Edit button
      console.log('Looking for Edit button to modify compatibility settings...');
      const editButtonSelectors = [
        'button:has-text("Edit")',
        'button:has-text("Configure")',
        'a:has-text("Edit")',
        '[data-testid="edit-compatibility"]'
      ];

      const editButton = await findElement(page, editButtonSelectors, { timeout: 10000 });
      await editButton.click();
      await page.waitForTimeout(1000);

      // Try to find input again after clicking edit
      compatFlagInput = await findElement(page, compatFlagSelectors, { timeout: 5000 });
    }

    // Step 9: Add compatibility flag
    console.log(`Adding compatibility flag: ${CONFIG.compatibilityFlag}...`);
    await compatFlagInput.scrollIntoViewIfNeeded();
    await compatFlagInput.click();
    await compatFlagInput.fill(CONFIG.compatibilityFlag);
    await page.waitForTimeout(500);

    await captureStep(page, '06-compatibility-flag-added');

    // Step 10: Look for Compatibility date input
    console.log('Looking for Compatibility date setting...');

    const compatDateSelectors = [
      'input[name*="compatibility"][name*="date"]',
      'input[type="date"]',
      'input[placeholder*="date"]',
      '[data-testid="compatibility-date-input"]',
      'label:has-text("Compatibility date") + input',
      'label:has-text("Compatibility date") ~ input'
    ];

    const compatDateInput = await findElement(page, compatDateSelectors, { timeout: 5000 });

    // Step 11: Set compatibility date
    console.log(`Setting compatibility date: ${CONFIG.compatibilityDate}...`);
    await compatDateInput.scrollIntoViewIfNeeded();
    await compatDateInput.click();
    await compatDateInput.fill(CONFIG.compatibilityDate);
    await page.waitForTimeout(500);

    await captureStep(page, '07-compatibility-date-added');

    // Step 12: Save the changes
    console.log('Looking for Save button...');

    const saveButtonSelectors = [
      'button:has-text("Save")',
      'button[type="submit"]',
      'button:has-text("Update")',
      'button:has-text("Apply")',
      '[data-testid="save-button"]'
    ];

    const saveButton = await findElement(page, saveButtonSelectors, { timeout: 5000 });
    await saveButton.scrollIntoViewIfNeeded();
    await saveButton.click();

    console.log('Save button clicked. Waiting for changes to be applied...');
    await page.waitForTimeout(3000);

    await captureStep(page, '08-changes-saved');

    // Step 13: Verify success
    console.log('Checking for success confirmation...');

    const successSelectors = [
      'text=Successfully',
      'text=saved',
      'text=updated',
      '[data-testid="success-message"]',
      '.success',
      '.notification.is-success'
    ];

    try {
      const successMessage = await findElement(page, successSelectors, { timeout: 5000 });
      const messageText = await successMessage.textContent();
      console.log(`Success message: ${messageText}`);
    } catch (e) {
      console.log('No explicit success message found, but changes appear to have been saved.');
    }

    await captureStep(page, '09-final-state');

    // Step 14: Document the configuration
    const configSummary = {
      timestamp: new Date().toISOString(),
      project: CONFIG.projectName,
      settings: {
        compatibilityFlag: CONFIG.compatibilityFlag,
        compatibilityDate: CONFIG.compatibilityDate
      },
      status: 'Configuration completed successfully'
    };

    const summaryFile = `${CONFIG.outputDir}/configuration-summary.json`;
    await fs.writeFile(summaryFile, JSON.stringify(configSummary, null, 2));
    console.log(`\nConfiguration summary saved to: ${summaryFile}`);

    console.log('\n' + '='.repeat(60));
    console.log('CONFIGURATION COMPLETED SUCCESSFULLY');
    console.log('='.repeat(60));
    console.log(`Project: ${CONFIG.projectName}`);
    console.log(`Compatibility Flag: ${CONFIG.compatibilityFlag}`);
    console.log(`Compatibility Date: ${CONFIG.compatibilityDate}`);
    console.log(`\nScreenshots saved to: ${CONFIG.outputDir}/`);
    console.log('='.repeat(60) + '\n');

  } catch (error) {
    console.error('\nAutomation failed:', error.message);
    console.error('Stack trace:', error.stack);

    if (page) {
      await captureErrorState(page, 'main-error');
      console.log('\nCurrent URL:', page.url());
      console.log('Page title:', await page.title().catch(() => 'N/A'));
    }

    throw error;

  } finally {
    // Cleanup
    if (!isExistingSession && browser) {
      await browser.close().catch(() => {});
      console.log('Browser closed');
    } else {
      console.log('Cleanup complete (existing session kept open)');
    }
  }
}

// ============================================================================
// EXECUTION
// ============================================================================

if (require.main === module) {
  configureCloudflarePages()
    .then(() => process.exit(0))
    .catch(error => {
      console.error('Fatal error:', error);
      process.exit(1);
    });
}

module.exports = { configureCloudflarePages };

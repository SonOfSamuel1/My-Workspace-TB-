#!/usr/bin/env node

/**
 * Playwright Automation Script - Cloudflare Pages Redeployment
 * Purpose: Trigger a redeployment of ynab-transaction-reviewer on Cloudflare Pages
 * Created: 2025-12-03
 *
 * Prerequisites:
 * - Node.js installed
 * - Playwright installed: npm install playwright
 * - Chrome running in debug mode on port 9222
 *
 * Usage:
 * node cloudflare-redeploy.js
 *
 * Authentication:
 * Uses CDP connection to existing Chrome session (already logged into Cloudflare)
 */

const { chromium } = require('playwright');
const fs = require('fs').promises;

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
  cdpEndpoint: 'http://127.0.0.1:9222',
  targetUrl: 'https://dash.cloudflare.com/b88c78c7542c29614c07bfe30e204759/pages/view/ynab-transaction-reviewer',
  outputDir: './cloudflare-screenshots',
  timeout: 30000,
  screenshotOnError: true,
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Capture screenshot with timestamp
 */
async function captureScreenshot(page, name) {
  try {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const filename = `${CONFIG.outputDir}/${name}-${timestamp}.png`;
    await fs.mkdir(CONFIG.outputDir, { recursive: true });
    await page.screenshot({ path: filename, fullPage: true });
    console.log(`Screenshot saved: ${filename}`);
    return filename;
  } catch (e) {
    console.log('Warning: Could not capture screenshot:', e.message);
    return null;
  }
}

/**
 * Capture error state
 */
async function captureErrorState(page, errorContext) {
  if (!CONFIG.screenshotOnError) return null;
  return await captureScreenshot(page, `error-${errorContext}`);
}

/**
 * Wait with timeout and helpful error message
 */
async function waitForElementWithTimeout(page, selector, description, timeout = 10000) {
  try {
    console.log(`Waiting for: ${description}...`);
    await page.waitForSelector(selector, { timeout, state: 'visible' });
    console.log(`Found: ${description}`);
    return true;
  } catch (error) {
    console.log(`Timeout waiting for: ${description}`);
    console.log(`Selector tried: ${selector}`);
    return false;
  }
}

/**
 * Connect to existing Chrome instance via CDP
 */
async function connectToExistingChrome() {
  try {
    console.log('Connecting to Chrome via CDP...');
    const browser = await chromium.connectOverCDP(CONFIG.cdpEndpoint);
    const defaultContext = browser.contexts()[0];
    const page = defaultContext.pages()[0] || await defaultContext.newPage();
    console.log('Connected to existing Chrome session via CDP');
    return { browser, page };
  } catch (error) {
    throw new Error(
      `Could not connect to Chrome at ${CONFIG.cdpEndpoint}\n` +
      `Make sure Chrome is running with: chrome --remote-debugging-port=9222\n` +
      `Error: ${error.message}`
    );
  }
}

// ============================================================================
// MAIN AUTOMATION FUNCTION
// ============================================================================

async function triggerRedeployment() {
  let browser = null;
  let page = null;

  try {
    console.log('Starting Cloudflare Pages redeployment automation...\n');

    // Step 1: Connect to existing Chrome session
    const connection = await connectToExistingChrome();
    browser = connection.browser;
    page = connection.page;

    // Step 2: Navigate to Cloudflare Pages project
    console.log('\nNavigating to Cloudflare Pages dashboard...');
    await page.goto(CONFIG.targetUrl, {
      waitUntil: 'domcontentloaded',
      timeout: CONFIG.timeout
    });

    // Wait for page to load and give extra time for dynamic content
    console.log('Waiting for page content to load...');
    await page.waitForTimeout(5000);

    // Scroll down to trigger lazy loading
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(2000);
    await page.evaluate(() => window.scrollTo(0, 0));

    await captureScreenshot(page, '01-initial-page-load');

    // Step 3: Look for the deployments section
    console.log('\nLooking for deployment history...');

    // Check if we're on the right page
    const pageTitle = await page.title();
    console.log(`Page title: ${pageTitle}`);

    // Check for "Deployments" tab to confirm we're in the right section
    const deploymentsTab = await page.locator('text=Deployments').first();
    if (await deploymentsTab.isVisible().catch(() => false)) {
      console.log('Found "Deployments" tab - we are on the correct page');
    }

    // Step 4: Find the most recent deployment
    // Cloudflare Pages typically shows deployments in a list/table format
    // Common selectors for deployment rows
    const deploymentSelectors = [
      '[data-testid="deployment-row"]',
      '.deployment-item',
      '[role="row"]',
      'tr[data-deployment]',
      '.deployments-list > div',
      'table tbody tr'
    ];

    let deploymentFound = false;
    let deploymentElement = null;

    for (const selector of deploymentSelectors) {
      try {
        const elements = await page.locator(selector).all();
        if (elements.length > 0) {
          console.log(`Found ${elements.length} potential deployment(s) with selector: ${selector}`);
          deploymentElement = elements[0]; // Get the first (most recent) deployment
          deploymentFound = true;
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (!deploymentFound) {
      console.log('Could not find deployment elements with standard selectors');
      console.log('Attempting to find by text content...');

      // Try to find any element containing deployment-related text
      const textMatches = await page.getByText(/production|preview|deployment/i).all();
      console.log(`Found ${textMatches.length} elements with deployment-related text`);
    }

    await captureScreenshot(page, '02-deployments-page');

    // Step 5: Look for redeploy/retry button
    console.log('\nSearching for redeploy options...');

    // DEBUG: Print all visible buttons on the page
    console.log('\nDEBUG: Scanning all buttons on the page...');
    const allButtons = await page.locator('button').all();
    console.log(`Found ${allButtons.length} total buttons`);

    for (let i = 0; i < Math.min(allButtons.length, 30); i++) {
      try {
        const button = allButtons[i];
        const isVisible = await button.isVisible();
        if (isVisible) {
          const text = await button.textContent();
          const ariaLabel = await button.getAttribute('aria-label');
          console.log(`  Button ${i}: text="${text?.trim() || '(empty)'}" aria-label="${ariaLabel || '(none)'}"`);
        }
      } catch (e) {
        // Skip buttons we can't inspect
      }
    }

    // First, close the search dialog if it's open
    try {
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
      console.log('Closed search dialog if it was open');
    } catch (e) {
      // No problem if it wasn't open
    }

    // Find the deployment rows and click the menu button on the FIRST (most recent) row
    // The three dots menu button should be in the same row as the deployment
    console.log('\nLooking for the three-dots menu in the first deployment row...');

    // Get the first table row (most recent deployment)
    const firstDeploymentRow = page.locator('table tbody tr').first();

    if (await firstDeploymentRow.isVisible({ timeout: 2000 })) {
      console.log('Found first deployment row');

      // Find the three-dots button within that row
      // It's likely the last button in the row, or has specific text "..."
      const menuInRow = firstDeploymentRow.locator('button').last();

      if (await menuInRow.isVisible({ timeout: 2000 })) {
        console.log('Found menu button in deployment row');
        const buttonText = await menuInRow.textContent();
        console.log(`Button text: "${buttonText?.trim()}"`);

        menuButton = menuInRow;
      } else {
        console.log('Could not find menu button in row, trying alternative approach');
      }
    }

    // Fallback: try to find any three-dots button near deployments
    if (!menuButton) {
      const menuButtonSelectors = [
        'table tbody tr button:has-text("...")',
        'table tbody tr button[aria-label*="menu"]',
        'table tbody tr button[aria-label*="actions"]',
        '[data-testid="deployment-actions"]',
      ];

      for (const selector of menuButtonSelectors) {
        try {
          const button = page.locator(selector).first();
          if (await button.isVisible({ timeout: 1000 })) {
            menuButton = button;
            console.log(`Found menu button with fallback selector: ${selector}`);
            break;
          }
        } catch (e) {
          continue;
        }
      }
    }

    if (menuButton) {
      console.log('Clicking deployment actions menu...');
      await menuButton.click();
      await page.waitForTimeout(1000);
      await captureScreenshot(page, '03-menu-opened');

      // Look for retry/redeploy option in the menu
      console.log('\nLooking for retry/redeploy option in the dropdown menu...');

      // First, let's check what options are in the menu
      const menuItems = await page.locator('[role="menuitem"], button[role="menuitem"], a[role="menuitem"]').all();
      console.log(`Found ${menuItems.length} menu items`);

      for (let i = 0; i < menuItems.length; i++) {
        try {
          const text = await menuItems[i].textContent();
          console.log(`  Menu item ${i}: "${text?.trim()}"`);
        } catch (e) {
          // Skip
        }
      }

      // Try various selectors for retry/redeploy
      const redeploySelectors = [
        'button:has-text("Retry deployment")',
        'button:has-text("Retry")',
        'button:has-text("Redeploy")',
        '[role="menuitem"]:has-text("Retry")',
        '[role="menuitem"]:has-text("Redeploy")',
        'a:has-text("Retry deployment")',
        'a:has-text("Redeploy")',
        // Sometimes it's just in a div or span within the dropdown
        'div:has-text("Retry deployment")',
        'span:has-text("Retry")',
      ];

      let redeployButton = null;
      for (const selector of redeploySelectors) {
        try {
          const element = page.locator(selector).first();
          if (await element.isVisible({ timeout: 2000 })) {
            redeployButton = element;
            console.log(`Found redeploy button with selector: ${selector}`);
            break;
          }
        } catch (e) {
          continue;
        }
      }

      if (redeployButton) {
        console.log('\nTriggering redeployment...');
        await redeployButton.click();
        await page.waitForTimeout(2000);
        await captureScreenshot(page, '04-after-redeploy-click');

        // Check for confirmation dialog
        const confirmSelectors = [
          'button:has-text("Confirm")',
          'button:has-text("Yes")',
          'button:has-text("Retry")',
          '[role="dialog"] button[type="submit"]',
        ];

        for (const selector of confirmSelectors) {
          try {
            const confirmButton = page.locator(selector).first();
            if (await confirmButton.isVisible({ timeout: 3000 })) {
              console.log('Confirming redeployment...');
              await confirmButton.click();
              await page.waitForTimeout(2000);
              await captureScreenshot(page, '05-deployment-confirmed');
              break;
            }
          } catch (e) {
            continue;
          }
        }

        console.log('\nRedeployment triggered successfully!');
        console.log('Check the Cloudflare dashboard for deployment progress.');

      } else {
        console.log('Could not find redeploy button in menu');

        // Try alternative approach: look for redeploy button directly on the page
        console.log('\nTrying alternative approach: looking for inline redeploy button...');
        const inlineRedeploySelectors = [
          'button:has-text("Retry")',
          'button:has-text("Redeploy")',
          '[data-action="retry"]',
          '[data-action="redeploy"]',
        ];

        for (const selector of inlineRedeploySelectors) {
          try {
            const button = page.locator(selector).first();
            if (await button.isVisible({ timeout: 2000 })) {
              console.log(`Found inline redeploy button: ${selector}`);
              await button.click();
              await page.waitForTimeout(2000);
              await captureScreenshot(page, '04-inline-redeploy-clicked');
              console.log('Redeployment triggered!');
              break;
            }
          } catch (e) {
            continue;
          }
        }
      }
    } else {
      console.log('Could not find deployment actions menu');
      console.log('\nTrying direct approaches to trigger redeploy...');

      // Approach 1: Click "View details" on the most recent deployment
      console.log('\nApproach 1: Clicking "View details" on first deployment...');

      // Get the "View details" link from the first deployment row
      const viewDetailsLink = page.locator('table tbody tr').first().locator('a:has-text("View details")');

      if (await viewDetailsLink.isVisible({ timeout: 2000 })) {
        console.log('Found "View details" link, clicking it...');
        await viewDetailsLink.click();
        await page.waitForTimeout(3000); // Wait for deployment details page to load
        await captureScreenshot(page, '04-deployment-details-page');

        console.log(`Current URL after View details: ${page.url()}`);

        // On the deployment details page, look for a "Manage" or "Retry" button
        const deploymentPageActions = [
          'button:has-text("Manage deployment")',
          'button:has-text("Retry deployment")',
          'button:has-text("Retry")',
          'button:has-text("Redeploy")',
          '[data-action="retry"]',
        ];

        for (const selector of deploymentPageActions) {
          try {
            const button = page.locator(selector).first();
            if (await button.isVisible({ timeout: 2000 })) {
              console.log(`Found action button: ${selector}`);
              await button.click();
              await page.waitForTimeout(2000);
              await captureScreenshot(page, '05-action-clicked');

              // Check for confirmation dialog
              const confirmButton = page.locator('button:has-text("Confirm"), button:has-text("Yes"), button:has-text("Retry")').first();
              if (await confirmButton.isVisible({ timeout: 2000 })) {
                console.log('Found confirmation button, clicking it...');
                await confirmButton.click();
                await page.waitForTimeout(2000);
                await captureScreenshot(page, '06-deployment-triggered');
              }

              console.log('\nRedeployment triggered successfully!');
              return;
            }
          } catch (e) {
            continue;
          }
        }

        console.log('No retry/redeploy button found on deployment details page');

        // Navigate back to deployments list
        await page.goBack();
        await page.waitForTimeout(2000);
      }

      // Approach 2: Look for any "Retry" or "Redeploy" button directly
      console.log('\nApproach 2: Looking for direct retry/redeploy buttons...');
      const directRetrySelectors = [
        'button:has-text("Retry deployment")',
        'button:has-text("Retry")',
        'button:has-text("Redeploy")',
        '[data-action="retry"]',
        '[data-action="redeploy"]',
        'a:has-text("Retry deployment")',
      ];

      for (const selector of directRetrySelectors) {
        try {
          const button = page.locator(selector).first();
          if (await button.isVisible({ timeout: 2000 })) {
            console.log(`Found direct retry button: ${selector}`);
            await button.click();
            await page.waitForTimeout(2000);
            await captureScreenshot(page, '04-direct-retry-clicked');
            console.log('\nRedeployment triggered successfully!');
            return;
          }
        } catch (e) {
          continue;
        }
      }

      console.log('\nApproach 3: Manual intervention needed');
      console.log('Could not automatically find the redeploy button.');
      console.log('Please review the screenshots to see what options are available.');
    }

    // Final screenshot
    await page.waitForTimeout(2000);
    await captureScreenshot(page, '06-final-state');

    console.log('\n=== SUMMARY ===');
    console.log(`Target URL: ${CONFIG.targetUrl}`);
    console.log(`Screenshots saved to: ${CONFIG.outputDir}/`);
    console.log('\nNext steps:');
    console.log('1. Review the screenshots to verify the redeployment was triggered');
    console.log('2. Monitor the deployment status in the Cloudflare dashboard');
    console.log('3. Check if nodejs_compat flag is applied in the new deployment');

  } catch (error) {
    console.error('\nAutomation failed:', error.message);
    console.error('Stack trace:', error.stack);

    if (page) {
      await captureErrorState(page, 'main-error');
      console.log(`\nCurrent URL: ${page.url()}`);
    }

    throw error;

  } finally {
    // Keep the browser session open (it's an existing session)
    console.log('\nAutomation complete (browser session kept open)');
  }
}

// ============================================================================
// EXECUTION
// ============================================================================

if (require.main === module) {
  triggerRedeployment()
    .then(() => {
      console.log('\nScript completed successfully');
      process.exit(0);
    })
    .catch(error => {
      console.error('\nScript failed:', error.message);
      process.exit(1);
    });
}

module.exports = { triggerRedeployment };

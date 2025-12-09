const { chromium } = require('playwright');

async function configureCloudflarePages() {
  console.log('Connecting to Chrome...');

  const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
  const contexts = browser.contexts();
  const context = contexts[0];
  const pages = context.pages();
  const page = pages[0] || await context.newPage();

  console.log('Navigating directly to project settings...');

  // Go directly to the Functions settings page
  await page.goto('https://dash.cloudflare.com/b88c78c7542c29614c07bfe30e204759/pages/view/ynab-transaction-reviewer/settings/functions');
  await page.waitForLoadState('networkidle');

  console.log('Current URL:', page.url());
  await page.screenshot({ path: 'cloudflare-settings.png' });

  // Wait a bit for the page to fully load
  await page.waitForTimeout(3000);

  // Look for compatibility date input and set it
  console.log('Looking for compatibility settings...');

  // Try to find and interact with the compatibility date field
  const compatDateInput = page.locator('input[name*="compatibility"], input[placeholder*="date"], input[aria-label*="date"]').first();
  if (await compatDateInput.isVisible({ timeout: 5000 }).catch(() => false)) {
    console.log('Found compatibility date input');
    await compatDateInput.fill('2024-01-01');
  }

  // Look for compatibility flags
  const flagsInput = page.locator('input[name*="flag"], input[placeholder*="flag"]').first();
  if (await flagsInput.isVisible({ timeout: 5000 }).catch(() => false)) {
    console.log('Found compatibility flags input');
    await flagsInput.fill('nodejs_compat');
  }

  // Take final screenshot
  await page.screenshot({ path: 'cloudflare-settings-final.png' });
  console.log('Screenshots saved. Please check the browser to verify settings.');
  console.log('The browser will stay open so you can manually complete the configuration if needed.');
}

configureCloudflarePages().catch(console.error);

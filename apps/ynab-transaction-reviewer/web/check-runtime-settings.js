#!/usr/bin/env node

const { chromium } = require('playwright');

async function checkSettings() {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
  const context = browser.contexts()[0];
  const page = context.pages()[0];

  console.log('\n' + '='.repeat(70));
  console.log('CLOUDFLARE PAGES RUNTIME CONFIGURATION');
  console.log('='.repeat(70));

  // Navigate to settings page
  await page.goto('https://dash.cloudflare.com/b88c78c7542c29614c07bfe30e204759/pages/view/ynab-transaction-reviewer/settings/functions',
    { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);

  // Extract the compatibility date value
  const compatDateRow = page.locator('text=Compatibility date').locator('xpath=ancestor::tr | ancestor::div').first();
  const dateValue = await compatDateRow.textContent();

  // Extract the compatibility flags value
  const compatFlagsRow = page.locator('text=Compatibility flags').locator('xpath=ancestor::tr | ancestor::div').first();
  const flagsValue = await compatFlagsRow.textContent();

  console.log('\nCurrent Settings:');
  console.log('-'.repeat(70));

  // Parse and display compatibility date
  const dateMatch = dateValue.match(/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+,\s+\d+/);
  if (dateMatch) {
    console.log(`Compatibility date:       ${dateMatch[0]}`);
  }

  // Parse and display compatibility flags
  const flagsMatch = flagsValue.match(/nodejs_[a-z_]+/);
  if (flagsMatch) {
    console.log(`Compatibility flags:      ${flagsMatch[0]}`);
  }

  console.log('\nTarget Settings:');
  console.log('-'.repeat(70));
  console.log('Compatibility date:       2024-01-01 (Jan 1, 2024)');
  console.log('Compatibility flags:      nodejs_compat');

  console.log('\nVerification:');
  console.log('-'.repeat(70));

  const dateCorrect = dateValue.includes('Jan 1, 2024') || dateValue.includes('2024-01-01');
  const flagsCorrect = flagsValue.includes('nodejs_compat');

  console.log(`Compatibility date:       ${dateCorrect ? '✓ CORRECT' : '✗ NEEDS UPDATE'}`);
  console.log(`Compatibility flags:      ${flagsCorrect ? '✓ CORRECT' : '✗ NEEDS UPDATE'}`);

  if (dateCorrect && flagsCorrect) {
    console.log('\n' + '='.repeat(70));
    console.log('STATUS: All settings are correctly configured!');
    console.log('='.repeat(70) + '\n');
  } else {
    console.log('\n' + '='.repeat(70));
    console.log('STATUS: Settings need to be updated');
    console.log('='.repeat(70) + '\n');
  }
}

checkSettings().then(() => process.exit(0)).catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});

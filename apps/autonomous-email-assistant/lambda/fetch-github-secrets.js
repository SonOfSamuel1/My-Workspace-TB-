/**
 * Fetch GitHub Secrets using Playwright
 * This script navigates to GitHub secrets page and extracts the values
 */

const { chromium } = require('playwright');
const { execSync } = require('child_process');

async function fetchGitHubSecrets() {
  console.log('Fetching GitHub secrets via Playwright...\n');

  const browser = await chromium.launch({
    headless: false,
    slowMo: 100
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to the repo secrets page
    const repoUrl = 'https://github.com/SonOfSamuel1/App--Internal-Business--Autonomous-Email-Assistant';
    const secretsUrl = `${repoUrl}/settings/secrets/actions`;

    console.log('Navigating to GitHub secrets page...');
    await page.goto(secretsUrl);

    // Wait for page to load
    await page.waitForTimeout(2000);

    // Check if we need to login
    const loginNeeded = await page.locator('input[name="login"]').count() > 0;

    if (loginNeeded) {
      console.log('Please log in to GitHub...');
      await page.waitForURL(/github\.com\/SonOfSamuel1/, { timeout: 120000 });
      console.log('Logged in! Navigating to secrets...');
      await page.goto(secretsUrl);
      await page.waitForTimeout(2000);
    }

    console.log('\n========================================');
    console.log('GitHub Secrets Found:');
    console.log('========================================\n');

    // Get list of secret names
    const secretNames = await page.locator('[data-target="secrets-list.name"]').allTextContents();

    console.log('Available secrets:');
    secretNames.forEach((name, i) => {
      console.log(`${i + 1}. ${name}`);
    });

    console.log('\n⚠️  Note: GitHub UI does not allow viewing secret values for security reasons.');
    console.log('The secrets are already configured in GitHub Actions.\n');

    console.log('To deploy to Lambda, you need to either:');
    console.log('1. Set up the credentials locally (recommended)');
    console.log('2. Manually enter them during deployment\n');

    console.log('To set up credentials locally:');
    console.log('=====================================\n');

    console.log('1. Get Claude Code token:');
    console.log('   claude setup-token\n');

    console.log('2. Set up Gmail MCP:');
    console.log('   npm install -g @gongrzhe/server-gmail-autoauth-mcp');
    console.log('   # Follow OAuth flow to create ~/.gmail-mcp/ directory\n');

    console.log('3. Then run deployment:');
    console.log('   cd lambda');
    console.log('   ./deploy-auto.sh\n');

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
}

// Run if called directly
if (require.main === module) {
  fetchGitHubSecrets().catch(console.error);
}

module.exports = { fetchGitHubSecrets };

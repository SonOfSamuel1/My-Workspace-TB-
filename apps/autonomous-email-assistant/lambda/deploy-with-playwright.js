/**
 * AWS Lambda Deployment via Playwright MCP
 *
 * This script uses Playwright to automate the AWS Console deployment
 * instead of using AWS CLI/SAM CLI
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
  AWS_CONSOLE_URL: 'https://console.aws.amazon.com',
  AWS_REGION: process.env.AWS_REGION || 'us-east-1',
  FUNCTION_NAME: 'email-assistant-processor',
  TIMEOUT: 300000, // 5 minutes
};

// Read credential files
function getCredentials() {
  const gmailOauthPath = path.join(process.env.HOME, '.gmail-mcp', 'gcp-oauth.keys.json');
  const gmailCredsPath = path.join(process.env.HOME, '.gmail-mcp', 'credentials.json');

  if (!fs.existsSync(gmailOauthPath)) {
    throw new Error(`Gmail OAuth credentials not found at ${gmailOauthPath}`);
  }

  if (!fs.existsSync(gmailCredsPath)) {
    throw new Error(`Gmail credentials not found at ${gmailCredsPath}`);
  }

  const gmailOauth = fs.readFileSync(gmailOauthPath, 'utf-8');
  const gmailCreds = fs.readFileSync(gmailCredsPath, 'utf-8');

  return {
    gmailOauthBase64: Buffer.from(gmailOauth).toString('base64'),
    gmailCredsBase64: Buffer.from(gmailCreds).toString('base64'),
  };
}

// Read Lambda function code
function getLambdaCode() {
  const indexPath = path.join(__dirname, 'index.js');
  return fs.readFileSync(indexPath, 'utf-8');
}

// Main deployment function
async function deployLambda() {
  console.log('Starting AWS Lambda deployment via Playwright...');
  console.log('');

  // Get credentials
  const creds = getCredentials();
  console.log('✓ Loaded Gmail credentials');

  // Get Claude Code token from environment or prompt
  const claudeToken = process.env.CLAUDE_CODE_OAUTH_TOKEN;
  if (!claudeToken) {
    console.error('Error: CLAUDE_CODE_OAUTH_TOKEN environment variable not set');
    process.exit(1);
  }
  console.log('✓ Claude Code token found');

  // Launch browser
  const browser = await chromium.launch({
    headless: false, // Show browser for AWS login
    slowMo: 100,
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to AWS Console
    console.log('Opening AWS Console...');
    await page.goto(CONFIG.AWS_CONSOLE_URL);

    // Wait for user to log in (if not already logged in)
    console.log('Please log in to AWS Console if prompted...');
    await page.waitForURL(/console\.aws\.amazon\.com/, { timeout: 120000 });
    console.log('✓ Logged in to AWS Console');

    // Navigate to Lambda
    console.log('Navigating to Lambda...');
    await page.goto(`https://${CONFIG.AWS_REGION}.console.aws.amazon.com/lambda/home?region=${CONFIG.AWS_REGION}#/functions`);
    await page.waitForTimeout(2000);

    // Check if function already exists
    const functionExists = await page.locator(`text="${CONFIG.FUNCTION_NAME}"`).count() > 0;

    if (functionExists) {
      console.log(`Function "${CONFIG.FUNCTION_NAME}" already exists. Updating...`);

      // Click on function name
      await page.click(`text="${CONFIG.FUNCTION_NAME}"`);
      await page.waitForTimeout(2000);

      // Go to Configuration → Environment variables
      await page.click('text=Configuration');
      await page.waitForTimeout(1000);
      await page.click('text=Environment variables');
      await page.waitForTimeout(1000);

      // Update environment variables
      await updateEnvironmentVariables(page, {
        CLAUDE_CODE_OAUTH_TOKEN: claudeToken,
        GMAIL_OAUTH_CREDENTIALS: creds.gmailOauthBase64,
        GMAIL_CREDENTIALS: creds.gmailCredsBase64,
        TWILIO_ACCOUNT_SID: process.env.TWILIO_ACCOUNT_SID || '',
        TWILIO_AUTH_TOKEN: process.env.TWILIO_AUTH_TOKEN || '',
        TWILIO_FROM_NUMBER: process.env.TWILIO_FROM_NUMBER || '',
        ESCALATION_PHONE: process.env.ESCALATION_PHONE || '+14077448449',
      });

      console.log('✓ Environment variables updated');

    } else {
      console.log(`Creating new function "${CONFIG.FUNCTION_NAME}"...`);

      // Click "Create function"
      await page.click('button:has-text("Create function")');
      await page.waitForTimeout(2000);

      // Select "Container image" option
      await page.click('input[value="container-image"]');
      await page.waitForTimeout(1000);

      // Enter function name
      await page.fill('input[placeholder*="function name"]', CONFIG.FUNCTION_NAME);

      // Note: For container image, user needs to push to ECR first
      console.log('');
      console.log('⚠️  For container-based Lambda, you need to:');
      console.log('   1. Build Docker image locally');
      console.log('   2. Push to Amazon ECR');
      console.log('   3. Provide ECR image URI');
      console.log('');
      console.log('Switching to automated approach with AWS CLI...');

      await browser.close();
      console.log('');
      console.log('Please use the deploy.sh script instead for container-based deployment:');
      console.log('  cd lambda && ./deploy.sh');
      return;
    }

    console.log('');
    console.log('✓ Deployment completed successfully!');
    console.log('');
    console.log('Next steps:');
    console.log('1. Set up EventBridge schedule for hourly execution');
    console.log('2. Test the function manually');
    console.log('3. Monitor CloudWatch Logs');

  } catch (error) {
    console.error('Error during deployment:', error);
    throw error;

  } finally {
    await browser.close();
  }
}

// Update environment variables
async function updateEnvironmentVariables(page, envVars) {
  await page.click('button:has-text("Edit")');
  await page.waitForTimeout(1000);

  for (const [key, value] of Object.entries(envVars)) {
    if (!value) continue; // Skip empty values

    // Check if variable exists
    const existingVar = await page.locator(`text="${key}"`).count() > 0;

    if (existingVar) {
      // Click edit on existing variable
      const row = page.locator(`tr:has-text("${key}")`);
      await row.locator('button:has-text("Edit")').click();
      await page.waitForTimeout(500);

      // Update value
      await page.fill(`input[name*="value"]`, value);
      await page.click('button:has-text("Save")');

    } else {
      // Add new variable
      await page.click('button:has-text("Add environment variable")');
      await page.waitForTimeout(500);

      // Fill in key and value
      const rows = await page.locator('tr[class*="environment-variable"]').count();
      await page.fill(`input[name="key-${rows}"]`, key);
      await page.fill(`input[name="value-${rows}"]`, value);
    }
  }

  // Save all changes
  await page.click('button:has-text("Save")');
  await page.waitForTimeout(2000);
}

// Setup EventBridge schedule
async function setupEventBridgeSchedule(page) {
  console.log('Setting up EventBridge schedule...');

  // Navigate to EventBridge
  await page.goto(`https://${CONFIG.AWS_REGION}.console.aws.amazon.com/events/home?region=${CONFIG.AWS_REGION}#/rules`);
  await page.waitForTimeout(2000);

  // Create rule
  await page.click('button:has-text("Create rule")');
  await page.waitForTimeout(1000);

  // Enter rule name
  await page.fill('input[placeholder*="rule name"]', 'email-assistant-hourly-schedule');

  // Enter description
  await page.fill('textarea[placeholder*="description"]', 'Hourly email processing from 7 AM to 5 PM EST (Mon-Fri)');

  // Select schedule
  await page.click('input[value="schedule"]');
  await page.waitForTimeout(500);

  // Enter cron expression
  await page.fill('input[placeholder*="cron"]', 'cron(0 12-22 ? * MON-FRI *)');

  // Click Next
  await page.click('button:has-text("Next")');
  await page.waitForTimeout(1000);

  // Select Lambda target
  await page.click('text=Lambda function');
  await page.waitForTimeout(500);

  // Select function from dropdown
  await page.selectOption('select[name*="function"]', CONFIG.FUNCTION_NAME);

  // Click Next
  await page.click('button:has-text("Next")');
  await page.waitForTimeout(1000);

  // Click Create rule
  await page.click('button:has-text("Create rule")');
  await page.waitForTimeout(2000);

  console.log('✓ EventBridge schedule created');
}

// Run deployment
deployLambda().catch(error => {
  console.error('Deployment failed:', error);
  process.exit(1);
});

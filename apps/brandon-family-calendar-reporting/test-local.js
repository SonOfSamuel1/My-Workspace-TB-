/**
 * Local testing script for the Lambda function
 *
 * Usage:
 * 1. Copy .env.example to .env
 * 2. Fill in your credentials in .env
 * 3. Run: node test-local.js
 */

require('dotenv').config();
const { handler } = require('./index');

async function testLocal() {
  console.log('Testing Lambda function locally...\n');

  // Verify environment variables
  const requiredVars = [
    'UNIQUE_EVENTS_CALENDAR_ID',
    'BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID',
    'EMAIL_TO',
    'EMAIL_FROM'
  ];

  // Check for either service account OR OAuth file credentials
  const hasServiceAccount = process.env.GOOGLE_CLIENT_EMAIL && process.env.GOOGLE_PRIVATE_KEY;
  const hasOAuthFiles = process.env.GOOGLE_CREDENTIALS_PATH && process.env.GOOGLE_TOKEN_PATH;

  if (!hasServiceAccount && !hasOAuthFiles) {
    console.error('❌ Missing Google credentials. Set either:');
    console.error('   Option 1: GOOGLE_CLIENT_EMAIL and GOOGLE_PRIVATE_KEY (service account)');
    console.error('   Option 2: GOOGLE_CREDENTIALS_PATH and GOOGLE_TOKEN_PATH (OAuth files)');
    console.error('\nRun "node authorize.js" to set up OAuth credentials');
    process.exit(1);
  }

  const missing = requiredVars.filter(v => !process.env[v]);
  if (missing.length > 0) {
    console.error('❌ Missing required environment variables:');
    missing.forEach(v => console.error(`   - ${v}`));
    console.error('\nPlease set these in your .env file');
    process.exit(1);
  }

  console.log('✓ Environment variables loaded');
  console.log(`✓ Email will be sent to: ${process.env.EMAIL_TO}`);
  console.log(`✓ Email will be sent from: ${process.env.EMAIL_FROM}`);
  if (hasServiceAccount) {
    console.log('✓ Using Service Account credentials');
  } else {
    console.log('✓ Using OAuth credentials from files');
  }

  console.log('Invoking Lambda handler...\n');

  try {
    const event = {};
    const context = {
      functionName: 'calendar-report-test',
      awsRequestId: 'test-request-id'
    };

    const result = await handler(event, context);

    console.log('\n=== RESULT ===');
    console.log(JSON.stringify(result, null, 2));

    if (result.statusCode === 200) {
      console.log('\n✅ SUCCESS! Check your email inbox.');
    } else {
      console.log('\n❌ FAILED. Check the error message above.');
    }

  } catch (error) {
    console.error('\n❌ ERROR:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

testLocal();

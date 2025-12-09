#!/usr/bin/env node

/**
 * Minimal Test Email Sender - bypasses complex dependencies
 */

const AWS = require('aws-sdk');
const fs = require('fs');
const path = require('path');

console.log('=== MINIMAL EMAIL TEST ===');
console.log('');

// Setup AWS SES
const ses = new AWS.SES({ region: 'us-east-1' });

async function run() {
  const recipientEmail = process.argv[2] || 'terrance@goodportion.org';
  console.log('Step 1: Setting up email parameters');
  console.log(`  Recipient: ${recipientEmail}`);

  // Read the preview HTML that was already generated
  const previewPath = path.join(__dirname, '..', 'preview', 'eod-report-preview.html');

  let htmlContent;
  if (fs.existsSync(previewPath)) {
    console.log('Step 2: Loading preview HTML from disk');
    htmlContent = fs.readFileSync(previewPath, 'utf-8');
    console.log(`  HTML length: ${htmlContent.length} characters`);
  } else {
    console.log('Step 2: No preview found, using simple HTML');
    htmlContent = `
      <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
          <h1 style="color: #0891b2;">Email Assistant - Test Email</h1>
          <p>This is a test email from the redesigned email output system.</p>
          <p>If you received this, the SES email sending is working correctly!</p>
          <hr>
          <p style="color: #6b7280; font-size: 12px;">Sent at: ${new Date().toISOString()}</p>
        </body>
      </html>
    `;
  }

  const subject = `[TEST] Email Assistant - EOD Report Preview - ${new Date().toLocaleDateString()}`;

  console.log('Step 3: Sending via AWS SES...');

  const params = {
    Source: 'brandonhome.appdev@gmail.com',
    Destination: {
      ToAddresses: [recipientEmail]
    },
    Message: {
      Subject: {
        Data: subject,
        Charset: 'UTF-8'
      },
      Body: {
        Html: {
          Data: htmlContent,
          Charset: 'UTF-8'
        },
        Text: {
          Data: 'Please view this email in an HTML-capable email client.',
          Charset: 'UTF-8'
        }
      }
    }
  };

  try {
    const result = await ses.sendEmail(params).promise();
    console.log('');
    console.log('=== SUCCESS ===');
    console.log(`Message ID: ${result.MessageId}`);
    console.log(`Check your inbox at: ${recipientEmail}`);
    console.log('');
    process.exit(0);
  } catch (error) {
    console.log('');
    console.log('=== ERROR ===');
    console.log(`Error code: ${error.code}`);
    console.log(`Error message: ${error.message}`);
    console.log('');
    process.exit(1);
  }
}

run();

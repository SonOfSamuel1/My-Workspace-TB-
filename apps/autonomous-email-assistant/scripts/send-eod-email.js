#!/usr/bin/env node

/**
 * Send EOD Report Email
 * Uses AWS SES (preferred) or Gmail API to send the HTML email
 */

const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');
const EmailSummaryGenerator = require('../lib/email-summary-generator');
const SESEmailSender = require('../lib/ses-email-sender');

// Prefer SES unless explicitly disabled
const USE_SES = process.env.USE_SES !== 'false';

// Sample data (in production, this would come from the actual processing)
const sampleData = {
  todayStats: {
    totalProcessed: 47,
    escalations: 3,
    handled: 28,
    drafts: 8,
    flagged: 8,
    agentProcessed: 5,
    avgResponseTime: '2.3 min',
    accuracy: 94
  },
  actionsTaken: [
    { timestamp: Date.now() - 3600000, emailId: '18c4a2b3d4e5f6a7', subject: 'Q4 Revenue Report - Action Required', from: 'cfo@company.com', type: 'escalated' },
    { timestamp: Date.now() - 7200000, emailId: '18c4a2b3d4e5f6a8', subject: 'Meeting reschedule request', from: 'sarah.johnson@client.com', type: 'handled' },
    { timestamp: Date.now() - 10800000, emailId: '18c4a2b3d4e5f6a9', subject: 'Partnership proposal from TechCorp', from: 'partnerships@techcorp.io', type: 'drafted' },
    { timestamp: Date.now() - 14400000, emailId: '18c4a2b3d4e5f6b0', subject: 'Invoice #4521 - Payment Received', from: 'billing@vendor.com', type: 'archived' },
    { timestamp: Date.now() - 18000000, emailId: '18c4a2b3d4e5f6b1', subject: 'Re: Project timeline update', from: 'mike.chen@engineering.com', type: 'handled' },
    { timestamp: Date.now() - 21600000, emailId: '18c4a2b3d4e5f6b2', subject: 'URGENT: Server outage notification', from: 'alerts@infrastructure.com', type: 'escalated' },
    { timestamp: Date.now() - 25200000, emailId: '18c4a2b3d4e5f6b3', subject: 'Weekly team sync notes', from: 'team-lead@company.com', type: 'handled' },
    { timestamp: Date.now() - 28800000, emailId: '18c4a2b3d4e5f6b4', subject: 'Contract review - ABC Corp', from: 'legal@company.com', type: 'drafted' }
  ],
  pendingForTomorrow: [
    { subject: 'Follow up: Board presentation feedback', from: 'ceo@company.com', followUpDate: new Date(Date.now() + 86400000).toISOString() },
    { subject: 'Re: Budget approval for Q1 initiatives', from: 'finance@company.com', followUpDate: new Date(Date.now() + 86400000).toISOString() },
    { subject: 'Client onboarding - NewClient Inc', from: 'sales@company.com' },
    { subject: 'Performance review scheduling', from: 'hr@company.com' }
  ],
  costs: { claude: 0.0847, emailAgent: 0.0234, aws: 0.0012, twilio: 0.0225, total: 0.13, projection: true },
  insights: [
    { type: 'pattern', message: 'Email volume 23% higher than average today. Most emails came between 9-11 AM.', action: 'View patterns', actionUrl: 'https://email-assistant.yourdomain.com/analytics/patterns' },
    { type: 'performance', message: 'Classification accuracy improved to 94% this week (up from 89%).', action: 'Review accuracy', actionUrl: 'https://email-assistant.yourdomain.com/analytics/accuracy' },
    { type: 'cost', message: 'Daily cost under budget. Monthly projection: $3.90 (budget: $5.00)', action: 'Cost details', actionUrl: 'https://email-assistant.yourdomain.com/analytics/costs' },
    { type: 'recommendation', message: 'Consider adding "sarah.johnson@client.com" to VIP list - 12 emails this week.', action: 'Manage VIPs', actionUrl: 'https://email-assistant.yourdomain.com/settings/vip' },
    { type: 'success', message: 'Email Agent successfully completed 5 autonomous tasks today with 100% success rate.' }
  ],
  topSenders: [
    { email: 'team-updates@company.com', count: 8, averageTier: 'Tier 4' },
    { email: 'sarah.johnson@client.com', count: 5, averageTier: 'Tier 2' },
    { email: 'alerts@infrastructure.com', count: 4, averageTier: 'Tier 1' },
    { email: 'hr@company.com', count: 3, averageTier: 'Tier 3' },
    { email: 'finance@company.com', count: 3, averageTier: 'Tier 2' }
  ]
};

async function sendEmail() {
  const recipientEmail = process.argv[2] || 'terrance@goodportion.org';

  console.log('Generating EOD Report email...');

  // Generate email content
  const generator = new EmailSummaryGenerator({
    dashboardUrl: 'https://email-assistant.yourdomain.com/dashboard',
    userEmail: recipientEmail
  });

  const result = await generator.generateEODReport(sampleData);

  console.log(`Subject: ${result.subject}`);
  console.log(`Recipient: ${recipientEmail}`);

  // Use SES (preferred) or Gmail as fallback
  if (USE_SES) {
    console.log('\nUsing AWS SES for email delivery...');

    try {
      const sesSender = new SESEmailSender({
        region: process.env.AWS_REGION || 'us-east-1',
        senderEmail: process.env.SES_SENDER_EMAIL || 'brandonhome.appdev@gmail.com'
      });

      const sendResult = await sesSender.sendHtmlEmail({
        to: recipientEmail,
        subject: result.subject,
        htmlContent: result.html,
        textContent: result.plainText
      });

      console.log('✅ Email sent successfully via SES!');
      console.log(`Message ID: ${sendResult.messageId}`);

    } catch (error) {
      console.error('❌ Failed to send email via SES:', error.message);

      // Save to file as fallback
      const outputPath = path.join(__dirname, '..', 'preview', 'eod-report-to-send.html');
      fs.mkdirSync(path.dirname(outputPath), { recursive: true });
      fs.writeFileSync(outputPath, result.html);

      console.log(`\nEmail saved to: ${outputPath}`);
    }

    return;
  }

  // Gmail fallback
  const credentialsPath = process.env.GMAIL_CREDENTIALS_PATH ||
    path.join(process.env.HOME, '.gmail-mcp', 'credentials.json');
  const keysPath = process.env.GMAIL_KEYS_PATH ||
    path.join(process.env.HOME, '.gmail-mcp', 'gcp-oauth.keys.json');

  if (!fs.existsSync(credentialsPath) || !fs.existsSync(keysPath)) {
    console.log('\nGmail credentials not found. Saving email to file instead...');

    const outputPath = path.join(__dirname, '..', 'preview', 'eod-report-to-send.html');
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, result.html);

    console.log(`\nEmail saved to: ${outputPath}`);
    console.log('\nTo send manually:');
    console.log('1. Open Gmail');
    console.log('2. Compose new email');
    console.log(`3. To: ${recipientEmail}`);
    console.log(`4. Subject: ${result.subject}`);
    console.log('5. Click "Insert from file" or paste the HTML content');

    return;
  }

  try {
    // Load credentials
    const keys = JSON.parse(fs.readFileSync(keysPath, 'utf-8'));
    const credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf-8'));

    // Setup OAuth2 client
    const oauth2Client = new google.auth.OAuth2(
      keys.installed?.client_id || keys.web?.client_id,
      keys.installed?.client_secret || keys.web?.client_secret,
      keys.installed?.redirect_uris?.[0] || keys.web?.redirect_uris?.[0]
    );

    oauth2Client.setCredentials(credentials);

    // Create Gmail client
    const gmail = google.gmail({ version: 'v1', auth: oauth2Client });

    // Create the email message
    const message = [
      `To: ${recipientEmail}`,
      `Subject: ${result.subject}`,
      'MIME-Version: 1.0',
      'Content-Type: text/html; charset=utf-8',
      '',
      result.html
    ].join('\n');

    // Encode the message
    const encodedMessage = Buffer.from(message)
      .toString('base64')
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');

    // Send the email
    console.log('\nSending email via Gmail...');

    const response = await gmail.users.messages.send({
      userId: 'me',
      requestBody: {
        raw: encodedMessage
      }
    });

    console.log('✅ Email sent successfully!');
    console.log(`Message ID: ${response.data.id}`);
    console.log(`Thread ID: ${response.data.threadId}`);

  } catch (error) {
    console.error('❌ Failed to send email:', error.message);

    // Save to file as fallback
    const outputPath = path.join(__dirname, '..', 'preview', 'eod-report-to-send.html');
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, result.html);

    console.log(`\nEmail saved to: ${outputPath}`);
    console.log('You can open this file and copy/paste the content into Gmail.');
  }
}

sendEmail().catch(console.error);
#!/usr/bin/env node

/**
 * Simple Test Email Sender
 * Uses AWS SES only (no googleapis dependency)
 */

const fs = require('fs');
const path = require('path');
const EmailSummaryGenerator = require('../lib/email-summary-generator');
const SESEmailSender = require('../lib/ses-email-sender');

// Sample data for EOD report
const sampleData = {
  todayStats: {
    totalProcessed: 47,
    escalations: 3,
    handled: 28,
    drafts: 8,
    flagged: 8,
    agentProcessed: 5,
    avgResponseTime: '2.3 min',
    accuracy: 94,
    processedTrend: 12
  },
  actionsTaken: [
    { timestamp: Date.now() - 3600000, emailId: '18c4a2b3d4e5f6a7', subject: 'Q4 Revenue Report - Action Required', from: 'cfo@company.com', type: 'escalated' },
    { timestamp: Date.now() - 7200000, emailId: '18c4a2b3d4e5f6a8', subject: 'Meeting reschedule request', from: 'sarah.johnson@client.com', type: 'handled' },
    { timestamp: Date.now() - 10800000, emailId: '18c4a2b3d4e5f6a9', subject: 'Partnership proposal from TechCorp', from: 'partnerships@techcorp.io', type: 'drafted' },
    { timestamp: Date.now() - 14400000, emailId: '18c4a2b3d4e5f6b0', subject: 'Invoice #4521 - Payment Received', from: 'billing@vendor.com', type: 'archived' }
  ],
  pendingForTomorrow: [
    { subject: 'Follow up: Board presentation feedback', from: 'ceo@company.com', followUpDate: new Date(Date.now() + 86400000).toISOString() },
    { subject: 'Re: Budget approval for Q1 initiatives', from: 'finance@company.com', followUpDate: new Date(Date.now() + 86400000).toISOString() }
  ],
  costs: { claude: 0.0847, emailAgent: 0.0234, aws: 0.0012, twilio: 0.0225, total: 0.13, projection: true },
  insights: [
    { type: 'pattern', message: 'Email volume 23% higher than average today.' },
    { type: 'performance', message: 'Classification accuracy improved to 94% this week.' },
    { type: 'success', message: 'Email Agent successfully completed 5 autonomous tasks today.' }
  ],
  topSenders: [
    { email: 'team-updates@company.com', count: 8, averageTier: 'Tier 4' },
    { email: 'sarah.johnson@client.com', count: 5, averageTier: 'Tier 2' }
  ]
};

async function sendTestEmail() {
  const recipientEmail = process.argv[2] || 'terrance@goodportion.org';

  console.log('='.repeat(60));
  console.log('TEST EMAIL SENDER');
  console.log('='.repeat(60));
  console.log(`Recipient: ${recipientEmail}`);
  console.log('');

  try {
    // Generate email content
    console.log('1. Generating EOD Report email...');
    const generator = new EmailSummaryGenerator({
      dashboardUrl: 'https://email-assistant.yourdomain.com/dashboard',
      userEmail: recipientEmail
    });

    const result = await generator.generateEODReport(sampleData);
    console.log(`   Subject: ${result.subject}`);
    console.log('   HTML generated successfully');

    // Save to preview folder
    const outputDir = path.join(__dirname, '..', 'preview');
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    const htmlPath = path.join(outputDir, 'test-email-preview.html');
    fs.writeFileSync(htmlPath, result.html);
    console.log(`   Preview saved to: ${htmlPath}`);

    // Send via SES
    console.log('');
    console.log('2. Sending via AWS SES...');

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

    console.log('');
    console.log('='.repeat(60));
    console.log('SUCCESS!');
    console.log('='.repeat(60));
    console.log(`Message ID: ${sendResult.messageId}`);
    console.log(`Check your inbox at: ${recipientEmail}`);

  } catch (error) {
    console.error('');
    console.error('ERROR:', error.message);
    console.error('');
    console.error('Full error:', error);
    process.exit(1);
  }
}

sendTestEmail();

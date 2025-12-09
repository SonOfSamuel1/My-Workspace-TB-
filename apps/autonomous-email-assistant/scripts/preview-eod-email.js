#!/usr/bin/env node

/**
 * Preview End of Day Email
 * Generates and displays a sample EOD report email
 */

const EmailSummaryGenerator = require('../lib/email-summary-generator');
const fs = require('fs');
const path = require('path');

// Sample data for preview
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
    processedTrend: 12 // Show +12% trend indicator
  },

  actionsTaken: [
    {
      timestamp: Date.now() - 3600000,
      emailId: '18c4a2b3d4e5f6a7',
      subject: 'Q4 Revenue Report - Action Required',
      from: 'cfo@company.com',
      type: 'escalated'
    },
    {
      timestamp: Date.now() - 7200000,
      emailId: '18c4a2b3d4e5f6a8',
      subject: 'Meeting reschedule request',
      from: 'sarah.johnson@client.com',
      type: 'handled'
    },
    {
      timestamp: Date.now() - 10800000,
      emailId: '18c4a2b3d4e5f6a9',
      subject: 'Partnership proposal from TechCorp',
      from: 'partnerships@techcorp.io',
      type: 'drafted'
    },
    {
      timestamp: Date.now() - 14400000,
      emailId: '18c4a2b3d4e5f6b0',
      subject: 'Invoice #4521 - Payment Received',
      from: 'billing@vendor.com',
      type: 'archived'
    },
    {
      timestamp: Date.now() - 18000000,
      emailId: '18c4a2b3d4e5f6b1',
      subject: 'Re: Project timeline update',
      from: 'mike.chen@engineering.com',
      type: 'handled'
    },
    {
      timestamp: Date.now() - 21600000,
      emailId: '18c4a2b3d4e5f6b2',
      subject: 'URGENT: Server outage notification',
      from: 'alerts@infrastructure.com',
      type: 'escalated'
    },
    {
      timestamp: Date.now() - 25200000,
      emailId: '18c4a2b3d4e5f6b3',
      subject: 'Weekly team sync notes',
      from: 'team-lead@company.com',
      type: 'handled'
    },
    {
      timestamp: Date.now() - 28800000,
      emailId: '18c4a2b3d4e5f6b4',
      subject: 'Contract review - ABC Corp',
      from: 'legal@company.com',
      type: 'drafted'
    }
  ],

  pendingForTomorrow: [
    {
      subject: 'Follow up: Board presentation feedback',
      from: 'ceo@company.com',
      followUpDate: new Date(Date.now() + 86400000).toISOString()
    },
    {
      subject: 'Re: Budget approval for Q1 initiatives',
      from: 'finance@company.com',
      followUpDate: new Date(Date.now() + 86400000).toISOString()
    },
    {
      subject: 'Client onboarding - NewClient Inc',
      from: 'sales@company.com'
    },
    {
      subject: 'Performance review scheduling',
      from: 'hr@company.com'
    }
  ],

  costs: {
    claude: 0.0847,
    emailAgent: 0.0234,
    aws: 0.0012,
    twilio: 0.0225,
    total: 0.13,
    projection: true
  },

  insights: [
    {
      type: 'pattern',
      message: 'Email volume 23% higher than average today. Most emails came between 9-11 AM.',
      action: 'View patterns',
      actionUrl: 'https://email-assistant.yourdomain.com/analytics/patterns'
    },
    {
      type: 'performance',
      message: 'Classification accuracy improved to 94% this week (up from 89%).',
      action: 'Review accuracy',
      actionUrl: 'https://email-assistant.yourdomain.com/analytics/accuracy'
    },
    {
      type: 'cost',
      message: 'Daily cost under budget. Monthly projection: $3.90 (budget: $5.00)',
      action: 'Cost details',
      actionUrl: 'https://email-assistant.yourdomain.com/analytics/costs'
    },
    {
      type: 'recommendation',
      message: 'Consider adding "sarah.johnson@client.com" to VIP list - 12 emails this week.',
      action: 'Manage VIPs',
      actionUrl: 'https://email-assistant.yourdomain.com/settings/vip'
    },
    {
      type: 'success',
      message: 'Email Agent successfully completed 5 autonomous tasks today with 100% success rate.'
    }
  ],

  topSenders: [
    { email: 'team-updates@company.com', count: 8, averageTier: 'Tier 4' },
    { email: 'sarah.johnson@client.com', count: 5, averageTier: 'Tier 2' },
    { email: 'alerts@infrastructure.com', count: 4, averageTier: 'Tier 1' },
    { email: 'hr@company.com', count: 3, averageTier: 'Tier 3' },
    { email: 'finance@company.com', count: 3, averageTier: 'Tier 2' }
  ]
};

async function generatePreview() {
  console.log('Generating End of Day Report email preview...\n');

  const generator = new EmailSummaryGenerator({
    dashboardUrl: 'https://email-assistant.yourdomain.com/dashboard',
    userEmail: 'terrance@goodportion.org'
  });

  const result = await generator.generateEODReport(sampleData);

  // Save HTML file
  const outputDir = path.join(__dirname, '..', 'preview');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const htmlPath = path.join(outputDir, 'eod-report-preview.html');
  fs.writeFileSync(htmlPath, result.html);

  console.log('=' .repeat(60));
  console.log('END OF DAY REPORT EMAIL PREVIEW');
  console.log('=' .repeat(60));
  console.log(`\nSubject: ${result.subject}`);
  console.log(`\nHTML saved to: ${htmlPath}`);
  console.log('\nOpen this file in your browser to see the full preview.');
  console.log('\n' + '-'.repeat(60));
  console.log('PLAIN TEXT VERSION:');
  console.log('-'.repeat(60));
  console.log(result.plainText);

  // Also output the HTML directly if requested
  if (process.argv.includes('--html')) {
    console.log('\n' + '-'.repeat(60));
    console.log('HTML OUTPUT:');
    console.log('-'.repeat(60));
    console.log(result.html);
  }

  return result;
}

generatePreview().catch(console.error);
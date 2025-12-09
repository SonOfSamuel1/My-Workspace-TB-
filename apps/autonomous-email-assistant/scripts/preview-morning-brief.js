#!/usr/bin/env node

/**
 * Preview Morning Brief Email
 * Generates and displays a sample morning brief email
 */

const EmailSummaryGenerator = require('../lib/email-summary-generator');
const fs = require('fs');
const path = require('path');

// Sample data for preview
const sampleData = {
  overnight: {
    totalEmails: 15,
    handled: 10,
    escalations: 2,
    drafts: 3
  },

  tier1Escalations: [
    {
      id: '18c4a2b3d4e5f6a1',
      from: 'ceo@company.com',
      subject: 'URGENT: Board meeting prep - need your input by 9 AM',
      preview: 'Hi Terrance, I need your thoughts on the Q4 numbers before the board meeting. Can you review the attached deck and send me your comments?',
      timestamp: Date.now() - 3600000
    },
    {
      id: '18c4a2b3d4e5f6a2',
      from: 'alerts@infrastructure.com',
      subject: 'CRITICAL: Production database performance degradation',
      preview: 'Alert: Database response times have increased by 300%. Current latency is 2.5s. Immediate attention required.',
      timestamp: Date.now() - 7200000
    }
  ],

  tier3Pending: [
    {
      id: '18c4a2b3d4e5f6b1',
      from: 'partnerships@techcorp.io',
      subject: 'Partnership Proposal - Revenue Share Model',
      preview: 'We would like to propose a strategic partnership with the following terms...',
      draftPreview: 'Thank you for reaching out. I have reviewed your proposal and would like to schedule a call to discuss further.',
      timestamp: Date.now() - 10800000
    },
    {
      id: '18c4a2b3d4e5f6b2',
      from: 'legal@company.com',
      subject: 'Contract Amendment - ABC Corp',
      preview: 'Please review the attached contract amendment and provide your approval by EOD.',
      draftPreview: 'I have reviewed the contract amendment. I approve the changes as outlined.',
      timestamp: Date.now() - 14400000
    },
    {
      id: '18c4a2b3d4e5f6b3',
      from: 'hr@company.com',
      subject: 'New Hire Approval Request - Engineering Team',
      preview: 'We would like to proceed with extending an offer to the candidate from last week. Need your sign-off.',
      draftPreview: 'Approved. Please proceed with the offer as discussed.',
      timestamp: Date.now() - 18000000
    }
  ],

  tier2Handled: [
    {
      id: '18c4a2b3d4e5f6c1',
      from: 'team-updates@company.com',
      subject: 'Weekly Engineering Standup Notes',
      action: 'Archived and labeled',
      timestamp: Date.now() - 21600000
    },
    {
      id: '18c4a2b3d4e5f6c2',
      from: 'calendar@google.com',
      subject: 'Meeting invitation: 1:1 with Sarah',
      action: 'Auto-accepted and added to calendar',
      timestamp: Date.now() - 25200000
    },
    {
      id: '18c4a2b3d4e5f6c3',
      from: 'newsletters@techdigest.com',
      subject: 'Tech News Daily - Dec 3, 2025',
      action: 'Archived to Read Later folder',
      timestamp: Date.now() - 28800000
    },
    {
      id: '18c4a2b3d4e5f6c4',
      from: 'billing@vendor.com',
      subject: 'Invoice #4521 - Payment Confirmation',
      action: 'Filed to Finance folder',
      timestamp: Date.now() - 32400000
    },
    {
      id: '18c4a2b3d4e5f6c5',
      from: 'support@saas-tool.com',
      subject: 'Your support ticket #12345 has been resolved',
      action: 'Archived',
      timestamp: Date.now() - 36000000
    }
  ],

  stats: {
    responseTime: '1.2 min',
    accuracy: 96,
    timeSaved: 2.5,
    cost: 0.08
  },

  agentActivity: {
    processed: 3,
    tasksCompleted: 2,
    toolsUsed: ['calendar', 'gmail', 'data']
  }
};

async function generatePreview() {
  console.log('Generating Morning Brief email preview...\n');

  const generator = new EmailSummaryGenerator({
    dashboardUrl: 'https://email-assistant.yourdomain.com/dashboard',
    userEmail: 'terrance@goodportion.org'
  });

  const result = await generator.generateMorningBrief(sampleData);

  // Save HTML file
  const outputDir = path.join(__dirname, '..', 'preview');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const htmlPath = path.join(outputDir, 'morning-brief-preview.html');
  fs.writeFileSync(htmlPath, result.html);

  console.log('=' .repeat(60));
  console.log('MORNING BRIEF EMAIL PREVIEW');
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

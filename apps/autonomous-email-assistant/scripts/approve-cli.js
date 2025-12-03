#!/usr/bin/env node

/**
 * Email Assistant Approval CLI
 * Quick command-line tool for managing approvals
 *
 * Usage:
 *   ./approve-cli.js list              - List pending approvals
 *   ./approve-cli.js show <id>         - Show approval details
 *   ./approve-cli.js approve <id>      - Approve an item
 *   ./approve-cli.js reject <id>       - Reject an item
 *   ./approve-cli.js approve-all       - Approve all pending items
 *   ./approve-cli.js stats             - Show statistics
 *   ./approve-cli.js dashboard         - Show dashboard summary
 */

const ApprovalQueueManager = require('../lib/database/approval-queue');
const EmailStateManager = require('../lib/database/email-state');

// Initialize
const approvalQueue = new ApprovalQueueManager();
const emailState = new EmailStateManager();
const userEmail = process.env.USER_EMAIL || 'terrance@goodportion.org';

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  white: '\x1b[37m',
  bgRed: '\x1b[41m',
  bgGreen: '\x1b[42m',
  bgYellow: '\x1b[43m'
};

function color(text, colorCode) {
  return `${colorCode}${text}${colors.reset}`;
}

function header(text) {
  console.log('\n' + color('═'.repeat(60), colors.cyan));
  console.log(color(`  ${text}`, colors.bright + colors.cyan));
  console.log(color('═'.repeat(60), colors.cyan) + '\n');
}

function subheader(text) {
  console.log(color(`\n▶ ${text}`, colors.yellow));
  console.log(color('─'.repeat(40), colors.yellow));
}

function success(text) {
  console.log(color(`✓ ${text}`, colors.green));
}

function error(text) {
  console.log(color(`✗ ${text}`, colors.red));
}

function info(text) {
  console.log(color(`ℹ ${text}`, colors.blue));
}

function formatDate(timestamp) {
  return new Date(timestamp).toLocaleString('en-US', {
    timeZone: 'America/New_York',
    dateStyle: 'short',
    timeStyle: 'short'
  });
}

function truncate(str, len = 50) {
  if (!str) return '';
  return str.length > len ? str.substring(0, len) + '...' : str;
}

async function listApprovals() {
  header('Pending Approvals');

  const approvals = await approvalQueue.getPendingApprovals(userEmail, 50);

  if (approvals.length === 0) {
    info('No pending approvals');
    return;
  }

  console.log(color(`Found ${approvals.length} pending approval(s)\n`, colors.white));

  approvals.forEach((approval, index) => {
    const tierColor = {
      'TIER_1': colors.red,
      'TIER_2': colors.yellow,
      'TIER_3': colors.blue,
      'TIER_4': colors.white
    }[approval.tier] || colors.white;

    console.log(color(`[${index + 1}]`, colors.bright) + ` ${color(approval.approvalId.substring(0, 8), colors.cyan)}`);
    console.log(`    ${color('Type:', colors.white)} ${approval.type}`);
    console.log(`    ${color('Tier:', colors.white)} ${color(approval.tier || 'N/A', tierColor)}`);
    console.log(`    ${color('From:', colors.white)} ${truncate(approval.from, 40)}`);
    console.log(`    ${color('Subject:', colors.white)} ${truncate(approval.subject, 45)}`);
    console.log(`    ${color('Date:', colors.white)} ${formatDate(approval.timestamp)}`);
    console.log(`    ${color('Action:', colors.white)} ${approval.action || approval.actionType || 'N/A'}`);
    console.log('');
  });

  console.log(color('─'.repeat(60), colors.white));
  console.log(`\nTo approve: ${color('./approve-cli.js approve <id>', colors.cyan)}`);
  console.log(`To reject:  ${color('./approve-cli.js reject <id>', colors.cyan)}`);
  console.log(`To view:    ${color('./approve-cli.js show <id>', colors.cyan)}`);
}

async function showApproval(approvalId) {
  // Support partial ID match
  const approvals = await approvalQueue.getPendingApprovals(userEmail, 100);
  const approval = approvals.find(a =>
    a.approvalId === approvalId ||
    a.approvalId.startsWith(approvalId)
  ) || await approvalQueue.getApproval(approvalId);

  if (!approval) {
    error(`Approval not found: ${approvalId}`);
    return;
  }

  header('Approval Details');

  console.log(color('ID:', colors.bright) + ` ${approval.approvalId}`);
  console.log(color('Type:', colors.bright) + ` ${approval.type}`);
  console.log(color('Status:', colors.bright) + ` ${approval.status}`);
  console.log(color('Tier:', colors.bright) + ` ${approval.tier || 'N/A'}`);
  console.log(color('Created:', colors.bright) + ` ${formatDate(approval.timestamp)}`);

  subheader('Email Information');
  console.log(`From: ${approval.from}`);
  console.log(`To: ${approval.to}`);
  console.log(`Subject: ${approval.subject}`);
  console.log(`Thread ID: ${approval.threadId || 'N/A'}`);
  console.log(`Gmail: https://mail.google.com/mail/u/0/#inbox/${approval.emailId}`);

  if (approval.draftContent) {
    subheader('Draft Content');
    console.log(approval.draftContent);
  }

  if (approval.suggestedResponse) {
    subheader('Suggested Response');
    console.log(approval.suggestedResponse);
  }

  if (approval.agentRequest) {
    subheader('Agent Request');
    console.log(JSON.stringify(approval.agentRequest, null, 2));
  }

  if (approval.reasoning) {
    subheader('Reasoning');
    console.log(approval.reasoning);
  }

  if (approval.confidence) {
    subheader('Confidence');
    console.log(`${(approval.confidence * 100).toFixed(1)}%`);
  }

  console.log('\n' + color('─'.repeat(60), colors.white));
  console.log(`\nTo approve: ${color(`./approve-cli.js approve ${approval.approvalId.substring(0, 8)}`, colors.green)}`);
  console.log(`To reject:  ${color(`./approve-cli.js reject ${approval.approvalId.substring(0, 8)}`, colors.red)}`);
}

async function approveItem(approvalId, reason = '') {
  // Support partial ID match
  const approvals = await approvalQueue.getPendingApprovals(userEmail, 100);
  const approval = approvals.find(a =>
    a.approvalId === approvalId ||
    a.approvalId.startsWith(approvalId)
  );

  if (!approval) {
    error(`Approval not found: ${approvalId}`);
    return;
  }

  try {
    await approvalQueue.approve(approval.approvalId, {
      approvedBy: 'cli',
      notes: reason
    });

    success(`Approved: ${approval.subject}`);
    info(`ID: ${approval.approvalId}`);
  } catch (err) {
    error(`Failed to approve: ${err.message}`);
  }
}

async function rejectItem(approvalId, reason = '') {
  // Support partial ID match
  const approvals = await approvalQueue.getPendingApprovals(userEmail, 100);
  const approval = approvals.find(a =>
    a.approvalId === approvalId ||
    a.approvalId.startsWith(approvalId)
  );

  if (!approval) {
    error(`Approval not found: ${approvalId}`);
    return;
  }

  try {
    await approvalQueue.reject(approval.approvalId, reason);

    success(`Rejected: ${approval.subject}`);
    info(`ID: ${approval.approvalId}`);
  } catch (err) {
    error(`Failed to reject: ${err.message}`);
  }
}

async function approveAll() {
  const approvals = await approvalQueue.getPendingApprovals(userEmail, 100);

  if (approvals.length === 0) {
    info('No pending approvals');
    return;
  }

  header(`Approving ${approvals.length} Items`);

  const results = await approvalQueue.bulkApprove(
    approvals.map(a => a.approvalId),
    'cli-bulk'
  );

  success(`Approved: ${results.successful.length}`);
  if (results.failed.length > 0) {
    error(`Failed: ${results.failed.length}`);
    results.failed.forEach(f => {
      console.log(`  - ${f.approvalId}: ${f.error}`);
    });
  }
}

async function showStats() {
  header('Statistics');

  const stats = await approvalQueue.getStatistics(userEmail);

  console.log(color('Queue Status', colors.bright));
  console.log(`  Pending:  ${color(stats.pending.toString(), colors.yellow)}`);
  console.log(`  Approved: ${color(stats.approved.toString(), colors.green)}`);
  console.log(`  Rejected: ${color(stats.rejected.toString(), colors.red)}`);
  console.log(`  Total:    ${stats.total}`);

  console.log(`\n${color('Performance', colors.bright)}`);
  console.log(`  Approval Rate: ${stats.approvalRate}`);
  console.log(`  Avg Response Time: ${stats.averageResponseTime} minutes`);
  console.log(`  Oldest Pending: ${stats.oldestPending ? formatDate(new Date(stats.oldestPending)) : 'N/A'}`);

  if (Object.keys(stats.byType).length > 0) {
    console.log(`\n${color('By Type', colors.bright)}`);
    Object.entries(stats.byType).forEach(([type, count]) => {
      console.log(`  ${type}: ${count}`);
    });
  }

  if (Object.keys(stats.byTier).length > 0) {
    console.log(`\n${color('By Tier', colors.bright)}`);
    Object.entries(stats.byTier).forEach(([tier, count]) => {
      const tierColor = {
        'TIER_1': colors.red,
        'TIER_2': colors.yellow,
        'TIER_3': colors.blue,
        'TIER_4': colors.white
      }[tier] || colors.white;
      console.log(`  ${color(tier, tierColor)}: ${count}`);
    });
  }
}

async function showDashboard() {
  header('Dashboard Summary');

  const data = await emailState.getDashboardData(7);

  console.log(color('Period', colors.bright));
  console.log(`  ${data.period.start.split('T')[0]} to ${data.period.end.split('T')[0]} (${data.period.days} days)`);

  console.log(`\n${color('Email Metrics', colors.bright)}`);
  console.log(`  Total Processed: ${data.metrics.total}`);
  console.log(`  Unique Threads:  ${data.metrics.uniqueThreads}`);
  console.log(`  Response Rate:   ${data.metrics.responseRate}`);
  console.log(`  Agent Processed: ${data.metrics.agentProcessedRate}`);
  console.log(`  Peak Hour:       ${data.metrics.peakHour || 'N/A'}`);

  if (Object.keys(data.metrics.byTier).length > 0) {
    console.log(`\n${color('By Tier', colors.bright)}`);
    Object.entries(data.metrics.byTier).forEach(([tier, count]) => {
      const tierColor = {
        'TIER_1': colors.red,
        'TIER_2': colors.yellow,
        'TIER_3': colors.blue,
        'TIER_4': colors.white
      }[tier] || colors.white;
      console.log(`  ${color(tier, tierColor)}: ${count}`);
    });
  }

  if (data.recentEscalations.length > 0) {
    subheader('Recent Escalations');
    data.recentEscalations.slice(0, 5).forEach(email => {
      console.log(`  ${color('•', colors.red)} ${truncate(email.subject, 40)}`);
      console.log(`    From: ${truncate(email.from, 35)}`);
    });
  }

  console.log(`\n${color('Last Updated:', colors.white)} ${formatDate(new Date(data.lastUpdated))}`);
}

function showHelp() {
  header('Email Assistant Approval CLI');

  console.log('Usage: ./approve-cli.js <command> [options]\n');

  console.log(color('Commands:', colors.bright));
  console.log('  list              List all pending approvals');
  console.log('  show <id>         Show details for a specific approval');
  console.log('  approve <id>      Approve an item (supports partial ID)');
  console.log('  reject <id>       Reject an item (supports partial ID)');
  console.log('  approve-all       Approve all pending items');
  console.log('  stats             Show approval statistics');
  console.log('  dashboard         Show dashboard summary');
  console.log('  help              Show this help message');

  console.log(`\n${color('Examples:', colors.bright)}`);
  console.log('  ./approve-cli.js list');
  console.log('  ./approve-cli.js show abc123');
  console.log('  ./approve-cli.js approve abc');
  console.log('  ./approve-cli.js reject abc "Not needed"');

  console.log(`\n${color('Environment:', colors.bright)}`);
  console.log(`  USER_EMAIL: ${userEmail}`);
  console.log(`  AWS_REGION: ${process.env.AWS_REGION || 'us-east-1'}`);
}

// Main execution
async function main() {
  const args = process.argv.slice(2);
  const command = args[0] || 'help';

  try {
    switch (command) {
      case 'list':
      case 'ls':
        await listApprovals();
        break;

      case 'show':
      case 'view':
        if (!args[1]) {
          error('Please provide an approval ID');
          return;
        }
        await showApproval(args[1]);
        break;

      case 'approve':
      case 'yes':
      case 'y':
        if (!args[1]) {
          error('Please provide an approval ID');
          return;
        }
        await approveItem(args[1], args[2]);
        break;

      case 'reject':
      case 'no':
      case 'n':
        if (!args[1]) {
          error('Please provide an approval ID');
          return;
        }
        await rejectItem(args[1], args[2]);
        break;

      case 'approve-all':
      case 'all':
        await approveAll();
        break;

      case 'stats':
      case 'statistics':
        await showStats();
        break;

      case 'dashboard':
      case 'dash':
        await showDashboard();
        break;

      case 'help':
      case '--help':
      case '-h':
      default:
        showHelp();
    }
  } catch (err) {
    error(`Error: ${err.message}`);
    if (process.env.DEBUG) {
      console.error(err.stack);
    }
    process.exit(1);
  }
}

main();
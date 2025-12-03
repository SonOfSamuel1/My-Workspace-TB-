#!/usr/bin/env node

/**
 * Email Reply Poller
 *
 * Monitors Gmail for replies to the daily task review email.
 * Parses commands and executes appropriate actions.
 *
 * Commands supported:
 *   complete #3         - Mark task #3 as complete
 *   defer #2 tomorrow   - Reschedule task #2 to tomorrow
 *   defer #5 monday     - Reschedule task #5 to Monday
 *   break down #1       - Create subtasks for task #1
 *   breakdown #1        - Same as above
 *   help #4             - Get Claude guidance for task #4
 */

import 'dotenv/config';
import { google } from 'googleapis';
import path from 'path';
import fs from 'fs/promises';
import { fileURLToPath } from 'url';

import { completeTask } from './complete-task.js';
import { deferTask } from './defer-task.js';
import { breakdownTask } from './breakdown-task.js';
import { helpTask } from './help-task.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const USER_EMAIL = process.env.USER_EMAIL || process.env.TODOIST_REVIEW_EMAIL;
const TASK_MAPPINGS_FILE = path.join(__dirname, '..', 'data', 'task-mappings.json');
const PROCESSED_MESSAGES_FILE = path.join(__dirname, '..', 'data', 'processed-messages.json');

/**
 * Load Gmail OAuth client
 */
async function getGmailClient() {
  const credentialsPath = process.env.GMAIL_CREDENTIALS_PATH ||
    path.join(process.env.HOME, '.gmail-mcp', 'credentials.json');
  const tokenPath = process.env.GMAIL_TOKEN_PATH ||
    path.join(process.env.HOME, '.gmail-mcp', 'token.json');

  const credentials = JSON.parse(await fs.readFile(credentialsPath, 'utf8'));
  const { client_id, client_secret, redirect_uris } = credentials.installed || credentials.web;

  const oauth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);

  const token = JSON.parse(await fs.readFile(tokenPath, 'utf8'));
  oauth2Client.setCredentials(token);

  return google.gmail({ version: 'v1', auth: oauth2Client });
}

/**
 * Load task mappings from today's report
 */
async function loadTaskMappings() {
  try {
    const data = await fs.readFile(TASK_MAPPINGS_FILE, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.warn('No task mappings found. Generate a daily report first.');
    return {};
  }
}

/**
 * Load previously processed message IDs
 */
async function loadProcessedMessages() {
  try {
    const data = await fs.readFile(PROCESSED_MESSAGES_FILE, 'utf8');
    return new Set(JSON.parse(data));
  } catch (error) {
    return new Set();
  }
}

/**
 * Save processed message IDs
 */
async function saveProcessedMessages(processedSet) {
  await fs.mkdir(path.dirname(PROCESSED_MESSAGES_FILE), { recursive: true });
  await fs.writeFile(PROCESSED_MESSAGES_FILE, JSON.stringify([...processedSet]), 'utf8');
}

/**
 * Parse command from email body
 * Returns: { action, taskRef, dateString? }
 */
function parseCommand(text) {
  // Normalize text
  const normalized = text.toLowerCase().trim();

  // Command patterns
  const patterns = [
    // complete #3
    { regex: /complete\s+#?(\d+)/i, action: 'complete' },
    // done #3
    { regex: /done\s+#?(\d+)/i, action: 'complete' },
    // defer #2 tomorrow / defer #2 to monday
    { regex: /defer\s+#?(\d+)\s+(?:to\s+)?(.+)/i, action: 'defer' },
    // reschedule #2 to tomorrow
    { regex: /reschedule\s+#?(\d+)\s+(?:to\s+)?(.+)/i, action: 'defer' },
    // break down #1 / breakdown #1
    { regex: /break\s*down\s+#?(\d+)/i, action: 'breakdown' },
    // help #4 / help with #4
    { regex: /help\s+(?:with\s+)?#?(\d+)/i, action: 'help' },
  ];

  for (const { regex, action } of patterns) {
    const match = normalized.match(regex);
    if (match) {
      return {
        action,
        taskRef: parseInt(match[1], 10),
        dateString: match[2]?.trim() || null
      };
    }
  }

  return null;
}

/**
 * Get the body text from an email message
 */
function getEmailBody(payload) {
  // Check for plain text part
  if (payload.mimeType === 'text/plain') {
    return Buffer.from(payload.body.data, 'base64').toString('utf8');
  }

  // Check multipart
  if (payload.parts) {
    for (const part of payload.parts) {
      if (part.mimeType === 'text/plain') {
        return Buffer.from(part.body.data, 'base64').toString('utf8');
      }
      // Recurse into nested parts
      if (part.parts) {
        const nested = getEmailBody(part);
        if (nested) return nested;
      }
    }
  }

  // Fall back to HTML
  if (payload.mimeType === 'text/html') {
    const html = Buffer.from(payload.body.data, 'base64').toString('utf8');
    // Strip HTML tags (basic)
    return html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  }

  return '';
}

/**
 * Extract just the reply portion of an email (remove quoted text)
 */
function extractReplyText(body) {
  // Common reply markers
  const markers = [
    /^On .+ wrote:$/m,
    /^-+ ?Original Message ?-+$/m,
    /^From: /m,
    /^Sent: /m,
    /^>+ /m,
    /^_{10,}/m
  ];

  let text = body;

  for (const marker of markers) {
    const match = text.match(marker);
    if (match) {
      text = text.substring(0, match.index).trim();
    }
  }

  return text.trim();
}

/**
 * Send confirmation email
 */
async function sendConfirmation(gmail, to, subject, result) {
  const statusEmoji = result.success ? '✅' : '❌';
  const html = `
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
    .status { font-size: 48px; text-align: center; margin: 20px 0; }
    .message { background: ${result.success ? '#e8f5e9' : '#ffebee'}; padding: 20px; border-radius: 10px; }
    .details { background: #f5f5f5; padding: 15px; border-radius: 8px; margin-top: 15px; font-family: monospace; font-size: 13px; }
  </style>
</head>
<body>
  <div class="status">${statusEmoji}</div>
  <div class="message">
    <strong>${result.success ? 'Action Completed' : 'Action Failed'}</strong>
    <p>${result.message}</p>
  </div>
  ${result.subtasks ? `
  <div class="details">
    <strong>Subtasks created:</strong><br>
    ${result.subtasks.map((st, i) => `${i + 1}. ${st.content}`).join('<br>')}
  </div>
  ` : ''}
</body>
</html>`;

  const message = [
    'Content-Type: text/html; charset=utf-8',
    'MIME-Version: 1.0',
    `To: ${to}`,
    `Subject: =?UTF-8?B?${Buffer.from(subject).toString('base64')}?=`,
    '',
    html
  ].join('\r\n');

  const encodedMessage = Buffer.from(message)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');

  await gmail.users.messages.send({
    userId: 'me',
    requestBody: {
      raw: encodedMessage
    }
  });
}

/**
 * Execute the parsed command
 */
async function executeCommand(command, taskMappings) {
  const taskId = taskMappings[command.taskRef];

  if (!taskId) {
    return {
      success: false,
      message: `Task #${command.taskRef} not found in today's report. Valid tasks are #1 through #${Object.keys(taskMappings).length}.`
    };
  }

  try {
    switch (command.action) {
      case 'complete':
        return await completeTask(taskId);

      case 'defer':
        if (!command.dateString) {
          return {
            success: false,
            message: 'Please specify when to defer to (e.g., "defer #2 tomorrow")'
          };
        }
        return await deferTask(taskId, command.dateString);

      case 'breakdown':
        return await breakdownTask(taskId);

      case 'help':
        return await helpTask(taskId);

      default:
        return {
          success: false,
          message: `Unknown action: ${command.action}`
        };
    }
  } catch (error) {
    return {
      success: false,
      message: `Failed to execute ${command.action}: ${error.message}`
    };
  }
}

/**
 * Main polling function
 */
async function pollForReplies() {
  console.log(`[${new Date().toISOString()}] Polling for email replies...`);

  const gmail = await getGmailClient();
  const taskMappings = await loadTaskMappings();
  const processedMessages = await loadProcessedMessages();

  if (Object.keys(taskMappings).length === 0) {
    console.log('No task mappings available. Skipping poll.');
    return;
  }

  // Search for recent replies to daily task review emails
  const query = `subject:"Daily Task Review" is:inbox newer_than:1d`;

  const response = await gmail.users.messages.list({
    userId: 'me',
    q: query,
    maxResults: 20
  });

  const messages = response.data.messages || [];
  console.log(`Found ${messages.length} messages matching query`);

  let processedCount = 0;

  for (const msg of messages) {
    // Skip already processed messages
    if (processedMessages.has(msg.id)) {
      continue;
    }

    // Get full message
    const fullMessage = await gmail.users.messages.get({
      userId: 'me',
      id: msg.id,
      format: 'full'
    });

    // Check if this is a reply (not the original)
    const headers = fullMessage.data.payload.headers;
    const fromHeader = headers.find(h => h.name.toLowerCase() === 'from')?.value || '';
    const subjectHeader = headers.find(h => h.name.toLowerCase() === 'subject')?.value || '';

    // Skip if this is from the system (not a reply)
    if (!subjectHeader.toLowerCase().includes('re:')) {
      processedMessages.add(msg.id);
      continue;
    }

    // Get email body
    const body = getEmailBody(fullMessage.data.payload);
    const replyText = extractReplyText(body);

    console.log(`Processing reply: "${replyText.substring(0, 100)}..."`);

    // Parse command
    const command = parseCommand(replyText);

    if (command) {
      console.log(`Found command: ${command.action} #${command.taskRef}${command.dateString ? ` ${command.dateString}` : ''}`);

      // Execute command
      const result = await executeCommand(command, taskMappings);

      console.log(`Result: ${result.success ? 'SUCCESS' : 'FAILED'} - ${result.message}`);

      // Send confirmation email
      try {
        const confirmSubject = `${result.success ? '✅' : '❌'} Action: ${command.action} #${command.taskRef}`;
        await sendConfirmation(gmail, USER_EMAIL, confirmSubject, result);
        console.log('Confirmation email sent');
      } catch (emailError) {
        console.error('Failed to send confirmation:', emailError.message);
      }

      processedCount++;
    } else {
      console.log('No valid command found in reply');
    }

    // Mark as processed
    processedMessages.add(msg.id);
  }

  // Save processed messages
  await saveProcessedMessages(processedMessages);

  console.log(`Processed ${processedCount} command(s)`);
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  // Check for --watch flag for continuous polling
  const watchMode = process.argv.includes('--watch');

  if (watchMode) {
    const pollInterval = parseInt(process.env.POLL_INTERVAL_MS || '300000', 10); // 5 min default
    console.log(`Starting reply poller in watch mode (interval: ${pollInterval / 1000}s)`);

    // Initial poll
    pollForReplies().catch(console.error);

    // Continue polling
    setInterval(() => {
      pollForReplies().catch(console.error);
    }, pollInterval);
  } else {
    // Single poll
    pollForReplies()
      .then(() => {
        console.log('Poll complete');
      })
      .catch(error => {
        console.error('Poll failed:', error);
        process.exit(1);
      });
  }
}

export { pollForReplies, parseCommand, executeCommand };

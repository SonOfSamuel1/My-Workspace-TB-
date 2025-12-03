#!/usr/bin/env node

/**
 * Help Task Script
 *
 * Uses Claude Code CLI to provide detailed guidance on how to complete a task.
 * Sends the guidance via email.
 * Usage: node help-task.js <taskId>
 */

import 'dotenv/config';
import { spawn } from 'child_process';
import { google } from 'googleapis';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const TODOIST_API_TOKEN = process.env.TODOIST_API_TOKEN;
const TODOIST_API_URL = 'https://api.todoist.com/rest/v2';
const USER_EMAIL = process.env.USER_EMAIL || process.env.TODOIST_REVIEW_EMAIL;

/**
 * Fetch task details from Todoist
 */
async function getTask(taskId) {
  const response = await fetch(`${TODOIST_API_URL}/tasks/${taskId}`, {
    headers: {
      'Authorization': `Bearer ${TODOIST_API_TOKEN}`
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch task: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Run Claude Code CLI to get task guidance
 */
function getClaudeGuidance(task) {
  return new Promise((resolve, reject) => {
    const prompt = `Provide detailed, actionable guidance on how to complete this task:

Task: "${task.content}"
${task.description ? `Description: ${task.description}` : ''}
${task.due?.date ? `Due: ${task.due.date}` : ''}

Provide:
1. A brief summary of the approach (1-2 sentences)
2. Step-by-step instructions (5-10 steps)
3. Helpful resources or references
4. Pro tips or common pitfalls to avoid
5. Time estimate

Respond with ONLY valid JSON, no explanation:
{
  "summary": "Brief overview of the approach",
  "steps": ["Step 1: specific action", "Step 2: specific action", ...],
  "resources": ["Resource 1", "Resource 2", ...],
  "tips": ["Pro tip 1", "Pro tip 2", ...],
  "estimatedMinutes": 60,
  "additionalNotes": "Any other helpful information"
}`;

    const claude = spawn('claude', ['--print', '-p', prompt], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env }
    });

    let stdout = '';
    let stderr = '';

    claude.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    claude.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    claude.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Claude CLI exited with code ${code}: ${stderr}`));
      } else {
        try {
          const jsonMatch = stdout.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            resolve(JSON.parse(jsonMatch[0]));
          } else {
            reject(new Error('No JSON found in Claude response'));
          }
        } catch (parseError) {
          reject(new Error(`Failed to parse Claude response: ${parseError.message}`));
        }
      }
    });

    claude.on('error', (err) => {
      reject(new Error(`Failed to spawn Claude CLI: ${err.message}`));
    });

    setTimeout(() => {
      claude.kill();
      reject(new Error('Claude CLI timed out after 2 minutes'));
    }, 120000);
  });
}

/**
 * Generate HTML email with guidance
 */
function generateGuidanceEmail(task, guidance) {
  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 680px; margin: 0 auto; padding: 20px; }
    .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }
    .header h1 { margin: 0 0 10px 0; font-size: 24px; }
    .header p { margin: 0; opacity: 0.9; }
    .section { background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 15px; }
    .section h2 { color: #667eea; margin: 0 0 15px 0; font-size: 18px; }
    .summary { background: white; border-left: 4px solid #667eea; padding: 15px; margin-bottom: 20px; }
    .steps { counter-reset: step; }
    .step { background: white; padding: 12px 12px 12px 50px; margin-bottom: 8px; border-radius: 8px; position: relative; }
    .step::before { counter-increment: step; content: counter(step); position: absolute; left: 12px; top: 12px; background: #667eea; color: white; width: 24px; height: 24px; border-radius: 50%; text-align: center; line-height: 24px; font-weight: bold; font-size: 12px; }
    .tip { background: #fffaf0; border-left: 4px solid #ed8936; padding: 12px; margin-bottom: 8px; border-radius: 0 8px 8px 0; }
    .resource { background: #e8f5e9; padding: 10px; border-radius: 8px; margin-bottom: 8px; }
    .time-estimate { background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); color: white; padding: 15px; border-radius: 10px; text-align: center; }
    .time-estimate .time { font-size: 32px; font-weight: bold; }
    .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
    a { color: #667eea; }
  </style>
</head>
<body>
  <div class="header">
    <h1>Task Guidance</h1>
    <p>${task.content}</p>
  </div>

  <div class="summary">
    <strong>Summary:</strong> ${guidance.summary}
  </div>

  ${guidance.estimatedMinutes ? `
  <div class="time-estimate">
    <div class="time">${guidance.estimatedMinutes} min</div>
    <div>Estimated time to complete</div>
  </div>
  ` : ''}

  <div class="section">
    <h2>Step-by-Step Instructions</h2>
    <div class="steps">
      ${guidance.steps.map(step => `<div class="step">${step}</div>`).join('')}
    </div>
  </div>

  ${guidance.tips && guidance.tips.length > 0 ? `
  <div class="section">
    <h2>Pro Tips</h2>
    ${guidance.tips.map(tip => `<div class="tip">💡 ${tip}</div>`).join('')}
  </div>
  ` : ''}

  ${guidance.resources && guidance.resources.length > 0 ? `
  <div class="section">
    <h2>Helpful Resources</h2>
    ${guidance.resources.map(resource => `<div class="resource">📚 ${resource}</div>`).join('')}
  </div>
  ` : ''}

  ${guidance.additionalNotes ? `
  <div class="section">
    <h2>Additional Notes</h2>
    <p>${guidance.additionalNotes}</p>
  </div>
  ` : ''}

  <div class="footer">
    <p>Generated by Daily Todoist Reviewer</p>
    <p><a href="${task.url}">Open Task in Todoist</a></p>
  </div>
</body>
</html>`;
}

/**
 * Send email via Gmail API
 */
async function sendEmail(to, subject, htmlContent) {
  // Load credentials
  const credentialsPath = process.env.GMAIL_CREDENTIALS_PATH ||
    path.join(process.env.HOME, '.gmail-mcp', 'credentials.json');
  const tokenPath = process.env.GMAIL_TOKEN_PATH ||
    path.join(process.env.HOME, '.gmail-mcp', 'token.json');

  const { client_id, client_secret, redirect_uris } = JSON.parse(
    await import('fs').then(fs => fs.promises.readFile(credentialsPath, 'utf8'))
  ).installed || JSON.parse(
    await import('fs').then(fs => fs.promises.readFile(credentialsPath, 'utf8'))
  ).web;

  const oauth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);

  const token = JSON.parse(
    await import('fs').then(fs => fs.promises.readFile(tokenPath, 'utf8'))
  );
  oauth2Client.setCredentials(token);

  const gmail = google.gmail({ version: 'v1', auth: oauth2Client });

  // Create email message
  const message = [
    'Content-Type: text/html; charset=utf-8',
    'MIME-Version: 1.0',
    `To: ${to}`,
    `Subject: =?UTF-8?B?${Buffer.from(subject).toString('base64')}?=`,
    '',
    htmlContent
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
 * Main function to help with a task
 */
async function helpTask(taskId) {
  if (!taskId) {
    throw new Error('Task ID is required');
  }

  if (!TODOIST_API_TOKEN) {
    throw new Error('TODOIST_API_TOKEN environment variable is not set');
  }

  if (!USER_EMAIL) {
    throw new Error('USER_EMAIL environment variable is not set');
  }

  console.log(`Getting help for task ${taskId}...`);

  // Get the task details
  const task = await getTask(taskId);
  console.log(`Task: "${task.content}"`);

  // Get Claude's guidance
  console.log('Asking Claude for guidance...');
  const guidance = await getClaudeGuidance(task);
  console.log(`Claude provided ${guidance.steps.length} steps`);

  // Generate and send email
  const html = generateGuidanceEmail(task, guidance);
  const subject = `Task Guidance: ${task.content}`;

  console.log(`Sending guidance email to ${USER_EMAIL}...`);
  await sendEmail(USER_EMAIL, subject, html);

  return {
    success: true,
    taskId,
    taskContent: task.content,
    stepsProvided: guidance.steps.length,
    estimatedMinutes: guidance.estimatedMinutes,
    emailSent: true,
    message: `Guidance for "${task.content}" has been sent to ${USER_EMAIL}.`
  };
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  const taskId = process.argv[2];

  if (!taskId) {
    console.error('Usage: node help-task.js <taskId>');
    process.exit(1);
  }

  helpTask(taskId)
    .then(result => {
      console.log('\nSuccess:', result.message);
      console.log(`\nProvided ${result.stepsProvided} steps`);
      console.log(`Estimated time: ${result.estimatedMinutes || 'N/A'} minutes`);
    })
    .catch(error => {
      console.error('Error:', error.message);
      process.exit(1);
    });
}

export { helpTask };

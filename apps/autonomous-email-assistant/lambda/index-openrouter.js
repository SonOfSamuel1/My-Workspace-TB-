/**
 * Email Assistant Lambda - OpenRouter API Version
 *
 * Uses OpenRouter API for AI reasoning and Gmail API directly
 * No CLI dependencies - runs natively in Lambda
 */

const { google } = require('googleapis');
const https = require('https');

// Configuration
const CONFIG = {
  openRouter: {
    baseUrl: 'https://openrouter.ai/api/v1/chat/completions',
    model: process.env.OPENROUTER_MODEL || 'deepseek/deepseek-chat',
    fallbackModel: 'google/gemini-2.0-flash-exp:free'
  },
  gmail: {
    userId: 'me',
    maxResults: 50
  },
  escalation: {
    phone: process.env.ESCALATION_PHONE || '+14077448449'
  }
};

// Logger
const logger = {
  info: (msg, data) => console.log(JSON.stringify({ level: 'INFO', message: msg, ...data, timestamp: new Date().toISOString() })),
  error: (msg, data) => console.error(JSON.stringify({ level: 'ERROR', message: msg, ...data, timestamp: new Date().toISOString() })),
  warn: (msg, data) => console.warn(JSON.stringify({ level: 'WARN', message: msg, ...data, timestamp: new Date().toISOString() }))
};

/**
 * Get execution mode based on current EST hour
 */
function getExecutionMode() {
  const now = new Date();
  const estTime = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  const hour = estTime.getHours();

  if (hour === 7) return 'morning_brief';
  if (hour === 17) return 'eod_report';
  if (hour === 13) return 'midday_check';
  return 'hourly_process';
}

/**
 * Initialize Gmail API client
 */
function getGmailClient() {
  const credentials = JSON.parse(
    Buffer.from(process.env.GMAIL_OAUTH_CREDENTIALS, 'base64').toString()
  );
  const tokens = JSON.parse(
    Buffer.from(process.env.GMAIL_CREDENTIALS, 'base64').toString()
  );

  const oauth2Client = new google.auth.OAuth2(
    credentials.installed.client_id,
    credentials.installed.client_secret,
    credentials.installed.redirect_uris[0]
  );

  oauth2Client.setCredentials(tokens);

  return google.gmail({ version: 'v1', auth: oauth2Client });
}

/**
 * Fetch recent emails from Gmail
 */
async function fetchEmails(gmail, hoursBack = 1) {
  const after = Math.floor(Date.now() / 1000) - (hoursBack * 3600);
  const query = `after:${after} in:inbox`;

  try {
    const response = await gmail.users.messages.list({
      userId: CONFIG.gmail.userId,
      q: query,
      maxResults: CONFIG.gmail.maxResults
    });

    if (!response.data.messages) {
      return [];
    }

    const emails = await Promise.all(
      response.data.messages.map(async (msg) => {
        const full = await gmail.users.messages.get({
          userId: CONFIG.gmail.userId,
          id: msg.id,
          format: 'full'
        });
        return parseEmail(full.data);
      })
    );

    return emails;
  } catch (error) {
    logger.error('Failed to fetch emails', { error: error.message });
    throw error;
  }
}

/**
 * Parse email message into structured format
 */
function parseEmail(message) {
  const headers = message.payload.headers;
  const getHeader = (name) => headers.find(h => h.name.toLowerCase() === name.toLowerCase())?.value || '';

  let body = '';
  if (message.payload.body.data) {
    body = Buffer.from(message.payload.body.data, 'base64').toString();
  } else if (message.payload.parts) {
    const textPart = message.payload.parts.find(p => p.mimeType === 'text/plain');
    if (textPart && textPart.body.data) {
      body = Buffer.from(textPart.body.data, 'base64').toString();
    }
  }

  return {
    id: message.id,
    threadId: message.threadId,
    from: getHeader('From'),
    to: getHeader('To'),
    subject: getHeader('Subject'),
    date: getHeader('Date'),
    body: body.substring(0, 2000), // Truncate for context
    labels: message.labelIds || []
  };
}

/**
 * Call OpenRouter API
 */
async function callOpenRouter(prompt, model = CONFIG.openRouter.model) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({
      model: model,
      messages: [
        {
          role: 'system',
          content: `You are an Executive Email Assistant for Terrance Brandon.
You process emails and classify them into tiers:
- TIER 1: Escalate immediately (revenue-impacting, VIP contacts, urgent)
- TIER 2: Handle independently (routine scheduling, newsletters, admin)
- TIER 3: Draft for approval (strategic comms, declines)
- TIER 4: Flag only (HR, legal, personal)

Off-limits contacts (always TIER 1): Family Members, Darrell Coleman, Paul Robertson, Tatyana Brandon

Communication style: Casual (Hi/Thanks), sign with "Kind regards,", NO emojis.
Email: terrance@goodportion.org
Phone: 407-744-8449`
        },
        {
          role: 'user',
          content: prompt
        }
      ],
      max_tokens: 4000,
      temperature: 0.3
    });

    const options = {
      hostname: 'openrouter.ai',
      path: '/api/v1/chat/completions',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.OPENROUTER_API_KEY}`,
        'HTTP-Referer': 'https://github.com/SonOfSamuel1/email-assistant',
        'X-Title': 'Email Assistant Lambda'
      }
    };

    const req = https.request(options, (res) => {
      let responseData = '';
      res.on('data', chunk => responseData += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(responseData);
          if (parsed.error) {
            reject(new Error(parsed.error.message || 'OpenRouter API error'));
          } else {
            resolve(parsed.choices[0].message.content);
          }
        } catch (e) {
          reject(new Error(`Failed to parse response: ${responseData.substring(0, 200)}`));
        }
      });
    });

    req.on('error', reject);
    req.setTimeout(60000, () => {
      req.destroy();
      reject(new Error('OpenRouter request timeout'));
    });

    req.write(data);
    req.end();
  });
}

/**
 * Apply Gmail label to message
 */
async function applyLabel(gmail, messageId, labelName) {
  try {
    // Get or create label
    const labelsResponse = await gmail.users.labels.list({ userId: CONFIG.gmail.userId });
    let label = labelsResponse.data.labels.find(l => l.name === labelName);

    if (!label) {
      const created = await gmail.users.labels.create({
        userId: CONFIG.gmail.userId,
        requestBody: { name: labelName }
      });
      label = created.data;
    }

    await gmail.users.messages.modify({
      userId: CONFIG.gmail.userId,
      id: messageId,
      requestBody: {
        addLabelIds: [label.id]
      }
    });

    return true;
  } catch (error) {
    logger.error('Failed to apply label', { messageId, labelName, error: error.message });
    return false;
  }
}

/**
 * Send email via Gmail
 */
async function sendEmail(gmail, to, subject, body) {
  const message = [
    `To: ${to}`,
    `Subject: ${subject}`,
    'Content-Type: text/plain; charset=utf-8',
    '',
    body
  ].join('\n');

  const encodedMessage = Buffer.from(message)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');

  try {
    await gmail.users.messages.send({
      userId: CONFIG.gmail.userId,
      requestBody: { raw: encodedMessage }
    });
    return true;
  } catch (error) {
    logger.error('Failed to send email', { to, subject, error: error.message });
    return false;
  }
}

/**
 * Process emails and generate response
 */
async function processEmails(gmail, mode, emails) {
  if (emails.length === 0) {
    return {
      processed: 0,
      summary: 'No new emails to process.',
      actions: []
    };
  }

  // Build prompt for classification
  const emailSummaries = emails.map((e, i) =>
    `Email ${i + 1}:
    From: ${e.from}
    Subject: ${e.subject}
    Body preview: ${e.body.substring(0, 500)}...`
  ).join('\n\n');

  const prompt = `Process these ${emails.length} emails. For each email:
1. Classify into TIER 1/2/3/4
2. Determine appropriate action
3. Specify which Gmail label to apply

Current mode: ${mode}
Current time: ${new Date().toLocaleString('en-US', { timeZone: 'America/New_York' })}

${emailSummaries}

Respond in this JSON format:
{
  "classifications": [
    {
      "emailIndex": 1,
      "tier": 1,
      "reason": "...",
      "action": "escalate|handle|draft|flag",
      "label": "Action Required",
      "response": "draft response if tier 2 or 3"
    }
  ],
  "summary": "Brief summary of processing",
  "escalations": ["list of tier 1 items requiring immediate attention"]
}`;

  try {
    const aiResponse = await callOpenRouter(prompt);

    // Parse AI response
    let parsed;
    try {
      // Extract JSON from response
      const jsonMatch = aiResponse.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        parsed = JSON.parse(jsonMatch[0]);
      } else {
        throw new Error('No JSON found in response');
      }
    } catch (e) {
      logger.warn('Failed to parse AI response as JSON', { error: e.message });
      parsed = {
        classifications: [],
        summary: aiResponse.substring(0, 500),
        escalations: []
      };
    }

    // Apply labels based on classification
    const actions = [];
    for (const classification of parsed.classifications || []) {
      const email = emails[classification.emailIndex - 1];
      if (email && classification.label) {
        await applyLabel(gmail, email.id, classification.label);
        actions.push({
          emailId: email.id,
          subject: email.subject,
          tier: classification.tier,
          label: classification.label,
          action: classification.action
        });
      }
    }

    return {
      processed: emails.length,
      summary: parsed.summary || `Processed ${emails.length} emails`,
      escalations: parsed.escalations || [],
      actions
    };

  } catch (error) {
    logger.error('Failed to process emails with AI', { error: error.message });
    throw error;
  }
}

/**
 * Generate and send report based on mode
 */
async function sendReport(gmail, mode, result) {
  const now = new Date().toLocaleDateString('en-US', {
    timeZone: 'America/New_York',
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  let subject, body;

  switch (mode) {
    case 'morning_brief':
      subject = `Morning Brief - ${now}`;
      body = `Good morning,

Here's your email briefing:

SUMMARY
${result.summary}

EMAILS PROCESSED: ${result.processed}

${result.escalations.length > 0 ? `ESCALATIONS REQUIRING ATTENTION:
${result.escalations.map(e => `- ${e}`).join('\n')}` : 'No urgent escalations.'}

ACTIONS TAKEN:
${result.actions.map(a => `- [Tier ${a.tier}] ${a.subject} -> ${a.label}`).join('\n') || 'No actions taken.'}

Kind regards,
Executive Email Assistant`;
      break;

    case 'eod_report':
      subject = `End of Day Report - ${now}`;
      body = `Good evening,

Here's your end-of-day summary:

TOTAL PROCESSED: ${result.processed}

${result.summary}

ACTIONS TAKEN:
${result.actions.map(a => `- [Tier ${a.tier}] ${a.subject} -> ${a.action}`).join('\n') || 'No actions taken.'}

${result.escalations.length > 0 ? `PENDING ESCALATIONS:
${result.escalations.map(e => `- ${e}`).join('\n')}` : ''}

Kind regards,
Executive Email Assistant`;
      break;

    case 'midday_check':
      if (result.escalations.length === 0) {
        logger.info('No escalations for midday check, skipping report');
        return;
      }
      subject = `Midday Alert - Urgent Items`;
      body = `Attention required:

${result.escalations.map(e => `- ${e}`).join('\n')}

Kind regards,
Executive Email Assistant`;
      break;

    default:
      // hourly_process - only send if escalations
      if (result.escalations.length === 0) {
        logger.info('Hourly process complete, no report needed');
        return;
      }
      subject = `Urgent: Email Escalation`;
      body = `Immediate attention required:

${result.escalations.map(e => `- ${e}`).join('\n')}

Kind regards,
Executive Email Assistant`;
  }

  if (subject && body) {
    await sendEmail(gmail, 'terrance@goodportion.org', subject, body);
    logger.info('Report sent', { mode, subject });
  }
}

/**
 * Main Lambda handler
 */
exports.handler = async (event, context) => {
  const startTime = Date.now();

  logger.info('Email Assistant Lambda started', {
    functionName: context.functionName,
    mode: getExecutionMode(),
    event: JSON.stringify(event).substring(0, 200)
  });

  try {
    // Validate environment
    const required = ['GMAIL_OAUTH_CREDENTIALS', 'GMAIL_CREDENTIALS', 'OPENROUTER_API_KEY'];
    const missing = required.filter(key => !process.env[key]);
    if (missing.length > 0) {
      throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
    }

    // Get execution mode
    const mode = getExecutionMode();
    logger.info('Execution mode determined', { mode });

    // Initialize Gmail
    const gmail = getGmailClient();
    logger.info('Gmail client initialized');

    // Determine hours to look back
    const hoursBack = mode === 'morning_brief' ? 14 : 1; // Overnight for morning

    // Fetch emails
    const emails = await fetchEmails(gmail, hoursBack);
    logger.info('Emails fetched', { count: emails.length, hoursBack });

    // Process with AI
    const result = await processEmails(gmail, mode, emails);
    logger.info('Emails processed', {
      processed: result.processed,
      escalations: result.escalations.length
    });

    // Send report if needed
    await sendReport(gmail, mode, result);

    const duration = Date.now() - startTime;
    logger.info('Lambda completed successfully', {
      duration,
      processed: result.processed
    });

    return {
      statusCode: 200,
      body: JSON.stringify({
        success: true,
        mode,
        processed: result.processed,
        escalations: result.escalations.length,
        duration
      })
    };

  } catch (error) {
    const duration = Date.now() - startTime;
    logger.error('Lambda execution failed', {
      error: error.message,
      stack: error.stack,
      duration
    });

    return {
      statusCode: 500,
      body: JSON.stringify({
        success: false,
        error: error.message,
        duration
      })
    };
  }
};

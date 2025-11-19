/**
 * Example Integration Script
 *
 * This demonstrates how the parent CLI email processing system can sync
 * results with the web application database.
 *
 * Usage from parent project:
 * ```javascript
 * const { syncEmailsToWebApp } = require('./web/integration-helper.js');
 *
 * await syncEmailsToWebApp({
 *   agentEmail: 'assistant@yourdomain.com',
 *   emails: processedEmails
 * });
 * ```
 */

const fetch = require('node-fetch');

const WEB_APP_URL = process.env.WEB_APP_URL || 'http://localhost:3000';
const API_KEY = process.env.INTEGRATION_API_KEY;

/**
 * Sync processed emails to the web application
 */
async function syncEmailsToWebApp({ agentEmail, emails }) {
  try {
    const response = await fetch(`${WEB_APP_URL}/api/integration/sync`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
      body: JSON.stringify({
        agentEmail,
        emails: emails.map(email => ({
          gmailId: email.id,
          gmailThreadId: email.threadId,
          subject: email.subject,
          from: email.from,
          to: email.to,
          snippet: email.snippet,
          body: email.body,
          tier: email.tier,
          reasoning: email.reasoning,
          confidence: email.confidence,
          status: email.status,
          receivedAt: email.receivedAt.toISOString(),
          processedAt: email.processedAt?.toISOString(),
          actions: email.actions?.map(action => ({
            type: action.type,
            data: action.data,
            requiresApproval: action.requiresApproval,
            toolName: action.toolName,
            toolInput: action.toolInput,
            toolOutput: action.toolOutput,
            status: action.status,
          })),
        })),
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Sync failed: ${error.error}`);
    }

    const result = await response.json();
    console.log(`✓ Synced ${result.synced} emails to web app`);
    return result;
  } catch (error) {
    console.error('Failed to sync emails to web app:', error.message);
    // Don't throw - allow CLI to continue even if web app sync fails
    return null;
  }
}

/**
 * Get agent configuration from web app
 */
async function getAgentConfig(agentEmail) {
  try {
    const response = await fetch(
      `${WEB_APP_URL}/api/integration/sync?agentEmail=${encodeURIComponent(agentEmail)}`,
      {
        headers: {
          'X-API-Key': API_KEY,
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Failed to get config: ${error.error}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to get agent config:', error.message);
    return null;
  }
}

/**
 * Example usage
 */
async function example() {
  // Example 1: Sync emails after processing
  const processedEmails = [
    {
      id: 'gmail-msg-123',
      threadId: 'gmail-thread-456',
      subject: 'Meeting Request',
      from: 'client@example.com',
      to: 'assistant@yourdomain.com',
      snippet: 'Can we schedule a meeting next week?',
      body: 'Hi,\n\nCan we schedule a meeting next week to discuss the project?\n\nThanks!',
      tier: 3, // Draft
      reasoning: 'Meeting request requires scheduling coordination - creating draft for approval',
      confidence: 0.85,
      status: 'pending_approval',
      receivedAt: new Date(),
      processedAt: new Date(),
      actions: [
        {
          type: 'draft_created',
          data: {
            responseText: 'Thank you for reaching out. I\'d be happy to schedule a meeting...',
          },
          requiresApproval: true,
          status: 'pending',
        },
      ],
    },
  ];

  await syncEmailsToWebApp({
    agentEmail: 'assistant@yourdomain.com',
    emails: processedEmails,
  });

  // Example 2: Get agent configuration
  const config = await getAgentConfig('assistant@yourdomain.com');
  console.log('Agent config:', config);
}

module.exports = {
  syncEmailsToWebApp,
  getAgentConfig,
};

// Run example if executed directly
if (require.main === module) {
  example().catch(console.error);
}

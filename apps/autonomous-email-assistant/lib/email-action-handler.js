/**
 * Email Action Handler
 * Processes actions from email button clicks (approve, reject, snooze, archive)
 *
 * Integrates with Gmail API to execute actions on emails.
 */

const ActionTokenGenerator = require('./action-token-generator');
const logger = require('./logger');

class EmailActionHandler {
  constructor(config = {}) {
    this.tokenGenerator = new ActionTokenGenerator(config.secretKey);
    this.gmailClient = config.gmailClient || null;
    this.onAction = config.onAction || null; // Callback for custom action handling
    this.snoozeHours = config.snoozeHours || 2;

    // Label IDs (should be configured per-user)
    this.labels = {
      approved: config.labels?.approved || 'Email-Assistant/Approved',
      rejected: config.labels?.rejected || 'Email-Assistant/Rejected',
      snoozed: config.labels?.snoozed || 'Email-Assistant/Snoozed',
      archived: config.labels?.archived || null // null means just remove from inbox
    };
  }

  /**
   * Set Gmail client after initialization
   */
  setGmailClient(client) {
    this.gmailClient = client;
  }

  /**
   * Handle an action from a token
   * @param {string} token - The action token from email URL
   * @returns {object} Result of the action
   */
  async handleAction(token) {
    // Verify token
    const verification = this.tokenGenerator.verifyToken(token);

    if (!verification.valid) {
      logger.warn(`Action token verification failed: ${verification.error}`);
      return {
        success: false,
        error: verification.error,
        action: null
      };
    }

    const { emailId, action, userId, metadata } = verification;
    logger.info(`Processing action: ${action} for email ${emailId} by ${userId}`);

    try {
      let result;

      switch (action) {
        case 'approve':
          result = await this.approveEmail(emailId, userId, metadata);
          break;
        case 'reject':
          result = await this.rejectEmail(emailId, userId, metadata);
          break;
        case 'snooze':
          result = await this.snoozeEmail(emailId, userId, metadata);
          break;
        case 'archive':
          result = await this.archiveEmail(emailId, userId, metadata);
          break;
        case 'view':
          // View action just redirects to Gmail - no processing needed
          result = {
            success: true,
            action: 'view',
            redirectUrl: `https://mail.google.com/mail/u/0/#inbox/${emailId}`
          };
          break;
        default:
          result = { success: false, error: `Unknown action: ${action}` };
      }

      // Call custom handler if provided
      if (this.onAction && result.success) {
        await this.onAction({
          action,
          emailId,
          userId,
          metadata,
          result
        });
      }

      return {
        ...result,
        action,
        emailId
      };
    } catch (error) {
      logger.error(`Error handling action ${action} for email ${emailId}: ${error.message}`);
      return {
        success: false,
        error: error.message,
        action,
        emailId
      };
    }
  }

  /**
   * Approve an email (send draft response, label as approved)
   */
  async approveEmail(emailId, userId, metadata = {}) {
    if (!this.gmailClient) {
      return { success: false, error: 'Gmail client not configured' };
    }

    try {
      // If there's a draft ID in metadata, send the draft
      if (metadata?.draftId) {
        await this.gmailClient.users.drafts.send({
          userId: 'me',
          requestBody: {
            id: metadata.draftId
          }
        });
        logger.info(`Sent draft ${metadata.draftId} for email ${emailId}`);
      }

      // Apply approved label and remove from inbox
      await this.modifyLabels(emailId, {
        addLabels: [this.labels.approved],
        removeLabels: ['INBOX']
      });

      return {
        success: true,
        message: 'Email approved and draft sent',
        draftSent: !!metadata?.draftId
      };
    } catch (error) {
      throw new Error(`Failed to approve email: ${error.message}`);
    }
  }

  /**
   * Reject an email (delete draft if exists, label as rejected)
   */
  async rejectEmail(emailId, userId, metadata = {}) {
    if (!this.gmailClient) {
      return { success: false, error: 'Gmail client not configured' };
    }

    try {
      // If there's a draft ID in metadata, delete it
      if (metadata?.draftId) {
        try {
          await this.gmailClient.users.drafts.delete({
            userId: 'me',
            id: metadata.draftId
          });
          logger.info(`Deleted draft ${metadata.draftId}`);
        } catch (err) {
          // Draft may already be deleted, continue
          logger.warn(`Could not delete draft: ${err.message}`);
        }
      }

      // Apply rejected label and remove from inbox
      await this.modifyLabels(emailId, {
        addLabels: [this.labels.rejected],
        removeLabels: ['INBOX']
      });

      return {
        success: true,
        message: 'Email rejected and draft deleted',
        draftDeleted: !!metadata?.draftId
      };
    } catch (error) {
      throw new Error(`Failed to reject email: ${error.message}`);
    }
  }

  /**
   * Snooze an email (remove from inbox, add to snoozed, schedule reminder)
   */
  async snoozeEmail(emailId, userId, metadata = {}) {
    if (!this.gmailClient) {
      return { success: false, error: 'Gmail client not configured' };
    }

    const snoozeUntil = new Date(Date.now() + (this.snoozeHours * 60 * 60 * 1000));

    try {
      // Apply snoozed label and remove from inbox
      await this.modifyLabels(emailId, {
        addLabels: [this.labels.snoozed],
        removeLabels: ['INBOX']
      });

      // Note: Gmail API doesn't have native snooze support
      // This would need a separate scheduler to un-snooze
      // For now, we just label it and track when to un-snooze

      return {
        success: true,
        message: `Email snoozed until ${snoozeUntil.toLocaleString()}`,
        snoozeUntil: snoozeUntil.toISOString()
      };
    } catch (error) {
      throw new Error(`Failed to snooze email: ${error.message}`);
    }
  }

  /**
   * Archive an email (remove from inbox)
   */
  async archiveEmail(emailId, userId, metadata = {}) {
    if (!this.gmailClient) {
      return { success: false, error: 'Gmail client not configured' };
    }

    try {
      // Remove from inbox (this is what archive does in Gmail)
      await this.modifyLabels(emailId, {
        addLabels: this.labels.archived ? [this.labels.archived] : [],
        removeLabels: ['INBOX']
      });

      return {
        success: true,
        message: 'Email archived'
      };
    } catch (error) {
      throw new Error(`Failed to archive email: ${error.message}`);
    }
  }

  /**
   * Helper to modify labels on an email
   */
  async modifyLabels(emailId, { addLabels = [], removeLabels = [] }) {
    if (!this.gmailClient) {
      throw new Error('Gmail client not configured');
    }

    // Convert label names to IDs if needed
    const addLabelIds = await this.resolveLabelIds(addLabels);
    const removeLabelIds = await this.resolveLabelIds(removeLabels);

    await this.gmailClient.users.messages.modify({
      userId: 'me',
      id: emailId,
      requestBody: {
        addLabelIds: addLabelIds.filter(id => id),
        removeLabelIds: removeLabelIds.filter(id => id)
      }
    });
  }

  /**
   * Resolve label names to Gmail label IDs
   */
  async resolveLabelIds(labelNames) {
    const ids = [];

    for (const name of labelNames) {
      // System labels like INBOX can be used directly
      if (['INBOX', 'SPAM', 'TRASH', 'UNREAD', 'STARRED', 'IMPORTANT'].includes(name)) {
        ids.push(name);
        continue;
      }

      // For custom labels, we'd need to look them up
      // For simplicity, assuming label names match IDs or using a cache
      ids.push(name);
    }

    return ids;
  }

  /**
   * Generate a response page HTML for action completion
   */
  generateResponsePage(result) {
    const success = result.success;
    const action = result.action || 'action';

    const statusColor = success ? '#059669' : '#dc2626';
    const statusIcon = success ? '&#10003;' : '&#10005;';
    const statusText = success ? 'Success' : 'Error';
    const message = result.message || result.error || 'Action completed';

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Email Action - ${statusText}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f1f5f9;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .card {
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      padding: 40px;
      max-width: 400px;
      text-align: center;
    }
    .icon {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: ${statusColor};
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 32px;
      margin: 0 auto 20px;
    }
    h1 {
      color: #0f172a;
      font-size: 24px;
      margin-bottom: 12px;
    }
    p {
      color: #475569;
      font-size: 16px;
      line-height: 1.5;
      margin-bottom: 24px;
    }
    .action-badge {
      display: inline-block;
      background: ${statusColor}20;
      color: ${statusColor};
      padding: 4px 12px;
      border-radius: 16px;
      font-size: 14px;
      font-weight: 500;
      text-transform: capitalize;
      margin-bottom: 16px;
    }
    .button {
      display: inline-block;
      background: #0891b2;
      color: white;
      padding: 12px 24px;
      border-radius: 8px;
      text-decoration: none;
      font-weight: 500;
      transition: background 0.2s;
    }
    .button:hover {
      background: #0e7490;
    }
    .gmail-link {
      display: block;
      margin-top: 16px;
      color: #0891b2;
      text-decoration: none;
      font-size: 14px;
    }
    .gmail-link:hover {
      text-decoration: underline;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">${statusIcon}</div>
    <span class="action-badge">${action}</span>
    <h1>${statusText}</h1>
    <p>${message}</p>
    ${result.emailId ? `
      <a href="https://mail.google.com/mail/u/0/#inbox/${result.emailId}" class="button">
        View in Gmail
      </a>
    ` : ''}
    <a href="https://mail.google.com/mail/u/0/#inbox" class="gmail-link">
      Go to Inbox
    </a>
  </div>
  ${result.redirectUrl ? `
  <script>
    // Auto-redirect after 2 seconds if there's a redirect URL
    setTimeout(() => {
      window.location.href = '${result.redirectUrl}';
    }, 2000);
  </script>
  ` : ''}
</body>
</html>`;
  }
}

module.exports = EmailActionHandler;

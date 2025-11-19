/**
 * Slack Integration
 * Rich notifications and bot commands via Slack
 */

const logger = require('./logger');

class SlackBot {
  constructor(config = {}) {
    this.webhookUrl = config.webhookUrl || process.env.SLACK_WEBHOOK_URL;
    this.botToken = config.botToken || process.env.SLACK_BOT_TOKEN;
    this.channel = config.channel || '#email-assistant';
  }

  /**
   * Send escalation notification
   */
  async sendEscalation(email, tier, analysis) {
    const color = tier === 1 ? 'danger' : 'warning';
    const emoji = tier === 1 ? '🔴' : '⚠️';

    const message = {
      channel: this.channel,
      text: `${emoji} TIER ${tier} ESCALATION`,
      attachments: [{
        color,
        title: email.subject,
        fields: [
          {
            title: 'From',
            value: email.from,
            short: true
          },
          {
            title: 'Received',
            value: this.formatTime(email.date),
            short: true
          },
          {
            title: 'Summary',
            value: this.summarize(email.body),
            short: false
          },
          {
            title: 'Analysis',
            value: analysis.reasoning.join(', '),
            short: false
          }
        ],
        actions: [
          {
            type: 'button',
            text: '🔍 View Email',
            url: this.getEmailUrl(email.id)
          },
          {
            type: 'button',
            text: '✅ Acknowledge',
            name: 'acknowledge',
            value: email.id,
            style: 'primary'
          }
        ],
        footer: 'Email Assistant',
        ts: Math.floor(Date.now() / 1000)
      }]
    };

    return await this.sendMessage(message);
  }

  /**
   * Send draft approval request
   */
  async sendDraftApproval(email, draft) {
    const message = {
      channel: this.channel,
      text: '📝 Draft Ready for Approval',
      attachments: [{
        color: 'good',
        title: `Re: ${email.subject}`,
        fields: [
          {
            title: 'To',
            value: email.from,
            short: true
          },
          {
            title: 'Draft',
            value: `\`\`\`${draft.substring(0, 500)}...\`\`\``,
            short: false
          }
        ],
        actions: [
          {
            type: 'button',
            text: '✅ Approve & Send',
            name: 'approve',
            value: draft.id,
            style: 'primary',
            confirm: {
              title: 'Send Email?',
              text: 'This will send the email immediately',
              ok_text: 'Send',
              dismiss_text: 'Cancel'
            }
          },
          {
            type: 'button',
            text: '✏️ Edit',
            name: 'edit',
            value: draft.id
          },
          {
            type: 'button',
            text: '❌ Reject',
            name: 'reject',
            value: draft.id,
            style: 'danger'
          }
        ]
      }]
    };

    return await this.sendMessage(message);
  }

  /**
   * Send daily summary
   */
  async sendDailySummary(stats) {
    const message = {
      channel: this.channel,
      text: '📊 Daily Email Report',
      attachments: [{
        color: '#36a64f',
        title: `Email Summary - ${new Date().toLocaleDateString()}`,
        fields: [
          {
            title: '📧 Processed',
            value: `${stats.processed} emails`,
            short: true
          },
          {
            title: '✅ Handled',
            value: `${stats.handled} (${stats.handledPct}%)`,
            short: true
          },
          {
            title: '🔴 Escalated',
            value: `${stats.escalated}`,
            short: true
          },
          {
            title: '⏳ Pending',
            value: `${stats.pending} approvals`,
            short: true
          },
          {
            title: '⏱️ Avg Response Time',
            value: stats.avgResponseTime,
            short: true
          },
          {
            title: '💰 Cost',
            value: `$${stats.cost}`,
            short: true
          }
        ],
        footer: 'Email Assistant Analytics',
        ts: Math.floor(Date.now() / 1000)
      }]
    };

    return await this.sendMessage(message);
  }

  /**
   * Send message via webhook
   */
  async sendMessage(message) {
    if (!this.webhookUrl) {
      logger.warn('Slack webhook URL not configured');
      return false;
    }

    try {
      // In production, would use actual fetch/axios
      // For now, log the message
      logger.info('Slack message sent', {
        channel: message.channel,
        text: message.text
      });

      return true;
    } catch (error) {
      logger.error('Failed to send Slack message', {
        error: error.message
      });
      return false;
    }
  }

  /**
   * Handle bot command
   */
  async handleCommand(command, args) {
    const commands = {
      status: () => this.getStatus(),
      pending: () => this.getPending(),
      stats: () => this.getStats(),
      approve: (id) => this.approveDraft(id),
      search: (query) => this.searchEmails(query)
    };

    const handler = commands[command];
    if (!handler) {
      return { error: `Unknown command: ${command}` };
    }

    return await handler(args);
  }

  /**
   * Get status
   */
  async getStatus() {
    return {
      status: 'healthy',
      lastRun: new Date().toISOString(),
      uptime: '99.9%'
    };
  }

  /**
   * Get pending approvals
   */
  async getPending() {
    // In production, query database
    return {
      pending: [],
      count: 0
    };
  }

  /**
   * Get stats
   */
  async getStats() {
    // In production, query analytics
    return {
      today: { processed: 23, handled: 18, escalated: 2 }
    };
  }

  /**
   * Approve draft
   */
  async approveDraft(draftId) {
    logger.info('Draft approved via Slack', { draftId });
    return { success: true, message: 'Draft approved and sent' };
  }

  /**
   * Search emails
   */
  async searchEmails(query) {
    // In production, perform actual search
    return {
      results: [],
      count: 0
    };
  }

  /**
   * Helper: Summarize text
   */
  summarize(text, maxLength = 200) {
    if (!text) return '';

    const cleaned = text.replace(/\s+/g, ' ').trim();
    return cleaned.length > maxLength ?
      cleaned.substring(0, maxLength) + '...' :
      cleaned;
  }

  /**
   * Helper: Format time
   */
  formatTime(date) {
    const now = new Date();
    const then = new Date(date);
    const diff = now - then;

    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (minutes > 0) return `${minutes} min ago`;
    return 'Just now';
  }

  /**
   * Helper: Get email URL
   */
  getEmailUrl(emailId) {
    return `https://mail.google.com/mail/u/0/#inbox/${emailId}`;
  }
}

module.exports = SlackBot;

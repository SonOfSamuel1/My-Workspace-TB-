/**
 * Email Polling Mechanism
 * Monitors and processes emails sent to the assistant email address
 */

const logger = require('./logger');
const { google } = require('googleapis');
const fs = require('fs').promises;
const path = require('path');

class EmailPoller {
  constructor(config = {}) {
    this.assistantEmail = config.assistantEmail || process.env.AGENT_EMAIL || 'assistant@yourdomain.com';
    this.pollInterval = config.pollInterval || 60000; // 1 minute default
    this.processedIds = new Set();
    this.gmail = null;
    this.auth = null;
    this.polling = false;
    this.pollTimer = null;
    this.lastPollTime = null;
    this.maxResults = config.maxResults || 10;
    this.initialized = false;

    // Callback handlers
    this.onEmailReceived = config.onEmailReceived || null;
    this.onError = config.onError || null;

    // Statistics
    this.stats = {
      totalPolls: 0,
      emailsFound: 0,
      emailsProcessed: 0,
      errors: 0,
      lastError: null,
      startTime: Date.now()
    };
  }

  /**
   * Initialize Gmail API
   */
  async initialize() {
    if (this.initialized) return true;

    try {
      // Load credentials from environment or file
      const credentialsPath = process.env.GOOGLE_CREDENTIALS_PATH ||
                            path.join(process.env.HOME, '.gmail-mcp', 'gcp-oauth.keys.json');

      const tokenPath = process.env.GOOGLE_TOKEN_PATH ||
                       path.join(process.env.HOME, '.gmail-mcp', 'credentials.json');

      // Check if files exist
      try {
        await fs.access(credentialsPath);
        await fs.access(tokenPath);
      } catch (error) {
        logger.warn('Gmail credentials not found, email polling disabled', {
          credentialsPath,
          tokenPath
        });
        return false;
      }

      // Load credentials
      const credentials = JSON.parse(await fs.readFile(credentialsPath, 'utf-8'));
      const token = JSON.parse(await fs.readFile(tokenPath, 'utf-8'));

      // Create OAuth2 client
      const { client_id, client_secret } = credentials.installed || credentials.web;
      this.auth = new google.auth.OAuth2(client_id, client_secret, 'urn:ietf:wg:oauth:2.0:oob');
      this.auth.setCredentials(token);

      // Initialize Gmail API
      this.gmail = google.gmail({ version: 'v1', auth: this.auth });

      // Test connection
      await this.gmail.users.getProfile({ userId: 'me' });

      this.initialized = true;
      logger.info('Email poller initialized successfully', {
        assistantEmail: this.assistantEmail,
        pollInterval: this.pollInterval
      });

      return true;
    } catch (error) {
      logger.error('Failed to initialize email poller', {
        error: error.message
      });
      this.stats.errors++;
      this.stats.lastError = error.message;

      if (this.onError) {
        this.onError(error);
      }

      return false;
    }
  }

  /**
   * Start polling for emails
   */
  async start() {
    if (this.polling) {
      logger.warn('Email polling already active');
      return;
    }

    // Initialize if not already done
    const initialized = await this.initialize();
    if (!initialized) {
      logger.error('Cannot start polling - initialization failed');
      return;
    }

    this.polling = true;
    this.stats.startTime = Date.now();

    logger.info('Starting email polling', {
      assistantEmail: this.assistantEmail,
      interval: this.pollInterval
    });

    // Initial poll
    await this.poll();

    // Set up recurring poll
    this.pollTimer = setInterval(async () => {
      if (this.polling) {
        await this.poll();
      }
    }, this.pollInterval);
  }

  /**
   * Stop polling for emails
   */
  stop() {
    if (!this.polling) {
      return;
    }

    this.polling = false;

    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }

    logger.info('Email polling stopped', {
      stats: this.stats
    });
  }

  /**
   * Perform a single poll for new emails
   */
  async poll() {
    if (!this.initialized || !this.gmail) {
      logger.error('Cannot poll - Gmail not initialized');
      return;
    }

    try {
      this.stats.totalPolls++;
      const startTime = Date.now();

      // Build query for emails to/cc the assistant
      const queries = [
        `to:${this.assistantEmail}`,
        `cc:${this.assistantEmail}`,
        `bcc:${this.assistantEmail}`
      ];

      // Add time filter if we've polled before
      if (this.lastPollTime) {
        const afterDate = new Date(this.lastPollTime);
        afterDate.setSeconds(afterDate.getSeconds() - 30); // 30 second overlap
        const dateStr = afterDate.toISOString().split('T')[0];
        queries.push(`after:${dateStr}`);
      }

      const query = `(${queries.slice(0, 3).join(' OR ')}) is:unread ${queries.slice(3).join(' ')}`;

      logger.debug('Polling for emails', { query });

      // Search for messages
      const response = await this.gmail.users.messages.list({
        userId: 'me',
        q: query,
        maxResults: this.maxResults
      });

      const messages = response.data.messages || [];

      if (messages.length > 0) {
        logger.info('Found emails to process', { count: messages.length });
        this.stats.emailsFound += messages.length;

        // Process each message
        for (const message of messages) {
          // Skip if already processed
          if (this.processedIds.has(message.id)) {
            logger.debug('Skipping already processed email', { id: message.id });
            continue;
          }

          await this.processEmail(message.id);
        }
      }

      this.lastPollTime = Date.now();
      const duration = Date.now() - startTime;

      logger.debug('Poll completed', {
        duration,
        messagesFound: messages.length,
        totalProcessed: this.stats.emailsProcessed
      });
    } catch (error) {
      logger.error('Poll failed', {
        error: error.message
      });
      this.stats.errors++;
      this.stats.lastError = error.message;

      if (this.onError) {
        this.onError(error);
      }
    }
  }

  /**
   * Process a single email
   */
  async processEmail(messageId) {
    try {
      logger.info('Processing email', { messageId });

      // Get full message details
      const response = await this.gmail.users.messages.get({
        userId: 'me',
        id: messageId,
        format: 'full'
      });

      const message = response.data;

      // Extract email data
      const emailData = await this.extractEmailData(message);

      // Mark as processed
      this.processedIds.add(messageId);
      this.stats.emailsProcessed++;

      // Clean up old processed IDs if too many (keep last 1000)
      if (this.processedIds.size > 1000) {
        const idsArray = Array.from(this.processedIds);
        this.processedIds = new Set(idsArray.slice(-500));
      }

      // Mark as read
      await this.markAsRead(messageId);

      // Add label to indicate processing
      await this.addLabel(messageId, 'Email Agent Processing');

      // Call the callback if provided
      if (this.onEmailReceived) {
        logger.info('Triggering email handler', {
          from: emailData.from,
          subject: emailData.subject
        });

        await this.onEmailReceived(emailData, messageId);
      }

      return emailData;
    } catch (error) {
      logger.error('Failed to process email', {
        messageId,
        error: error.message
      });
      this.stats.errors++;
      this.stats.lastError = error.message;

      if (this.onError) {
        this.onError(error);
      }
    }
  }

  /**
   * Extract email data from Gmail message
   */
  async extractEmailData(message) {
    const headers = message.payload.headers || [];
    const getHeader = (name) => {
      const header = headers.find(h => h.name.toLowerCase() === name.toLowerCase());
      return header ? header.value : '';
    };

    // Extract basic headers
    const emailData = {
      id: message.id,
      threadId: message.threadId,
      from: getHeader('From'),
      to: getHeader('To'),
      cc: getHeader('Cc'),
      bcc: getHeader('Bcc'),
      subject: getHeader('Subject'),
      date: getHeader('Date'),
      messageId: getHeader('Message-Id'),
      inReplyTo: getHeader('In-Reply-To'),
      references: getHeader('References'),
      labels: message.labelIds || [],
      snippet: message.snippet
    };

    // Extract body
    const body = this.extractBody(message.payload);
    emailData.body = body.text || '';
    emailData.htmlBody = body.html || '';

    // Extract attachments
    emailData.attachments = this.extractAttachments(message.payload);

    // Parse sender details
    const fromMatch = emailData.from.match(/(.*?)\s*<(.+?)>/);
    if (fromMatch) {
      emailData.senderName = fromMatch[1].replace(/"/g, '').trim();
      emailData.senderEmail = fromMatch[2];
    } else {
      emailData.senderName = '';
      emailData.senderEmail = emailData.from;
    }

    // Determine if this is a direct request or CC
    emailData.isDirect = emailData.to.includes(this.assistantEmail);
    emailData.isCc = emailData.cc.includes(this.assistantEmail);
    emailData.isBcc = emailData.bcc.includes(this.assistantEmail);

    // Extract thread context if this is a reply
    if (emailData.threadId && emailData.inReplyTo) {
      emailData.threadContext = await this.getThreadContext(emailData.threadId, message.id);
    }

    return emailData;
  }

  /**
   * Extract body from message payload
   */
  extractBody(payload) {
    const body = { text: '', html: '' };

    const extractFromParts = (parts) => {
      if (!parts) return;

      for (const part of parts) {
        if (part.mimeType === 'text/plain' && part.body.data) {
          body.text = Buffer.from(part.body.data, 'base64').toString('utf-8');
        } else if (part.mimeType === 'text/html' && part.body.data) {
          body.html = Buffer.from(part.body.data, 'base64').toString('utf-8');
        } else if (part.parts) {
          extractFromParts(part.parts);
        }
      }
    };

    if (payload.parts) {
      extractFromParts(payload.parts);
    } else if (payload.body && payload.body.data) {
      const content = Buffer.from(payload.body.data, 'base64').toString('utf-8');
      if (payload.mimeType === 'text/html') {
        body.html = content;
      } else {
        body.text = content;
      }
    }

    // If no text body, try to extract from HTML
    if (!body.text && body.html) {
      // Simple HTML to text conversion (in production use a proper library)
      body.text = body.html
        .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
        .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
        .replace(/<br\s*\/?>/gi, '\n')
        .replace(/<\/p>/gi, '\n\n')
        .replace(/<\/div>/gi, '\n')
        .replace(/<[^>]+>/g, '')
        .replace(/&nbsp;/g, ' ')
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .trim();
    }

    return body;
  }

  /**
   * Extract attachments from message payload
   */
  extractAttachments(payload) {
    const attachments = [];

    const extractFromParts = (parts) => {
      if (!parts) return;

      for (const part of parts) {
        if (part.filename && part.body.attachmentId) {
          attachments.push({
            filename: part.filename,
            mimeType: part.mimeType,
            size: part.body.size,
            attachmentId: part.body.attachmentId
          });
        }

        if (part.parts) {
          extractFromParts(part.parts);
        }
      }
    };

    if (payload.parts) {
      extractFromParts(payload.parts);
    }

    return attachments;
  }

  /**
   * Get thread context for replies
   */
  async getThreadContext(threadId, currentMessageId) {
    try {
      const response = await this.gmail.users.threads.get({
        userId: 'me',
        id: threadId,
        format: 'minimal'
      });

      const thread = response.data;
      const messages = thread.messages || [];

      // Filter out current message and get last 3 messages for context
      const contextMessages = messages
        .filter(m => m.id !== currentMessageId)
        .slice(-3)
        .map(m => {
          const headers = m.payload.headers || [];
          const getHeader = (name) => {
            const header = headers.find(h => h.name.toLowerCase() === name.toLowerCase());
            return header ? header.value : '';
          };

          return {
            id: m.id,
            from: getHeader('From'),
            date: getHeader('Date'),
            snippet: m.snippet
          };
        });

      return {
        messageCount: messages.length,
        context: contextMessages
      };
    } catch (error) {
      logger.error('Failed to get thread context', {
        threadId,
        error: error.message
      });
      return null;
    }
  }

  /**
   * Mark email as read
   */
  async markAsRead(messageId) {
    try {
      await this.gmail.users.messages.modify({
        userId: 'me',
        id: messageId,
        requestBody: {
          removeLabelIds: ['UNREAD']
        }
      });

      logger.debug('Marked email as read', { messageId });
    } catch (error) {
      logger.error('Failed to mark as read', {
        messageId,
        error: error.message
      });
    }
  }

  /**
   * Add label to email
   */
  async addLabel(messageId, labelName) {
    try {
      // First, ensure the label exists
      const labelId = await this.ensureLabel(labelName);

      if (labelId) {
        await this.gmail.users.messages.modify({
          userId: 'me',
          id: messageId,
          requestBody: {
            addLabelIds: [labelId]
          }
        });

        logger.debug('Added label to email', { messageId, labelName });
      }
    } catch (error) {
      logger.error('Failed to add label', {
        messageId,
        labelName,
        error: error.message
      });
    }
  }

  /**
   * Ensure a label exists, create if not
   */
  async ensureLabel(labelName) {
    try {
      // List all labels
      const response = await this.gmail.users.labels.list({
        userId: 'me'
      });

      const labels = response.data.labels || [];
      const existingLabel = labels.find(l => l.name === labelName);

      if (existingLabel) {
        return existingLabel.id;
      }

      // Create new label
      const createResponse = await this.gmail.users.labels.create({
        userId: 'me',
        requestBody: {
          name: labelName,
          labelListVisibility: 'labelShow',
          messageListVisibility: 'show'
        }
      });

      logger.info('Created new Gmail label', { labelName });
      return createResponse.data.id;
    } catch (error) {
      logger.error('Failed to ensure label', {
        labelName,
        error: error.message
      });
      return null;
    }
  }

  /**
   * Send reply to an email
   */
  async sendReply(originalMessageId, replyContent) {
    try {
      // Get original message for threading
      const original = await this.gmail.users.messages.get({
        userId: 'me',
        id: originalMessageId,
        format: 'metadata',
        metadataHeaders: ['From', 'To', 'Subject', 'Message-Id', 'References']
      });

      const headers = original.data.payload.headers || [];
      const getHeader = (name) => {
        const header = headers.find(h => h.name === name);
        return header ? header.value : '';
      };

      const from = getHeader('From');
      const subject = getHeader('Subject');
      const messageId = getHeader('Message-Id');
      const references = getHeader('References');

      // Build reply
      const replySubject = subject.startsWith('Re:') ? subject : `Re: ${subject}`;
      const replyReferences = references ? `${references} ${messageId}` : messageId;

      const emailContent = [
        `To: ${from}`,
        `Subject: ${replySubject}`,
        `In-Reply-To: ${messageId}`,
        `References: ${replyReferences}`,
        '',
        replyContent
      ].join('\n');

      // Send reply
      const encodedMessage = Buffer.from(emailContent).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

      const response = await this.gmail.users.messages.send({
        userId: 'me',
        requestBody: {
          raw: encodedMessage,
          threadId: original.data.threadId
        }
      });

      logger.info('Sent reply', {
        originalMessageId,
        replyMessageId: response.data.id
      });

      return response.data;
    } catch (error) {
      logger.error('Failed to send reply', {
        originalMessageId,
        error: error.message
      });
      throw error;
    }
  }

  /**
   * Get poller statistics
   */
  getStats() {
    const runtime = Date.now() - this.stats.startTime;
    const avgPollTime = this.stats.totalPolls > 0 ? runtime / this.stats.totalPolls : 0;

    return {
      ...this.stats,
      runtime,
      avgPollTime,
      isPolling: this.polling,
      lastPollTime: this.lastPollTime,
      processedCount: this.processedIds.size
    };
  }

  /**
   * Reset statistics
   */
  resetStats() {
    this.stats = {
      totalPolls: 0,
      emailsFound: 0,
      emailsProcessed: 0,
      errors: 0,
      lastError: null,
      startTime: Date.now()
    };
  }

  /**
   * Check if polling is active
   */
  isPolling() {
    return this.polling;
  }

  /**
   * Force a poll immediately
   */
  async forcePoll() {
    logger.info('Forcing immediate poll');
    await this.poll();
  }
}

module.exports = EmailPoller;
module.exports.EmailPoller = EmailPoller;
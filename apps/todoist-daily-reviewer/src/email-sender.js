/**
 * Email Sender - Sends HTML reports via Gmail API
 *
 * Handles Gmail API authentication and email delivery.
 */

import { google } from 'googleapis';
import fs from 'fs';
import path from 'path';

/**
 * Email Sender class
 */
export class EmailSender {
  constructor(options = {}) {
    this.credentialsPath = options.credentialsPath || process.env.GOOGLE_CREDENTIALS_FILE;
    this.tokenPath = options.tokenPath || process.env.GOOGLE_TOKEN_FILE;
    this.gmail = null;
    this.initialized = false;
  }

  /**
   * Initialize Gmail API client
   */
  async initialize() {
    if (this.initialized) return;

    try {
      // Load credentials
      const credentials = await this.loadCredentials();

      // Create OAuth2 client
      const { client_secret, client_id, redirect_uris } = credentials.installed || credentials.web;
      const oAuth2Client = new google.auth.OAuth2(
        client_id,
        client_secret,
        redirect_uris ? redirect_uris[0] : 'http://localhost'
      );

      // Load saved token
      const token = await this.loadToken();
      oAuth2Client.setCredentials(token);

      // Create Gmail client
      this.gmail = google.gmail({ version: 'v1', auth: oAuth2Client });
      this.initialized = true;

      console.log('Gmail API initialized successfully');
    } catch (error) {
      console.error('Failed to initialize Gmail API:', error.message);
      throw error;
    }
  }

  /**
   * Load OAuth credentials
   */
  async loadCredentials() {
    // Check for base64 encoded credentials (Lambda environment)
    if (process.env.GMAIL_OAUTH_CREDENTIALS) {
      const decoded = Buffer.from(process.env.GMAIL_OAUTH_CREDENTIALS, 'base64').toString('utf-8');
      return JSON.parse(decoded);
    }

    // Load from file
    if (!this.credentialsPath) {
      throw new Error('No credentials path specified');
    }

    const content = fs.readFileSync(this.credentialsPath, 'utf-8');
    return JSON.parse(content);
  }

  /**
   * Load saved OAuth token
   */
  async loadToken() {
    // Check for base64 encoded token (Lambda environment)
    if (process.env.GMAIL_CREDENTIALS) {
      const decoded = Buffer.from(process.env.GMAIL_CREDENTIALS, 'base64').toString('utf-8');
      return JSON.parse(decoded);
    }

    // Load from file
    if (!this.tokenPath) {
      throw new Error('No token path specified');
    }

    const content = fs.readFileSync(this.tokenPath, 'utf-8');
    return JSON.parse(content);
  }

  /**
   * Send HTML email
   */
  async sendHtmlEmail(options) {
    const { to, subject, htmlContent, from } = options;

    if (!this.initialized) {
      await this.initialize();
    }

    // Build email
    const email = this.buildEmail({
      to,
      subject,
      htmlContent,
      from: from || 'me'
    });

    // Encode to base64url
    const encodedEmail = Buffer.from(email)
      .toString('base64')
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');

    try {
      const response = await this.gmail.users.messages.send({
        userId: 'me',
        requestBody: {
          raw: encodedEmail
        }
      });

      console.log(`Email sent successfully. Message ID: ${response.data.id}`);
      return {
        success: true,
        messageId: response.data.id,
        threadId: response.data.threadId
      };
    } catch (error) {
      console.error('Failed to send email:', error.message);
      throw error;
    }
  }

  /**
   * Build MIME email message
   */
  buildEmail({ to, subject, htmlContent, from }) {
    const boundary = 'boundary_' + Date.now().toString(16);

    const emailLines = [
      `From: ${from}`,
      `To: ${to}`,
      `Subject: ${subject}`,
      'MIME-Version: 1.0',
      `Content-Type: multipart/alternative; boundary="${boundary}"`,
      '',
      `--${boundary}`,
      'Content-Type: text/plain; charset="UTF-8"',
      'Content-Transfer-Encoding: quoted-printable',
      '',
      this.htmlToPlainText(htmlContent),
      '',
      `--${boundary}`,
      'Content-Type: text/html; charset="UTF-8"',
      'Content-Transfer-Encoding: quoted-printable',
      '',
      htmlContent,
      '',
      `--${boundary}--`
    ];

    return emailLines.join('\r\n');
  }

  /**
   * Convert HTML to plain text (basic conversion)
   */
  htmlToPlainText(html) {
    return html
      // Remove style and script tags with their contents
      .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
      // Replace common elements
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/p>/gi, '\n\n')
      .replace(/<\/div>/gi, '\n')
      .replace(/<\/h[1-6]>/gi, '\n\n')
      .replace(/<li>/gi, '  - ')
      .replace(/<\/li>/gi, '\n')
      // Remove all remaining HTML tags
      .replace(/<[^>]+>/g, '')
      // Decode HTML entities
      .replace(/&nbsp;/g, ' ')
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/&#039;/g, "'")
      // Clean up whitespace
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }

  /**
   * Validate credentials without sending
   */
  async validateCredentials() {
    try {
      await this.initialize();

      // Try to get user profile to verify credentials work
      const response = await this.gmail.users.getProfile({ userId: 'me' });

      return {
        valid: true,
        email: response.data.emailAddress,
        messagesTotal: response.data.messagesTotal
      };
    } catch (error) {
      return {
        valid: false,
        error: error.message
      };
    }
  }
}

/**
 * Simple email sender for Lambda (without file dependencies)
 */
export class LambdaEmailSender {
  constructor() {
    this.gmail = null;
  }

  /**
   * Initialize with credentials from environment
   */
  async initialize() {
    if (this.gmail) return;

    // Get credentials from environment
    const oauthCreds = JSON.parse(
      Buffer.from(process.env.GMAIL_OAUTH_CREDENTIALS, 'base64').toString('utf-8')
    );
    const userCreds = JSON.parse(
      Buffer.from(process.env.GMAIL_CREDENTIALS, 'base64').toString('utf-8')
    );

    // Create OAuth2 client
    const { client_secret, client_id, redirect_uris } = oauthCreds.installed || oauthCreds.web;
    const oAuth2Client = new google.auth.OAuth2(
      client_id,
      client_secret,
      redirect_uris ? redirect_uris[0] : 'http://localhost'
    );

    oAuth2Client.setCredentials(userCreds);
    this.gmail = google.gmail({ version: 'v1', auth: oAuth2Client });
  }

  /**
   * Send HTML email
   */
  async send(to, subject, htmlContent) {
    await this.initialize();

    const boundary = 'boundary_' + Date.now().toString(16);
    const email = [
      `To: ${to}`,
      `Subject: ${subject}`,
      'MIME-Version: 1.0',
      `Content-Type: text/html; charset="UTF-8"`,
      '',
      htmlContent
    ].join('\r\n');

    const encodedEmail = Buffer.from(email)
      .toString('base64')
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');

    const response = await this.gmail.users.messages.send({
      userId: 'me',
      requestBody: { raw: encodedEmail }
    });

    return response.data;
  }
}

export default EmailSender;

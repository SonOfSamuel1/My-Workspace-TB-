/**
 * AWS SES Email Sender - Sends HTML reports via AWS SES
 *
 * Replaces Gmail API for more reliable automated email delivery.
 * Benefits:
 * - No OAuth token expiration issues
 * - Native AWS Lambda integration
 * - Cost effective (~$0.10 per 1000 emails)
 * - Simpler IAM-based credential management
 */

import { SESClient, SendEmailCommand, GetSendQuotaCommand } from '@aws-sdk/client-ses';

/**
 * SES Email Sender class
 */
export class SESEmailSender {
  constructor(options = {}) {
    this.region = options.region || process.env.AWS_REGION || 'us-east-1';
    this.senderEmail = options.senderEmail || process.env.SES_SENDER_EMAIL || 'brandonhome.appdev@gmail.com';

    this.client = new SESClient({ region: this.region });

    console.log(`SES Email Sender initialized (region: ${this.region}, sender: ${this.senderEmail})`);
  }

  /**
   * Send HTML email via AWS SES
   */
  async sendHtmlEmail(options) {
    const { to, subject, htmlContent, textContent } = options;

    const params = {
      Source: this.senderEmail,
      Destination: {
        ToAddresses: [to]
      },
      Message: {
        Subject: {
          Data: subject,
          Charset: 'UTF-8'
        },
        Body: {
          Html: {
            Data: htmlContent,
            Charset: 'UTF-8'
          },
          Text: {
            Data: textContent || this.htmlToPlainText(htmlContent),
            Charset: 'UTF-8'
          }
        }
      }
    };

    try {
      const command = new SendEmailCommand(params);
      const response = await this.client.send(command);

      console.log(`Email sent successfully! Message ID: ${response.MessageId}`);
      console.log(`  To: ${to}`);
      console.log(`  Subject: ${subject}`);

      return {
        success: true,
        messageId: response.MessageId
      };
    } catch (error) {
      console.error(`SES send failed: ${error.name} - ${error.message}`);

      if (error.name === 'MessageRejected') {
        console.error('Message rejected - check sender/recipient verification');
      } else if (error.name === 'MailFromDomainNotVerifiedError') {
        console.error(`Sender domain not verified: ${this.senderEmail}`);
      }

      throw error;
    }
  }

  /**
   * Validate SES credentials and permissions
   */
  async validateCredentials() {
    try {
      const command = new GetSendQuotaCommand({});
      const response = await this.client.send(command);

      console.log('SES credentials validated successfully');
      console.log(`  Send quota: ${response.SentLast24Hours}/${response.Max24HourSend} (24hr)`);
      console.log(`  Max send rate: ${response.MaxSendRate} emails/sec`);

      return {
        valid: true,
        quota: {
          max24HourSend: response.Max24HourSend,
          sentLast24Hours: response.SentLast24Hours,
          maxSendRate: response.MaxSendRate
        }
      };
    } catch (error) {
      console.error(`SES credential validation failed: ${error.message}`);
      return {
        valid: false,
        error: error.message
      };
    }
  }

  /**
   * Convert HTML to plain text for email fallback
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
}

/**
 * Simple SES sender for Lambda (stateless)
 */
export class LambdaSESEmailSender {
  constructor() {
    this.region = process.env.AWS_REGION || 'us-east-1';
    this.senderEmail = process.env.SES_SENDER_EMAIL || 'brandonhome.appdev@gmail.com';
    this.client = new SESClient({ region: this.region });
  }

  async send(to, subject, htmlContent) {
    const params = {
      Source: this.senderEmail,
      Destination: { ToAddresses: [to] },
      Message: {
        Subject: { Data: subject, Charset: 'UTF-8' },
        Body: {
          Html: { Data: htmlContent, Charset: 'UTF-8' }
        }
      }
    };

    const command = new SendEmailCommand(params);
    const response = await this.client.send(command);

    return {
      messageId: response.MessageId
    };
  }
}

export default SESEmailSender;

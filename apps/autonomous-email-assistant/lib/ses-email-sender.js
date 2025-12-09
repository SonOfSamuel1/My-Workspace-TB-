/**
 * AWS SES Email Sender
 *
 * Sends HTML emails via AWS SES for reliable automated email delivery.
 * Benefits:
 * - No OAuth token expiration issues
 * - Native AWS Lambda integration
 * - Cost effective (~$0.10 per 1000 emails)
 * - Simpler IAM-based credential management
 */

const AWS = require('aws-sdk');
const logger = require('./logger');

class SESEmailSender {
  constructor(options = {}) {
    this.region = options.region || process.env.AWS_REGION || 'us-east-1';
    this.senderEmail = options.senderEmail || process.env.SES_SENDER_EMAIL || 'brandonhome.appdev@gmail.com';

    this.ses = new AWS.SES({ region: this.region });

    logger.info(`SES Email Sender initialized (region: ${this.region}, sender: ${this.senderEmail})`);
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
      const result = await this.ses.sendEmail(params).promise();

      logger.info(`Email sent successfully! Message ID: ${result.MessageId}`);
      logger.info(`  To: ${to}`);
      logger.info(`  Subject: ${subject}`);

      return {
        success: true,
        messageId: result.MessageId
      };
    } catch (error) {
      logger.error(`SES send failed: ${error.code} - ${error.message}`);

      if (error.code === 'MessageRejected') {
        logger.error('Message rejected - check sender/recipient verification');
      } else if (error.code === 'MailFromDomainNotVerified') {
        logger.error(`Sender domain not verified: ${this.senderEmail}`);
      }

      throw error;
    }
  }

  /**
   * Validate SES credentials and permissions
   */
  async validateCredentials() {
    try {
      const result = await this.ses.getSendQuota().promise();

      logger.info('SES credentials validated successfully');
      logger.info(`  Send quota: ${result.SentLast24Hours}/${result.Max24HourSend} (24hr)`);
      logger.info(`  Max send rate: ${result.MaxSendRate} emails/sec`);

      return {
        valid: true,
        quota: {
          max24HourSend: result.Max24HourSend,
          sentLast24Hours: result.SentLast24Hours,
          maxSendRate: result.MaxSendRate
        }
      };
    } catch (error) {
      logger.error(`SES credential validation failed: ${error.message}`);
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

module.exports = SESEmailSender;

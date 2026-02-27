#!/usr/bin/env python3
"""
AWS SES Email Sender Module

Provides email functionality using AWS Simple Email Service (SES).
This replaces the Gmail API for more reliable automated email delivery.

Benefits over Gmail API:
- No OAuth token expiration issues
- Native AWS integration with Lambda
- Cost effective (~$0.10 per 1000 emails)
- Simpler credential management via IAM
"""

import os
import logging
from typing import Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SESEmailSender:
    """
    AWS SES email sender with HTML support.

    Matches the interface of the Gmail-based EmailSender for easy swapping.
    """

    def __init__(
        self,
        region: str = 'us-east-1',
        sender_email: Optional[str] = None
    ):
        """
        Initialize SES email sender.

        Args:
            region: AWS region for SES (default: us-east-1)
            sender_email: Default sender email address (must be verified in SES)
        """
        self.region = region
        self.sender_email = sender_email or os.getenv('SES_SENDER_EMAIL', 'brandonhome.appdev@gmail.com')

        # Initialize SES client
        # Uses default credential chain: environment vars, IAM role, or ~/.aws/credentials
        self.ses_client = boto3.client('ses', region_name=region)

        logger.info(f"SES Email Sender initialized (region: {region}, sender: {self.sender_email})")

    def send_html_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        sender: Optional[str] = None
    ) -> bool:
        """
        Send an HTML email via AWS SES.

        Args:
            to: Recipient email address
            subject: Email subject line
            html_content: HTML body content
            text_content: Plain text alternative (auto-generated if not provided)
            sender: Override sender email (must be verified in SES)

        Returns:
            True if email sent successfully, False otherwise
        """
        sender_email = sender or self.sender_email

        # Generate plain text fallback if not provided
        if text_content is None:
            text_content = self._html_to_text(html_content)

        try:
            response = self.ses_client.send_email(
                Source=sender_email,
                Destination={
                    'ToAddresses': [to]
                },
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Text': {
                            'Data': text_content,
                            'Charset': 'UTF-8'
                        },
                        'Html': {
                            'Data': html_content,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )

            message_id = response.get('MessageId', 'unknown')
            logger.info(f"Email sent successfully! Message ID: {message_id}")
            logger.info(f"  To: {to}")
            logger.info(f"  Subject: {subject}")

            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            logger.error(f"SES send failed: {error_code} - {error_message}")

            # Provide helpful context for common errors
            if error_code == 'MessageRejected':
                logger.error("Message rejected - check sender/recipient verification")
            elif error_code == 'MailFromDomainNotVerified':
                logger.error(f"Sender domain not verified: {sender_email}")
            elif error_code == 'ConfigurationSetDoesNotExist':
                logger.error("SES configuration set not found")
            elif error_code == 'AccountSendingPaused':
                logger.error("SES sending paused - check AWS account status")

            return False

        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}", exc_info=True)
            return False

    def send_raw_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        sender: Optional[str] = None
    ) -> bool:
        """
        Send a raw MIME email via AWS SES.

        This method provides more control over email formatting.

        Args:
            to: Recipient email address
            subject: Email subject line
            html_content: HTML body content
            text_content: Plain text alternative
            sender: Override sender email

        Returns:
            True if email sent successfully, False otherwise
        """
        sender_email = sender or self.sender_email

        # Generate plain text fallback if not provided
        if text_content is None:
            text_content = self._html_to_text(html_content)

        # Create MIME message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to

        # Attach text and HTML parts
        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')

        msg.attach(part1)
        msg.attach(part2)

        try:
            response = self.ses_client.send_raw_email(
                Source=sender_email,
                Destinations=[to],
                RawMessage={
                    'Data': msg.as_string()
                }
            )

            message_id = response.get('MessageId', 'unknown')
            logger.info(f"Raw email sent successfully! Message ID: {message_id}")

            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"SES raw send failed: {error_code} - {error_message}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error sending raw email: {str(e)}", exc_info=True)
            return False

    def validate_credentials(self) -> bool:
        """
        Validate SES credentials and permissions.

        Returns:
            True if credentials are valid and have SES permissions
        """
        try:
            # Try to get send quota - this validates permissions
            response = self.ses_client.get_send_quota()

            max_24hr = response.get('Max24HourSend', 0)
            sent_24hr = response.get('SentLast24Hours', 0)
            max_send_rate = response.get('MaxSendRate', 0)

            logger.info("SES credentials validated successfully")
            logger.info(f"  Send quota: {sent_24hr:.0f}/{max_24hr:.0f} emails (24hr)")
            logger.info(f"  Max send rate: {max_send_rate:.1f} emails/sec")

            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            logger.error(f"SES credential validation failed: {error_code} - {error_message}")

            if error_code == 'AccessDeniedException':
                logger.error("IAM role/user lacks ses:GetSendQuota permission")

            return False

        except Exception as e:
            logger.error(f"Unexpected error validating SES: {str(e)}")
            return False

    def check_email_verified(self, email: str) -> bool:
        """
        Check if an email address is verified in SES.

        Args:
            email: Email address to check

        Returns:
            True if verified, False otherwise
        """
        try:
            response = self.ses_client.get_identity_verification_attributes(
                Identities=[email]
            )

            attributes = response.get('VerificationAttributes', {})
            email_attrs = attributes.get(email, {})
            status = email_attrs.get('VerificationStatus', 'NotVerified')

            is_verified = status == 'Success'

            if is_verified:
                logger.info(f"Email {email} is verified in SES")
            else:
                logger.warning(f"Email {email} verification status: {status}")

            return is_verified

        except ClientError as e:
            logger.error(f"Error checking email verification: {e}")
            return False

    def get_sending_limits(self) -> dict:
        """
        Get current SES sending limits and usage.

        Returns:
            Dictionary with quota information
        """
        try:
            response = self.ses_client.get_send_quota()

            return {
                'max_24hr_send': response.get('Max24HourSend', 0),
                'sent_last_24hrs': response.get('SentLast24Hours', 0),
                'max_send_rate': response.get('MaxSendRate', 0),
                'remaining_24hr': response.get('Max24HourSend', 0) - response.get('SentLast24Hours', 0)
            }

        except ClientError as e:
            logger.error(f"Error getting send quota: {e}")
            return {}

    def _html_to_text(self, html: str) -> str:
        """
        Convert HTML to plain text for email fallback.

        Simple conversion that strips HTML tags.

        Args:
            html: HTML content

        Returns:
            Plain text version
        """
        import re

        # Remove style and script tags with content
        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Replace common block elements with newlines
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</tr>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</td>', '\t', text, flags=re.IGNORECASE)
        text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)

        # Replace headers with emphasized text
        text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\n\1\n', text, flags=re.IGNORECASE | re.DOTALL)

        # Remove remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Decode HTML entities
        import html
        text = html.unescape(text)

        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        text = text.strip()

        return text

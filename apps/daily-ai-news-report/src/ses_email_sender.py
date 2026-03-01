"""
SES Email Sender - Sends emails via AWS SES.
"""

import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Union

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SESEmailSender:
    """Sends emails using AWS Simple Email Service (SES)."""

    def __init__(
        self,
        sender_email: Optional[str] = None,
        region: Optional[str] = None
    ):
        """
        Initialize the SES email sender.

        Args:
            sender_email: Sender email address (must be verified in SES)
            region: AWS region for SES
        """
        self.sender_email = sender_email or os.environ.get('SENDER_EMAIL')
        self.region = region or os.environ.get('AWS_REGION', 'us-east-1')

        if not self.sender_email:
            raise ValueError("Sender email is required")

        self.client = boto3.client('ses', region_name=self.region)

    def send_email(
        self,
        recipients: Union[str, List[str]],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        reply_to: Optional[List[str]] = None
    ) -> dict:
        """
        Send an email via SES.

        Args:
            recipients: Single email or list of recipient emails
            subject: Email subject
            html_body: HTML content
            text_body: Plain text content (optional)
            reply_to: Reply-to addresses (optional)

        Returns:
            SES response dict with MessageId
        """
        if isinstance(recipients, str):
            recipients = [recipients]

        # Create MIME message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.sender_email
        msg['To'] = ', '.join(recipients)

        # Add plain text part
        if text_body:
            text_part = MIMEText(text_body, 'plain', 'utf-8')
            msg.attach(text_part)

        # Add HTML part
        html_part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(html_part)

        try:
            response = self.client.send_raw_email(
                Source=self.sender_email,
                Destinations=recipients,
                RawMessage={'Data': msg.as_string()},
            )
            logger.info(f"Email sent successfully. MessageId: {response['MessageId']}")
            return response

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"SES error ({error_code}): {error_message}")
            raise

    def send_simple_email(
        self,
        recipients: Union[str, List[str]],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> dict:
        """
        Send a simple email via SES (non-MIME).

        Args:
            recipients: Single email or list of recipient emails
            subject: Email subject
            html_body: HTML content
            text_body: Plain text content (optional)

        Returns:
            SES response dict
        """
        if isinstance(recipients, str):
            recipients = [recipients]

        body = {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
        if text_body:
            body['Text'] = {'Data': text_body, 'Charset': 'UTF-8'}

        try:
            response = self.client.send_email(
                Source=self.sender_email,
                Destination={'ToAddresses': recipients},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': body,
                }
            )
            logger.info(f"Email sent successfully. MessageId: {response['MessageId']}")
            return response

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"SES error ({error_code}): {error_message}")
            raise

    def verify_email_identity(self, email: str) -> dict:
        """
        Send verification email to a new email address.

        Args:
            email: Email address to verify

        Returns:
            SES response
        """
        try:
            response = self.client.verify_email_identity(EmailAddress=email)
            logger.info(f"Verification email sent to {email}")
            return response
        except ClientError as e:
            logger.error(f"Failed to send verification: {e}")
            raise

    def get_send_quota(self) -> dict:
        """
        Get current SES sending quota and statistics.

        Returns:
            Dict with Max24HourSend, SentLast24Hours, MaxSendRate
        """
        try:
            response = self.client.get_send_quota()
            return {
                'max_24_hour_send': response['Max24HourSend'],
                'sent_last_24_hours': response['SentLast24Hours'],
                'max_send_rate': response['MaxSendRate'],
            }
        except ClientError as e:
            logger.error(f"Failed to get quota: {e}")
            raise

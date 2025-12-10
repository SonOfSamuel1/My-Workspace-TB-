"""
AWS SES Email Service for YNAB Transaction Reviewer

Handles email sending with HTML content using AWS Simple Email Service.
"""

import os
import logging
from typing import Optional, List, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import re

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SESEmailService:
    """Manages AWS SES email sending."""

    def __init__(self, sender_email: Optional[str] = None, region: Optional[str] = None):
        """
        Initialize the SES email service.

        Args:
            sender_email: Email address to send from (must be verified in SES)
            region: AWS region for SES (defaults to us-east-1)
        """
        self.sender_email = sender_email or os.getenv('SES_SENDER_EMAIL', 'TERRANCE@GOODPORTION.ORG')
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        self.client = boto3.client('ses', region_name=self.region)

    def send_email(self,
                   to: str,
                   subject: str,
                   html_body: str,
                   cc: Optional[List[str]] = None,
                   bcc: Optional[List[str]] = None,
                   reply_to: Optional[str] = None) -> bool:
        """
        Send an HTML email via SES.

        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML content for email body
            cc: Optional list of CC recipients
            bcc: Optional list of BCC recipients
            reply_to: Optional reply-to address

        Returns:
            True if sent successfully
        """
        try:
            # Create plain text version
            text_body = self._html_to_text(html_body)

            # Build destination
            destination = {'ToAddresses': [to]}
            if cc:
                destination['CcAddresses'] = cc
            if bcc:
                destination['BccAddresses'] = bcc

            # Build message
            message = {
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                    'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                }
            }

            # Send email
            kwargs = {
                'Source': self.sender_email,
                'Destination': destination,
                'Message': message
            }

            if reply_to:
                kwargs['ReplyToAddresses'] = [reply_to]

            response = self.client.send_email(**kwargs)
            logger.info(f"Email sent successfully via SES: {response['MessageId']}")
            return True

        except ClientError as error:
            logger.error(f"Failed to send email via SES: {error.response['Error']['Message']}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return False

    def send_transaction_review_email(self,
                                     to_email: str,
                                     transactions_html: str,
                                     summary_stats: Dict) -> bool:
        """
        Send transaction review email with formatted HTML.

        Args:
            to_email: Recipient email address
            transactions_html: HTML content for transactions section
            summary_stats: Summary statistics for the email

        Returns:
            True if sent successfully
        """
        # Determine subject based on unapproved count only
        unapproved_count = summary_stats.get('unapproved_count', 0)

        if unapproved_count == 0:
            subject = "[YNAB Review] All transactions approved!"
        else:
            subject = f"[YNAB Review] {unapproved_count} transactions need approval"

        # Build full HTML email
        html_body = self._build_review_email_html(transactions_html, summary_stats)

        return self.send_email(
            to=to_email,
            subject=subject,
            html_body=html_body
        )

    def _build_monthly_breakdown_html(self, unapproved_by_month: dict) -> str:
        """Build HTML for monthly breakdown of unapproved transactions"""
        if not unapproved_by_month:
            return ""

        # Sort months chronologically
        months = sorted(
            unapproved_by_month.keys(),
            key=lambda x: datetime.strptime(x, '%B %Y')
        )

        # Build badge HTML for each month with count > 0
        # Neutral gray styling for all badges
        badges = []
        for month in months:
            count = unapproved_by_month[month]
            if count > 0:
                badges.append(f'''
                    <span style="display: inline-block; background: #e5e7eb; color: #374151; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 500; margin: 4px;">
                        {month}: <strong>{count}</strong>
                    </span>
                ''')

        if not badges:
            return ""

        return f'''
        <div style="background: #f8fafc; border-radius: 12px; padding: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">
            <div style="font-size: 11px; color: #64748b; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">By Month</div>
            <div>
                {''.join(badges)}
            </div>
        </div>
        '''

    def _build_review_email_html(self, transactions_html: str, summary_stats: Dict) -> str:
        """Build complete HTML email for transaction review"""
        # Build monthly breakdown HTML
        monthly_breakdown_html = self._build_monthly_breakdown_html(
            summary_stats.get('unapproved_by_month', {})
        )

        # Get next email time
        tomorrow = datetime.now() + timedelta(days=1)
        if tomorrow.weekday() == 5:  # Saturday
            next_email = "Sunday at 5 PM"
        else:
            next_email = "Tomorrow at 5 PM"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f8fafc;">
                <tr>
                    <td align="center" style="padding: 40px 20px;">
                        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">

                            <!-- Header -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #1e293b 0%, #334155 100%); padding: 32px 40px;">
                                    <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600; letter-spacing: -0.5px;">YNAB Transaction Review</h1>
                                    <p style="margin: 6px 0 0 0; color: #94a3b8; font-size: 14px;">{datetime.now().strftime('%A, %B %d, %Y')}</p>
                                </td>
                            </tr>

                            <!-- Summary Stats -->
                            <tr>
                                <td style="padding: 32px 40px 24px 40px;">
                                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                        <tr>
                                            <td width="33%" align="center" style="padding: 16px 8px;">
                                                <div style="background: #f3f4f6; border-radius: 12px; padding: 20px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                                                    <div style="font-size: 36px; font-weight: 700; color: #1f2937; line-height: 1;">{summary_stats.get('unapproved_count', 0)}</div>
                                                    <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 8px; font-weight: 600;">Need Approval</div>
                                                </div>
                                            </td>
                                            <td width="33%" align="center" style="padding: 16px 8px;">
                                                <div style="background: #f3f4f6; border-radius: 12px; padding: 20px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                                                    <div style="font-size: 36px; font-weight: 700; color: #1f2937; line-height: 1;">{summary_stats.get('oldest_days', 0)}</div>
                                                    <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 8px; font-weight: 600;">Days Old</div>
                                                </div>
                                            </td>
                                            <td width="33%" align="center" style="padding: 16px 8px;">
                                                <div style="background: #f3f4f6; border-radius: 12px; padding: 20px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                                                    <div style="font-size: 36px; font-weight: 700; color: #1f2937; line-height: 1;">{summary_stats.get('amazon_unapproved_count', 0)}</div>
                                                    <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 8px; font-weight: 600;">Amazon</div>
                                                </div>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>

                            <!-- Monthly Breakdown -->
                            <tr>
                                <td style="padding: 0 40px 24px 40px;">
                                    {monthly_breakdown_html}
                                </td>
                            </tr>

                            <!-- Transactions -->
                            <tr>
                                <td style="padding: 0 40px 32px 40px;">
                                    {transactions_html}
                                </td>
                            </tr>

                            <!-- Footer -->
                            <tr>
                                <td style="background: #f8fafc; padding: 24px 40px; border-top: 1px solid #e5e7eb;">
                                    <p style="margin: 0 0 16px 0; text-align: center;">
                                        <a href="https://app.ynab.com" style="display: inline-block; background: #374151; color: #ffffff; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 500; box-shadow: 0 1px 2px rgba(0,0,0,0.04);">Open YNAB</a>
                                    </p>
                                    <p style="margin: 0; color: #64748b; font-size: 13px; text-align: center;">
                                        Next review: <strong style="color: #475569;">{next_email}</strong>
                                    </p>
                                    <p style="margin: 8px 0 0 0; color: #94a3b8; font-size: 12px; text-align: center;">
                                        Daily at 5 PM (except Saturdays)
                                    </p>
                                </td>
                            </tr>

                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        return html

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (simplified)"""
        # Remove HTML tags
        text = re.sub('<[^<]+?>', '', html)
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Replace HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        return text.strip()

    def test_connection(self) -> bool:
        """
        Test SES connection by checking identity verification status.

        Returns:
            True if connection successful
        """
        try:
            response = self.client.get_identity_verification_attributes(
                Identities=[self.sender_email]
            )
            status = response.get('VerificationAttributes', {}).get(
                self.sender_email, {}
            ).get('VerificationStatus', 'NotFound')

            if status == 'Success':
                logger.info(f"SES sender verified: {self.sender_email}")
                return True
            else:
                logger.warning(f"SES sender not verified: {self.sender_email} (status: {status})")
                return False
        except ClientError as error:
            logger.error(f"SES connection test failed: {error}")
            return False

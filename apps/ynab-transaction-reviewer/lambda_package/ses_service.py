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
        # Determine subject based on transaction counts
        uncategorized_count = summary_stats.get('total_count', 0)
        unapproved_count = summary_stats.get('unapproved_count', 0)

        if uncategorized_count == 0 and unapproved_count == 0:
            subject = "[YNAB Review] All transactions categorized!"
        else:
            parts = []
            if uncategorized_count > 0:
                parts.append(f"{uncategorized_count} uncategorized")
            if unapproved_count > 0:
                parts.append(f"{unapproved_count} need approval")
            subject = f"[YNAB Review] {' + '.join(parts)}"

        # Build full HTML email
        html_body = self._build_review_email_html(transactions_html, summary_stats)

        return self.send_email(
            to=to_email,
            subject=subject,
            html_body=html_body
        )

    def _build_review_email_html(self, transactions_html: str, summary_stats: Dict) -> str:
        """Build complete HTML email for transaction review"""
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
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background-color: white;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    border-bottom: 2px solid #4CAF50;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                h1 {{
                    color: #2c3e50;
                    margin: 0;
                    font-size: 28px;
                }}
                .subtitle {{
                    color: #7f8c8d;
                    margin-top: 5px;
                    font-size: 14px;
                }}
                .summary {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 30px;
                }}
                .summary-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 20px;
                    margin-top: 15px;
                }}
                .summary-item {{
                    text-align: center;
                }}
                .summary-value {{
                    font-size: 24px;
                    font-weight: bold;
                }}
                .summary-label {{
                    font-size: 12px;
                    opacity: 0.9;
                    text-transform: uppercase;
                }}
                .transactions-section {{
                    margin-top: 30px;
                }}
                .transaction {{
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                }}
                .transaction-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: start;
                    margin-bottom: 10px;
                }}
                .transaction-payee {{
                    font-size: 18px;
                    font-weight: 600;
                    color: #2c3e50;
                }}
                .transaction-amount {{
                    font-size: 20px;
                    font-weight: bold;
                    color: #e74c3c;
                }}
                .transaction-amount.positive {{
                    color: #27ae60;
                }}
                .transaction-details {{
                    color: #6c757d;
                    font-size: 14px;
                    margin: 10px 0;
                }}
                .suggestion-box {{
                    background: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    padding: 15px;
                    margin: 15px 0;
                }}
                .suggestion-header {{
                    color: #5c6bc0;
                    font-weight: 600;
                    margin-bottom: 10px;
                    display: flex;
                    align-items: center;
                }}
                .suggestion-item {{
                    padding: 8px 0;
                    border-bottom: 1px solid #f0f0f0;
                }}
                .suggestion-item:last-child {{
                    border-bottom: none;
                }}
                .confidence {{
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                    margin-left: 10px;
                }}
                .confidence.high {{
                    background: #c8e6c9;
                    color: #2e7d32;
                }}
                .confidence.medium {{
                    background: #fff3cd;
                    color: #856404;
                }}
                .confidence.low {{
                    background: #f8d7da;
                    color: #721c24;
                }}
                .action-buttons {{
                    margin-top: 15px;
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                }}
                .action-button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: 500;
                }}
                .action-button:hover {{
                    background: #45a049;
                }}
                .action-button.secondary {{
                    background: #6c757d;
                }}
                .action-button.secondary:hover {{
                    background: #5a6268;
                }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #e0e0e0;
                    text-align: center;
                    color: #6c757d;
                    font-size: 13px;
                }}
                .next-email {{
                    background: #e3f2fd;
                    color: #1976d2;
                    padding: 10px;
                    border-radius: 5px;
                    margin-top: 20px;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>YNAB Transaction Review</h1>
                    <div class="subtitle">{datetime.now().strftime('%A, %B %d, %Y')}</div>
                </div>

                <div class="summary">
                    <h2 style="margin: 0; margin-bottom: 10px;">Summary</h2>
                    <div class="summary-grid">
                        <div class="summary-item">
                            <div class="summary-value">{summary_stats.get('total_count', 0)}</div>
                            <div class="summary-label">Uncategorized</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-value" style="color: #ffcc80;">{summary_stats.get('unapproved_count', 0)}</div>
                            <div class="summary-label">Need Approval</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-value">{summary_stats.get('accounts_affected', 0)}</div>
                            <div class="summary-label">Accounts</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-value">{summary_stats.get('oldest_days', 0)}</div>
                            <div class="summary-label">Days Old</div>
                        </div>
                    </div>
                </div>

                <div class="transactions-section">
                    <h2>Transactions Needing Categorization</h2>
                    {transactions_html}
                </div>

                <div class="next-email">
                    Next email: {next_email}
                </div>

                <div class="footer">
                    <p>YNAB Transaction Reviewer - Automated Daily at 5 PM (except Saturdays)</p>
                </div>
            </div>
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

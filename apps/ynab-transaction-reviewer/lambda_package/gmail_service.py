"""
Gmail Service for YNAB Transaction Reviewer

Handles email sending with HTML content for transaction review notifications.
"""

import os
import base64
import pickle
import logging
from pathlib import Path
from typing import Optional, List, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Monkey patch for Python 3.9 compatibility
import importlib.metadata as metadata
if not hasattr(metadata, 'packages_distributions'):
    def packages_distributions():
        return {}
    metadata.packages_distributions = packages_distributions

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Gmail API scopes needed for sending emails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class GmailService:
    """Manages Gmail API authentication and email sending."""

    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """
        Initialize the Gmail service manager.

        Args:
            credentials_path: Path to credentials.json file
            token_path: Path to store token.pickle file
        """
        # Set default paths - check environment variables first (for Lambda)
        base_dir = Path(__file__).parent.parent
        self.credentials_path = (
            credentials_path or
            os.getenv('GMAIL_CREDENTIALS_PATH') or
            str(base_dir / 'credentials' / 'gmail_credentials.json')
        )
        self.token_path = (
            token_path or
            os.getenv('GMAIL_TOKEN_PATH') or
            str(base_dir / 'credentials' / 'gmail_token.pickle')
        )

        # Ensure credentials directory exists
        Path(self.token_path).parent.mkdir(parents=True, exist_ok=True)

        self.service = None
        self.creds = None

    def authenticate(self) -> Credentials:
        """
        Authenticate with Gmail API using OAuth2.

        Returns:
            Authenticated credentials object
        """
        creds = None

        # Load existing token if it exists
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
                logger.info("Loaded existing Gmail authentication token")
            except Exception as e:
                logger.warning(f"Could not load token: {e}")
                creds = None

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired Gmail token")
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found at {self.credentials_path}\n"
                        "Please download credentials.json from Google Cloud Console:\n"
                        "1. Go to https://console.cloud.google.com/\n"
                        "2. Enable Gmail API\n"
                        "3. Create OAuth 2.0 credentials\n"
                        "4. Download as 'gmail_credentials.json' and place in credentials/"
                    )

                logger.info("Starting Gmail OAuth2 flow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Gmail authentication successful")

            # Save the credentials for the next run
            try:
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info("Saved Gmail authentication token")
            except Exception as e:
                logger.error(f"Could not save token: {e}")

        self.creds = creds
        return creds

    def get_service(self):
        """
        Get authenticated Gmail service object.

        Returns:
            Gmail service object for API calls
        """
        if not self.service:
            if not self.creds:
                self.authenticate()

            try:
                self.service = build('gmail', 'v1', credentials=self.creds)
                logger.info("Gmail service created successfully")
            except Exception as e:
                logger.error(f"Failed to create Gmail service: {e}")
                raise

        return self.service

    def send_email(self,
                   to: str,
                   subject: str,
                   html_body: str,
                   cc: Optional[List[str]] = None,
                   bcc: Optional[List[str]] = None,
                   reply_to: Optional[str] = None) -> bool:
        """
        Send an HTML email.

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
            service = self.get_service()

            # Create message
            message = MIMEMultipart('alternative')
            message['To'] = to
            message['Subject'] = subject

            # Get sender email
            sender_email = self.get_user_email()
            if sender_email:
                message['From'] = sender_email

            if cc:
                message['Cc'] = ', '.join(cc)
            if bcc:
                message['Bcc'] = ', '.join(bcc)
            if reply_to:
                message['Reply-To'] = reply_to

            # Create plain text version (simplified)
            text_body = self._html_to_text(html_body)
            part_text = MIMEText(text_body, 'plain')
            part_html = MIMEText(html_body, 'html')

            message.attach(part_text)
            message.attach(part_html)

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            body = {'raw': raw_message}

            # Send message
            result = service.users().messages().send(userId='me', body=body).execute()
            logger.info(f"Email sent successfully: {result['id']}")
            return True

        except HttpError as error:
            logger.error(f"Failed to send email: {error}")
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
        from datetime import datetime, timedelta
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
                    📧 Next email: {next_email}
                </div>

                <div class="footer">
                    <p>YNAB Transaction Reviewer • Automated Daily at 5 PM (except Saturdays)</p>
                    <p style="margin-top: 10px;">
                        <a href="#" style="color: #6c757d; margin: 0 10px;">Preferences</a> •
                        <a href="#" style="color: #6c757d; margin: 0 10px;">Unsubscribe</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (simplified)"""
        # Very basic HTML to text conversion
        import re
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
        Test Gmail API connection.

        Returns:
            True if connection successful
        """
        try:
            service = self.get_service()
            # Try to get user profile
            result = service.users().getProfile(userId='me').execute()
            logger.info(f"Gmail connected: {result.get('emailAddress')}")
            return True
        except HttpError as error:
            logger.error(f"Gmail connection test failed: {error}")
            return False

    def get_user_email(self) -> Optional[str]:
        """
        Get the authenticated user's email address.

        Returns:
            Email address string or None
        """
        try:
            service = self.get_service()
            result = service.users().getProfile(userId='me').execute()
            return result.get('emailAddress')
        except Exception as e:
            logger.error(f"Could not get user email: {e}")
            return None
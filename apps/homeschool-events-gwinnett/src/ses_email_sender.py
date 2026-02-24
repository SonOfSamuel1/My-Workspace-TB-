#!/usr/bin/env python3
"""
AWS SES Email Sender Module

Provides email functionality using AWS Simple Email Service (SES).
Reused from weekly-atlanta-news-report.
"""

import html
import logging
import os
import re
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SESEmailSender:
    """AWS SES email sender with HTML support."""

    def __init__(
        self,
        region: str = "us-east-1",
        sender_email: Optional[str] = None,
    ):
        self.region = region
        self.sender_email = sender_email or os.getenv(
            "SES_SENDER_EMAIL", "brandonhome.appdev@gmail.com"
        )
        self.ses_client = boto3.client("ses", region_name=region)
        logger.info(
            f"SES Email Sender initialized (region: {region}, sender: {self.sender_email})"
        )

    def send_html_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        sender: Optional[str] = None,
    ) -> bool:
        """Send an HTML email via AWS SES.

        Args:
            to: Single email or comma-separated list of emails.
        """
        sender_email = sender or self.sender_email

        if text_content is None:
            text_content = self._html_to_text(html_content)

        to_addresses = [addr.strip() for addr in to.split(",") if addr.strip()]

        try:
            response = self.ses_client.send_email(
                Source=sender_email,
                Destination={"ToAddresses": to_addresses},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": text_content, "Charset": "UTF-8"},
                        "Html": {"Data": html_content, "Charset": "UTF-8"},
                    },
                },
            )

            message_id = response.get("MessageId", "unknown")
            logger.info(f"Email sent successfully! Message ID: {message_id}")
            logger.info(f"  To: {', '.join(to_addresses)}")
            logger.info(f"  Subject: {subject}")
            return True

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error(f"SES send failed: {error_code} - {error_message}")

            if error_code == "MessageRejected":
                logger.error("Message rejected - check sender/recipient verification")
            elif error_code == "MailFromDomainNotVerified":
                logger.error(f"Sender domain not verified: {sender_email}")
            elif error_code == "AccountSendingPaused":
                logger.error("SES sending paused - check AWS account status")

            return False

        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}", exc_info=True)
            return False

    def validate_credentials(self) -> bool:
        """Validate SES credentials and permissions."""
        try:
            response = self.ses_client.get_send_quota()

            max_24hr = response.get("Max24HourSend", 0)
            sent_24hr = response.get("SentLast24Hours", 0)
            max_send_rate = response.get("MaxSendRate", 0)

            logger.info("SES credentials validated successfully")
            logger.info(f"  Send quota: {sent_24hr:.0f}/{max_24hr:.0f} emails (24hr)")
            logger.info(f"  Max send rate: {max_send_rate:.1f} emails/sec")
            return True

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            logger.error(f"SES credential validation failed: {error_code}")
            if error_code == "AccessDeniedException":
                logger.error("IAM role/user lacks ses:GetSendQuota permission")
            return False

        except Exception as e:
            logger.error(f"Unexpected error validating SES: {str(e)}")
            return False

    def check_email_verified(self, email: str) -> bool:
        """Check if an email address is verified in SES."""
        try:
            response = self.ses_client.get_identity_verification_attributes(
                Identities=[email]
            )
            attributes = response.get("VerificationAttributes", {})
            email_attrs = attributes.get(email, {})
            status = email_attrs.get("VerificationStatus", "NotVerified")
            is_verified = status == "Success"

            if is_verified:
                logger.info(f"Email {email} is verified in SES")
            else:
                logger.warning(f"Email {email} verification status: {status}")
            return is_verified

        except ClientError as e:
            logger.error(f"Error checking email verification: {e}")
            return False

    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text for email fallback."""
        text = re.sub(
            r"<style[^>]*>.*?</style>",
            "",
            html_content,
            flags=re.DOTALL | re.IGNORECASE,
        )
        text = re.sub(
            r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE
        )
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</tr>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</td>", "\t", text, flags=re.IGNORECASE)
        text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(
            r"<h[1-6][^>]*>(.*?)</h[1-6]>",
            r"\n\n\1\n",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r" +", " ", text)
        return text.strip()

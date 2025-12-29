"""
General email matcher for finding receipt/confirmation emails
that match YNAB transactions by payee name and amount.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from email_client_base import EmailMessage

logger = logging.getLogger(__name__)


class GeneralEmailMatcher:
    """
    Searches email accounts for receipt/confirmation emails
    matching YNAB transactions by payee name and amount.
    """

    def __init__(self, email_service: Any):
        """
        Initialize the email matcher.

        Args:
            email_service: MultiAccountEmailService instance
        """
        self.email_service = email_service

    def find_receipt_email(
        self,
        payee_name: str,
        amount: float,
        txn_date: datetime,
        days_tolerance: int = 7
    ) -> Optional[Dict]:
        """
        Search emails for a receipt matching the payee and amount.

        Args:
            payee_name: YNAB payee name (e.g., "Target", "Costco")
            amount: Transaction amount in dollars
            txn_date: Transaction date
            days_tolerance: Days before/after to search

        Returns:
            Dict with email match info or None if not found:
            {
                'message_id': str,
                'subject': str,
                'date': datetime,
                'sender': str,
                'source_account': str,  # "Primary Gmail" or "Brittany Mail.com"
                'account_type': str,    # "gmail" or "imap"
                'deep_link': Optional[str],  # Gmail deep link or None
            }
        """
        if not payee_name or amount <= 0:
            return None

        # Clean payee name for search
        search_term = self._clean_payee_for_search(payee_name)
        if not search_term:
            return None

        logger.info(f"Searching emails for: '{search_term}' ${amount:.2f} around {txn_date.date()}")

        # Search each email client
        for client in self.email_service.clients:
            try:
                match = self._search_client_for_receipt(
                    client=client,
                    search_term=search_term,
                    amount=amount,
                    txn_date=txn_date,
                    days_tolerance=days_tolerance
                )
                if match:
                    return match
            except Exception as e:
                logger.error(f"Error searching {client.name}: {e}")
                continue

        return None

    def _clean_payee_for_search(self, payee_name: str) -> str:
        """
        Clean and normalize payee name for email search.

        Removes common prefixes, suffixes, and normalizes for search.
        """
        if not payee_name:
            return ""

        # Convert to lowercase for processing
        cleaned = payee_name.strip()

        # Remove common card transaction prefixes
        prefixes_to_remove = [
            'TST*', 'SQ*', 'SQU*', 'PAYPAL*', 'PP*', 'CHECKCARD ',
            'POS ', 'PURCHASE ', 'DEBIT CARD ', 'VISA ', 'MC ',
        ]
        for prefix in prefixes_to_remove:
            if cleaned.upper().startswith(prefix):
                cleaned = cleaned[len(prefix):]

        # Remove location suffixes (city, state, ZIP)
        # Pattern: ends with things like "AUSTIN TX", "CA 94xxx", etc.
        cleaned = re.sub(r'\s+[A-Z]{2}\s*\d{5}(-\d{4})?$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+[A-Z]{2}$', '', cleaned, flags=re.IGNORECASE)

        # Remove store numbers like "#1234" or "STORE 1234"
        cleaned = re.sub(r'#?\s*\d{3,}$', '', cleaned)
        cleaned = re.sub(r'\s+(STORE|STR|LOC)\s*#?\d+', '', cleaned, flags=re.IGNORECASE)

        # Remove trailing asterisks and spaces
        cleaned = cleaned.rstrip('* ')

        # Take first part if there's a dash separator (e.g., "TARGET - T1234")
        if ' - ' in cleaned:
            cleaned = cleaned.split(' - ')[0]

        # Get the core business name (first 2-3 words usually)
        words = cleaned.split()
        if len(words) > 3:
            cleaned = ' '.join(words[:3])

        return cleaned.strip()

    def _search_client_for_receipt(
        self,
        client: Any,
        search_term: str,
        amount: float,
        txn_date: datetime,
        days_tolerance: int
    ) -> Optional[Dict]:
        """
        Search a specific email client for matching receipt.
        """
        # Calculate date range
        start_date = txn_date - timedelta(days=days_tolerance)
        end_date = txn_date + timedelta(days=days_tolerance)
        days_back = (datetime.now() - start_date).days + 1

        # Format amount for search (handles $XX.XX format)
        amount_str = f"{amount:.2f}"
        amount_whole = str(int(amount))

        # Search for emails containing the payee name
        try:
            messages = client.search_messages(
                senders=None,  # Search all senders
                days_back=days_back,
                subject_contains=search_term,
                max_results=50
            )
        except Exception as e:
            logger.debug(f"Subject search failed for {client.name}: {e}")
            messages = []

        # If no subject matches, try body search for Gmail
        if not messages and hasattr(client, 'account_type') and client.account_type == 'gmail':
            try:
                # Gmail supports full-text search
                messages = self._gmail_full_search(client, search_term, days_back)
            except Exception as e:
                logger.debug(f"Full-text search failed: {e}")

        # Filter messages by amount and date
        for msg in messages:
            if not self._is_in_date_range(msg.date, start_date, end_date):
                continue

            # Check if amount appears in email
            if self._message_contains_amount(msg, amount_str, amount_whole):
                # Build result
                result = {
                    'message_id': msg.id,
                    'subject': msg.subject[:100] if msg.subject else 'No Subject',
                    'body_text': msg.body_text[:1000] if msg.body_text else '',
                    'date': msg.date,
                    'sender': msg.sender,
                    'source_account': client.name,
                    'account_type': getattr(client, 'account_type', 'unknown'),
                    'deep_link': None
                }

                # Add Gmail deep link
                if result['account_type'] == 'gmail':
                    result['deep_link'] = f"https://mail.google.com/mail/u/0/#inbox/{msg.id}"

                logger.info(f"Found receipt match in {client.name}: {msg.subject[:50]}...")
                return result

        return None

    def _gmail_full_search(self, client: Any, search_term: str, days_back: int) -> List[EmailMessage]:
        """
        Perform Gmail full-text search using the API query.
        """
        # Access the Gmail service directly
        if not hasattr(client, '_service'):
            return []

        try:
            after_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
            query = f'"{search_term}" after:{after_date}'

            results = client._service.users().messages().list(
                userId='me',
                q=query,
                maxResults=20
            ).execute()

            message_refs = results.get('messages', [])
            messages = []

            for msg_ref in message_refs[:20]:
                try:
                    message = client.get_message(msg_ref['id'])
                    if message:
                        messages.append(message)
                except Exception:
                    continue

            return messages
        except Exception as e:
            logger.debug(f"Gmail full search error: {e}")
            return []

    def _is_in_date_range(self, email_date: datetime, start: datetime, end: datetime) -> bool:
        """Check if email date is within the expected range."""
        if not email_date:
            return False

        # Normalize to date only for comparison
        email_d = email_date.date() if hasattr(email_date, 'date') else email_date
        start_d = start.date() if hasattr(start, 'date') else start
        end_d = end.date() if hasattr(end, 'date') else end

        return start_d <= email_d <= end_d

    def _message_contains_amount(
        self,
        message: EmailMessage,
        amount_str: str,
        amount_whole: str
    ) -> bool:
        """
        Check if the email contains the transaction amount.
        """
        # Build content to search
        content_parts = []

        if message.subject:
            content_parts.append(message.subject)
        if message.body_text:
            content_parts.append(message.body_text)
        if message.body_html:
            content_parts.append(message.body_html)

        content = ' '.join(content_parts)

        if not content:
            return False

        # Look for amount patterns
        # $XX.XX or XX.XX
        if amount_str in content:
            return True

        # With dollar sign variations
        if f"${amount_str}" in content:
            return True

        # Sometimes amounts appear without cents for whole dollars
        if amount_str.endswith('.00'):
            if f"${amount_whole}" in content or f" {amount_whole} " in content:
                return True

        # Look for amount with different separators
        amount_comma = amount_str.replace('.', ',')
        if amount_comma in content or f"${amount_comma}" in content:
            return True

        return False

    def find_all_receipt_emails(
        self,
        transactions: List[Dict],
        days_tolerance: int = 7
    ) -> List[Dict]:
        """
        Find receipt emails for multiple transactions.

        Args:
            transactions: List of YNAB transaction dicts
            days_tolerance: Days before/after to search

        Returns:
            List of dicts with transaction + email match info
        """
        results = []

        for txn in transactions:
            payee_name = txn.get('payee_name', '')
            amount = txn.get('amount', 0)
            txn_date = txn.get('date')

            if not txn_date:
                continue

            if isinstance(txn_date, str):
                txn_date = datetime.fromisoformat(txn_date)

            match = self.find_receipt_email(
                payee_name=payee_name,
                amount=amount,
                txn_date=txn_date,
                days_tolerance=days_tolerance
            )

            result = {
                'transaction': txn,
                'email_match': match,
                'matched': match is not None
            }
            results.append(result)

        matched_count = sum(1 for r in results if r['matched'])
        logger.info(f"Found email matches for {matched_count}/{len(transactions)} transactions")

        return results

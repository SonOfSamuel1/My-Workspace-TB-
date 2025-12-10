"""
Amazon email parser for order confirmation emails.
Extracts transaction data from emails (Gmail or IMAP) without browser automation.

Supports both:
- Legacy Gmail API service object (backward compatible)
- New EmailMessage objects from multi-account email service
"""

import os
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union, Any
from bs4 import BeautifulSoup
import base64

# Import EmailMessage for type checking (optional import for backward compatibility)
try:
    from email_client_base import EmailMessage
except ImportError:
    EmailMessage = None

logger = logging.getLogger(__name__)


class AmazonEmailParser:
    """
    Parse Amazon order confirmation emails.

    Supports multiple input sources:
    - Gmail API service object (legacy)
    - EmailMessage objects from multi-account email service
    """

    def __init__(self, gmail_service=None):
        """
        Initialize the email parser.

        Args:
            gmail_service: Optional Gmail API service object (legacy support)
        """
        self.gmail_service = gmail_service
        self.email_addresses = [
            'ship-confirm@amazon.com',
            'auto-confirm@amazon.com',
            'order-update@amazon.com',
            'digital-no-reply@amazon.com',
            'no-reply@amazon.com'
        ]

    def fetch_order_emails(self, days_back: int = 7) -> List[Dict]:
        """
        Fetch Amazon order confirmation emails from Gmail.

        Args:
            days_back: Number of days to look back for emails

        Returns:
            List of email messages
        """
        try:
            # Build query for Amazon emails
            after_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')

            # Search for emails from Amazon
            queries = []
            for email in self.email_addresses:
                queries.append(f'from:{email}')

            query = f"({' OR '.join(queries)}) after:{after_date}"
            logger.info(f"Searching Gmail with query: {query}")

            # Execute search
            results = self.gmail_service.users().messages().list(
                userId='me',
                q=query,
                maxResults=100
            ).execute()

            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} Amazon emails")

            # Fetch full message content
            emails = []
            for msg in messages:
                try:
                    full_msg = self.gmail_service.users().messages().get(
                        userId='me',
                        id=msg['id']
                    ).execute()
                    emails.append(full_msg)
                except Exception as e:
                    logger.error(f"Error fetching email {msg['id']}: {str(e)}")
                    continue

            return emails

        except Exception as e:
            logger.error(f"Failed to fetch Amazon emails: {str(e)}")
            return []

    def parse_order_email(self, email_message: Dict) -> Optional[Dict]:
        """
        Parse an Amazon order confirmation email.

        Args:
            email_message: Gmail message object

        Returns:
            Parsed transaction dictionary or None
        """
        try:
            # Extract email metadata
            headers = email_message['payload'].get('headers', [])
            subject = ''
            date_str = ''

            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                elif header['name'] == 'Date':
                    date_str = header['value']

            # Skip if not an order confirmation
            if not any(keyword in subject.lower() for keyword in ['order', 'shipment', 'delivered', 'your amazon.com order']):
                return None

            # Extract email body
            body_html = self._extract_email_body(email_message)
            if not body_html:
                return None

            # Parse HTML content
            soup = BeautifulSoup(body_html, 'html.parser')

            # Extract order details
            order_data = self._extract_order_details(soup, subject)

            if not order_data:
                return None

            # Parse email date
            email_date = self._parse_email_date(date_str)
            if not order_data.get('date'):
                order_data['date'] = email_date

            logger.info(f"Parsed order: {order_data.get('order_id', 'Unknown')} - ${order_data.get('total', 0)}")
            return order_data

        except Exception as e:
            logger.error(f"Failed to parse email: {str(e)}")
            return None

    def _extract_email_body(self, message: Dict) -> Optional[str]:
        """Extract HTML body from email message."""
        try:
            # Handle multipart messages
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part['mimeType'] == 'text/html':
                        data = part['body'].get('data', '')
                        if data:
                            return base64.urlsafe_b64decode(data).decode('utf-8')
                    elif 'parts' in part:  # Nested parts
                        for subpart in part['parts']:
                            if subpart['mimeType'] == 'text/html':
                                data = subpart['body'].get('data', '')
                                if data:
                                    return base64.urlsafe_b64decode(data).decode('utf-8')

            # Handle simple messages
            elif message['payload'].get('body', {}).get('data'):
                return base64.urlsafe_b64decode(
                    message['payload']['body']['data']
                ).decode('utf-8')

        except Exception as e:
            logger.error(f"Error extracting email body: {str(e)}")

        return None

    def _extract_order_details(self, soup: BeautifulSoup, subject: str) -> Optional[Dict]:
        """
        Extract order details from parsed HTML.

        Args:
            soup: BeautifulSoup parsed HTML
            subject: Email subject line

        Returns:
            Order details dictionary
        """
        try:
            # Initialize order data
            order_data = {
                'items': [],
                'status': 'Confirmed'
            }

            # Extract order ID from subject or body
            order_id_match = re.search(r'\b(\d{3}-\d{7}-\d{7})\b', str(soup))
            if order_id_match:
                order_data['order_id'] = order_id_match.group(1)
            else:
                # Generate pseudo ID from email timestamp
                order_data['order_id'] = f"EMAIL-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Extract total amount
            # Look for patterns like "$49.99" or "Order Total: $123.45"
            total_patterns = [
                r'(?:order total|total|grand total)[:\s]*\$?([\d,]+\.?\d*)',
                r'\$?([\d,]+\.?\d+).*(?:order total|total)',
                r'(?:charged|payment)[:\s]*\$?([\d,]+\.?\d*)'
            ]

            text_content = soup.get_text().lower()
            for pattern in total_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    try:
                        order_data['total'] = float(match.group(1).replace(',', ''))
                        break
                    except:
                        continue

            # If no total found, look for item prices (with $ sign to be more specific)
            if 'total' not in order_data:
                # First try finding prices with $ sign (more reliable)
                price_matches = re.findall(r'\$\s*([\d,]+\.\d{2})', str(soup))
                if price_matches:
                    # Filter out unreasonable prices (more than $10,000)
                    prices = [float(p.replace(',', '')) for p in price_matches if float(p.replace(',', '')) < 10000]
                    if prices:
                        order_data['total'] = max(prices)

            # Extract items (simplified - look for product names)
            # Amazon emails typically have product names as links
            product_links = soup.find_all('a', href=re.compile(r'/dp/|/gp/product'))

            for link in product_links[:5]:  # Limit to first 5 items
                item_name = link.get_text(strip=True)
                if item_name and len(item_name) > 3:
                    # Extract ASIN from link if available
                    asin_match = re.search(r'/dp/([A-Z0-9]{10})', link.get('href', ''))
                    asin = asin_match.group(1) if asin_match else 'UNKNOWN'

                    order_data['items'].append({
                        'name': item_name[:100],  # Truncate long names
                        'category': 'General',  # Will be refined later
                        'asin': asin,
                        'link': f"https://www.amazon.com/dp/{asin}"
                    })

            # If no items found, create generic item
            if not order_data['items']:
                order_data['items'] = [{
                    'name': 'Amazon Purchase',
                    'category': 'Shopping',
                    'asin': 'UNKNOWN',
                    'link': 'https://www.amazon.com'
                }]

            # Set item prices (divide total by number of items as estimate)
            if order_data.get('total') and order_data['items']:
                item_price = order_data['total'] / len(order_data['items'])
                for item in order_data['items']:
                    item['price'] = round(item_price, 2)
                    item['quantity'] = 1

            # Extract or estimate dates
            # Look for delivery date or order date in email
            date_patterns = [
                r'(?:delivered|arriving|expected)[:\s]*([a-z]+ \d{1,2},? \d{4})',
                r'(?:ordered on|order date)[:\s]*([a-z]+ \d{1,2},? \d{4})',
                r'([a-z]+ \d{1,2},? \d{4})'
            ]

            for pattern in date_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    try:
                        order_data['date'] = datetime.strptime(match.group(1), '%B %d, %Y')
                        break
                    except:
                        try:
                            order_data['date'] = datetime.strptime(match.group(1), '%b %d, %Y')
                            break
                        except:
                            continue

            # Estimate subtotal and tax
            if order_data.get('total'):
                order_data['subtotal'] = round(order_data['total'] * 0.92, 2)
                order_data['tax'] = round(order_data['total'] * 0.08, 2)

            # Default payment method (will be matched by account later)
            order_data['payment_method'] = 'Amazon Card'

            # Sanity check: reject unreasonable totals (> $10,000 or < $0.01)
            total = order_data.get('total', 0)
            if total < 0.01 or total > 10000:
                logger.debug(f"Rejecting order with invalid total: ${total}")
                return None

            return order_data

        except Exception as e:
            logger.error(f"Error extracting order details: {str(e)}")
            return None

    def _parse_email_date(self, date_str: str) -> datetime:
        """Parse email date string to datetime."""
        try:
            # Gmail date format: "Mon, 1 Jan 2024 12:00:00 +0000"
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str).replace(tzinfo=None)
        except:
            return datetime.now()

    def get_transactions(self, start_date: datetime, end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Main entry point to get Amazon transactions from emails.

        Args:
            start_date: Start of date range
            end_date: End of date range (default: today)

        Returns:
            List of transaction dictionaries
        """
        if not end_date:
            end_date = datetime.now()

        days_back = (end_date - start_date).days + 1
        logger.info(f"Fetching Amazon transactions from emails (last {days_back} days)")

        # Fetch emails
        emails = self.fetch_order_emails(days_back)

        # Parse each email
        transactions = []
        for email in emails:
            transaction = self.parse_order_email(email)
            if transaction:
                # Filter by date range
                if transaction.get('date'):
                    if start_date <= transaction['date'] <= end_date:
                        transactions.append(transaction)
                else:
                    # If no date, use email date (today)
                    transaction['date'] = datetime.now()
                    transactions.append(transaction)

        # Sort by date descending
        transactions.sort(key=lambda x: x.get('date', datetime.now()), reverse=True)

        logger.info(f"Parsed {len(transactions)} transactions from emails")
        return transactions

    # =========================================================================
    # New Multi-Source Methods (for EmailMessage objects)
    # =========================================================================

    def parse_email_messages(
        self,
        messages: List[Any],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Parse Amazon transactions from EmailMessage objects.

        This is the new entry point for multi-account email service integration.

        Args:
            messages: List of EmailMessage objects from any email client
            start_date: Optional start date filter
            end_date: Optional end date filter (default: now)

        Returns:
            List of transaction dictionaries
        """
        if not messages:
            return []

        if not end_date:
            end_date = datetime.now()

        transactions = []

        for message in messages:
            try:
                transaction = self.parse_email_message(message)
                if transaction:
                    # Apply date filter if specified
                    tx_date = transaction.get('date', datetime.now())
                    if start_date and tx_date < start_date:
                        continue
                    if end_date and tx_date > end_date:
                        continue

                    # Track source account if available
                    if hasattr(message, 'headers'):
                        source = message.headers.get('x-source-account', 'unknown')
                        transaction['source_account'] = source

                    transactions.append(transaction)
            except Exception as e:
                logger.error(f"Error parsing email message: {e}")
                continue

        # Sort by date descending
        transactions.sort(key=lambda x: x.get('date', datetime.now()), reverse=True)

        logger.info(f"Parsed {len(transactions)} transactions from {len(messages)} email messages")
        return transactions

    def parse_email_message(self, message: Any) -> Optional[Dict]:
        """
        Parse a single EmailMessage object into a transaction.

        Args:
            message: EmailMessage object from email client

        Returns:
            Transaction dictionary or None
        """
        try:
            # Get subject and check if it's an Amazon order email
            subject = getattr(message, 'subject', '') or ''
            if not any(keyword in subject.lower() for keyword in [
                'order', 'shipment', 'delivered', 'amazon.com', 'your amazon'
            ]):
                logger.debug(f"Skipping non-order email: {subject[:50]}...")
                return None

            # Get email body (prefer HTML)
            body_html = getattr(message, 'body_html', None)
            body_text = getattr(message, 'body_text', None)

            if not body_html and not body_text:
                logger.debug(f"No body content for email: {subject[:50]}...")
                return None

            # Parse HTML content if available
            if body_html:
                soup = BeautifulSoup(body_html, 'html.parser')
            else:
                # Create minimal soup from text
                soup = BeautifulSoup(f"<html><body>{body_text}</body></html>", 'html.parser')

            # Extract order details
            order_data = self._extract_order_details(soup, subject)

            if not order_data:
                logger.debug(f"Could not extract order details from: {subject[:50]}...")
                return None

            # Use message date if not extracted from content
            message_date = getattr(message, 'date', None)
            if not order_data.get('date') and message_date:
                order_data['date'] = message_date

            # Add sender info
            sender = getattr(message, 'sender', '')
            order_data['email_sender'] = sender

            # Add message ID for reference
            message_id = getattr(message, 'id', '')
            order_data['email_message_id'] = message_id

            logger.info(f"Parsed order: {order_data.get('order_id', 'Unknown')} - ${order_data.get('total', 0)}")
            return order_data

        except Exception as e:
            logger.error(f"Failed to parse email message: {e}")
            return None

    def get_transactions_from_messages(
        self,
        messages: List[Any],
        days_back: int = 30
    ) -> List[Dict]:
        """
        Convenience method to get transactions from email messages with date range.

        Args:
            messages: List of EmailMessage objects
            days_back: Number of days to include

        Returns:
            List of transaction dictionaries
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        return self.parse_email_messages(
            messages=messages,
            start_date=start_date,
            end_date=end_date
        )
"""
Email Report Generator

Creates beautifully formatted HTML emails for transaction review with
smart suggestions and action links.
"""

import logging
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import base64
import re

from ynab_service import Transaction
from suggestion_engine import CategorySuggestion
from split_analyzer import SplitSuggestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Clean text-based labels (no icons - better email compatibility)
ICONS = {
    'hourglass': '',
    'folder': '',
    'calendar': '',
    'credit_card': '',
    'note': '',
    'robot': '',
    'scissors': '',
    'check': '',
    'link': '',
    'check_circle': '<div style="width: 80px; height: 80px; line-height: 80px; text-align: center; background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); color: white; border-radius: 50%; font-size: 40px; margin: 0 auto 20px auto; font-weight: bold;">&#10003;</div>',
}


class EmailGenerator:
    """Generates and sends transaction review emails"""

    def __init__(self, email_service, action_base_url: Optional[str] = None, budget_id: Optional[str] = None):
        """
        Initialize email generator

        Args:
            email_service: Email service instance (GmailService or SESEmailService)
            action_base_url: Base URL for action links (for Lambda deployment)
            budget_id: YNAB budget ID for generating links
        """
        self.email_service = email_service
        self.action_base_url = action_base_url or "https://your-api-gateway-url.com/actions"
        self.budget_id = budget_id
        # Custom web app URL for deep linking (defaults to None, uses YNAB URLs if not set)
        self.web_app_url = os.getenv('YNAB_WEB_APP_URL')

    def generate_and_send_review_email(self,
                                      to_email: str,
                                      transactions: List[Transaction],
                                      suggestions: Dict[str, List[CategorySuggestion]],
                                      split_suggestions: Dict[str, List[SplitSuggestion]],
                                      unapproved_transactions: List[Transaction] = None,
                                      unapproved_suggestions: Dict[str, List[CategorySuggestion]] = None,
                                      unapproved_splits: Dict[str, List[SplitSuggestion]] = None,
                                      is_sunday: bool = False) -> bool:
        """
        Generate and send the review email

        Args:
            to_email: Recipient email address
            transactions: List of uncategorized transactions
            suggestions: Dictionary of transaction_id -> category suggestions
            split_suggestions: Dictionary of transaction_id -> split suggestions
            unapproved_transactions: List of transactions needing approval
            unapproved_suggestions: Dictionary of transaction_id -> category suggestions for unapproved
            unapproved_splits: Dictionary of transaction_id -> split suggestions for unapproved
            is_sunday: Whether today is Sunday (includes Saturday transactions)

        Returns:
            True if sent successfully
        """
        # Initialize optional parameters
        unapproved_transactions = unapproved_transactions or []
        unapproved_suggestions = unapproved_suggestions or {}
        unapproved_splits = unapproved_splits or {}

        if not transactions and not unapproved_transactions:
            logger.info("No transactions to review, skipping email")
            return True

        # Generate summary statistics
        summary_stats = self._calculate_summary_stats(
            transactions, is_sunday, unapproved_transactions
        )

        # Skip uncategorized transactions - only show unapproved
        # Generate unapproved transactions HTML
        combined_html = ""
        if unapproved_transactions:
            combined_html = self._generate_unapproved_section_html(
                unapproved_transactions,
                unapproved_suggestions,
                unapproved_splits,
                is_sunday
            )

        # Send email
        return self.email_service.send_transaction_review_email(
            to_email=to_email,
            transactions_html=combined_html,
            summary_stats=summary_stats
        )

    def _calculate_summary_stats(self, transactions: List[Transaction], is_sunday: bool,
                                  unapproved_transactions: List[Transaction] = None) -> Dict:
        """Calculate summary statistics for email"""
        unapproved_transactions = unapproved_transactions or []

        total_amount = sum(abs(t.amount) for t in transactions)
        unapproved_amount = sum(abs(t.amount) for t in unapproved_transactions)

        # Group by account (combine both lists)
        accounts = set(t.account_name for t in transactions)
        accounts.update(t.account_name for t in unapproved_transactions)

        # Find oldest transaction (from both lists)
        all_transactions = transactions + unapproved_transactions
        oldest_days = 0
        if all_transactions:
            oldest_date = min(datetime.strptime(t.date, '%Y-%m-%d') for t in all_transactions)
            oldest_days = (datetime.now() - oldest_date).days

        # Count Saturday vs Sunday if applicable
        saturday_count = 0
        sunday_count = 0
        if is_sunday:
            for t in transactions:
                txn_date = datetime.strptime(t.date, '%Y-%m-%d')
                if txn_date.weekday() == 5:  # Saturday
                    saturday_count += 1
                else:
                    sunday_count += 1

        # Group unapproved transactions by month
        unapproved_by_month = defaultdict(int)
        for t in unapproved_transactions:
            month_key = datetime.strptime(t.date, '%Y-%m-%d').strftime('%B %Y')
            unapproved_by_month[month_key] += 1

        # Count Amazon transactions needing approval
        amazon_pattern = re.compile(r'amazon|amzn', re.IGNORECASE)
        amazon_unapproved_count = sum(
            1 for t in unapproved_transactions
            if amazon_pattern.search(t.payee_name or '')
        )

        stats = {
            'total_count': len(transactions),
            'total_amount': total_amount,
            'accounts_affected': len(accounts),
            'oldest_days': oldest_days,
            'is_sunday': is_sunday,
            'saturday_count': saturday_count,
            'sunday_count': sunday_count,
            'unapproved_count': len(unapproved_transactions),
            'unapproved_amount': unapproved_amount,
            'unapproved_by_month': dict(unapproved_by_month),
            'amazon_unapproved_count': amazon_unapproved_count
        }

        return stats

    def _generate_transactions_html(self,
                                   transactions: List[Transaction],
                                   suggestions: Dict[str, List[CategorySuggestion]],
                                   split_suggestions: Dict[str, List[SplitSuggestion]],
                                   is_sunday: bool) -> str:
        """Generate HTML for transactions section"""
        html_parts = []

        # Group by date if Sunday (to separate Saturday/Sunday)
        if is_sunday:
            saturday_txns = []
            other_txns = []

            for t in transactions:
                txn_date = datetime.strptime(t.date, '%Y-%m-%d')
                if txn_date.weekday() == 5:  # Saturday
                    saturday_txns.append(t)
                else:
                    other_txns.append(t)

            if saturday_txns:
                html_parts.append('<h3 style="color: #6c757d; margin-top: 20px;">Saturday Transactions</h3>')
                for txn in saturday_txns:
                    html_parts.append(self._generate_transaction_html(txn, suggestions, split_suggestions))

            if other_txns:
                html_parts.append('<h3 style="color: #6c757d; margin-top: 20px;">Today\'s Transactions</h3>')
                for txn in other_txns:
                    html_parts.append(self._generate_transaction_html(txn, suggestions, split_suggestions))
        else:
            # Regular day - just list all transactions
            for i, txn in enumerate(transactions, 1):
                html_parts.append(self._generate_transaction_html(txn, suggestions, split_suggestions, i))

        return '\n'.join(html_parts)

    def _generate_unapproved_section_html(self,
                                          transactions: List[Transaction],
                                          suggestions: Dict[str, List[CategorySuggestion]],
                                          split_suggestions: Dict[str, List[SplitSuggestion]],
                                          is_sunday: bool) -> str:
        """Generate HTML for unapproved transactions section"""
        if not transactions:
            return ""

        html_parts = []

        # Section header with clean styling
        html_parts.append(f'''
        <div style="margin-top: 24px;">
            <h2 style="color: #1e293b; margin: 0 0 8px 0; font-size: 18px; font-weight: 600;">
                Transactions Needing Approval
            </h2>
            <p style="color: #64748b; margin: 0 0 20px 0; font-size: 14px;">
                Review and approve these imported transactions in YNAB.
            </p>
        ''')

        # Group by date if Sunday (to separate Saturday/Sunday)
        if is_sunday:
            saturday_txns = []
            other_txns = []

            for t in transactions:
                txn_date = datetime.strptime(t.date, '%Y-%m-%d')
                if txn_date.weekday() == 5:  # Saturday
                    saturday_txns.append(t)
                else:
                    other_txns.append(t)

            if saturday_txns:
                html_parts.append('<h3 style="color: #6c757d; margin-top: 20px;">Saturday Transactions</h3>')
                for txn in saturday_txns:
                    html_parts.append(self._generate_unapproved_transaction_html(txn, suggestions, split_suggestions))

            if other_txns:
                html_parts.append('<h3 style="color: #6c757d; margin-top: 20px;">Today\'s Transactions</h3>')
                for txn in other_txns:
                    html_parts.append(self._generate_unapproved_transaction_html(txn, suggestions, split_suggestions))
        else:
            # Regular day - sort by date descending (most recent first) and list with alternating colors
            sorted_transactions = sorted(transactions, key=lambda t: t.date, reverse=True)
            for idx, txn in enumerate(sorted_transactions):
                html_parts.append(self._generate_unapproved_transaction_html(txn, suggestions, split_suggestions, idx))

        html_parts.append('</div>')

        return '\n'.join(html_parts)

    def _generate_unapproved_transaction_html(self,
                                              transaction: Transaction,
                                              suggestions: Dict[str, List[CategorySuggestion]],
                                              split_suggestions: Dict[str, List[SplitSuggestion]],
                                              index: int = 0) -> str:
        """Generate HTML for a single unapproved transaction"""
        # Format amount
        amount_class = "positive" if transaction.amount > 0 else ""
        amount_str = f"${abs(transaction.amount):,.2f}"
        if transaction.amount > 0:
            amount_str = f"+{amount_str}"
        else:
            amount_str = f"-{amount_str}"

        # Get suggestions for this transaction
        txn_suggestions = suggestions.get(transaction.id, [])
        txn_splits = split_suggestions.get(transaction.id, [])

        # Generate action token for security
        action_token = self._generate_action_token(transaction.id)

        # Alternating row colors for better readability
        bg_color = "#ffffff" if index % 2 == 0 else "#f9fafb"

        # Show category if assigned (unapproved transactions often have categories)
        category_display = ""
        if transaction.category_name:
            category_display = f'<span style="background: #dcfce7; color: #166534; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 500;">{transaction.category_name}</span>'

        html = f"""
        <div style="background: {bg_color}; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="vertical-align: top;">
                        <div style="font-size: 17px; font-weight: 600; color: #1e293b; margin-bottom: 6px;">{transaction.payee_name}</div>
                        <div style="font-size: 13px; color: #64748b; margin-bottom: 10px;">
                            {transaction.date} &bull; {transaction.account_name}
                            {f' &bull; {transaction.memo}' if transaction.memo else ''}
                        </div>
                        <div style="display: inline-block;">
                            {category_display}
                            <span style="background: #fef3c7; color: #92400e; padding: 5px 12px; border-radius: 6px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; margin-left: 6px;">Pending</span>
                        </div>
                    </td>
                    <td style="vertical-align: top; text-align: right; width: 120px;">
                        <div style="font-size: 22px; font-weight: 700; color: {'#16a34a' if transaction.amount > 0 else '#dc2626'};">{amount_str}</div>
                    </td>
                </tr>
            </table>
        """

        # Add suggestions if available (for validation/context)
        if txn_suggestions:
            html += f"""
            <div style="background: #f8fafc; border-radius: 8px; padding: 14px; margin-top: 16px;">
                <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; margin-bottom: 10px;">
                    Suggested Categories
                </div>
            """

            for suggestion in txn_suggestions[:3]:  # Show top 3
                conf_color = '#16a34a' if suggestion.confidence >= 80 else ('#d97706' if suggestion.confidence >= 60 else '#dc2626')
                html += f"""
                <div style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <span style="font-weight: 600; color: #1e293b;">{suggestion.category_name}</span>
                    <span style="background: {'#dcfce7' if suggestion.confidence >= 80 else ('#fef3c7' if suggestion.confidence >= 60 else '#fee2e2')}; color: {conf_color}; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-left: 8px;">{suggestion.confidence:.0f}%</span>
                    <div style="font-size: 12px; color: #64748b; margin-top: 4px;">{suggestion.reason}</div>
                </div>
                """

            html += "</div>"

        # Add split suggestions if available
        if txn_splits:
            html += f"""
            <div style="background: #fff7ed; border-radius: 8px; padding: 14px; margin-top: 12px;">
                <div style="font-size: 11px; color: #9a3412; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; margin-bottom: 10px;">
                    Suggested Split
                </div>
            """

            for split in txn_splits:
                html += f"""
                <div style="padding: 6px 0;">
                    <span style="font-weight: 600; color: #1e293b;">{split.category_name}</span>
                    <span style="color: #ea580c; font-weight: 600; margin-left: 8px;">${abs(split.amount):.2f}</span>
                    <div style="font-size: 12px; color: #64748b; margin-top: 2px;">{split.memo}</div>
                </div>
                """

            html += "</div>"

        # Add action button
        transaction_url = self._get_transaction_url(transaction)
        button_text = "Review in YNAB" if not self.web_app_url else "Review & Approve"
        html += f"""
            <div style="margin-top: 16px;">
                <a href="{transaction_url}" style="display: inline-block; background: #374151; color: #ffffff; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 600; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);" target="_blank">
                    {button_text}
                </a>
            </div>
        </div>
        """

        return html

    def _generate_transaction_html(self,
                                  transaction: Transaction,
                                  suggestions: Dict[str, List[CategorySuggestion]],
                                  split_suggestions: Dict[str, List[SplitSuggestion]],
                                  number: Optional[int] = None) -> str:
        """Generate HTML for a single transaction"""
        # Format amount
        amount_class = "positive" if transaction.amount > 0 else ""
        amount_str = f"${abs(transaction.amount):,.2f}"
        if transaction.amount > 0:
            amount_str = f"+{amount_str}"
        else:
            amount_str = f"-{amount_str}"

        # Get suggestions for this transaction
        txn_suggestions = suggestions.get(transaction.id, [])
        txn_splits = split_suggestions.get(transaction.id, [])

        # Generate action token for security
        action_token = self._generate_action_token(transaction.id)

        html = f"""
        <div class="transaction">
            <div class="transaction-header">
                <div>
                    <div class="transaction-payee">{transaction.payee_name}</div>
                    <div class="transaction-details">
                        {ICONS['calendar']} {transaction.date} &bull; {ICONS['credit_card']} {transaction.account_name}
                        {f' &bull; {ICONS["note"]} {transaction.memo}' if transaction.memo else ''}
                    </div>
                </div>
                <div class="transaction-amount {amount_class}">{amount_str}</div>
            </div>
        """

        # Add suggestions if available
        if txn_suggestions:
            html += f"""
            <div class="suggestion-box">
                <div class="suggestion-header">
                    {ICONS['robot']} SMART SUGGESTIONS
                </div>
            """

            for suggestion in txn_suggestions[:3]:  # Show top 3
                confidence_class = self._get_confidence_class(suggestion.confidence)
                html += f"""
                <div class="suggestion-item">
                    <strong>{suggestion.category_name}</strong>
                    <span class="confidence {confidence_class}">{suggestion.confidence:.0f}% confidence</span>
                    <br>
                    <span style="font-size: 12px; color: #6c757d;">{suggestion.reason}</span>
                </div>
                """

            html += "</div>"

        # Add split suggestions if available
        if txn_splits:
            html += f"""
            <div class="suggestion-box">
                <div class="suggestion-header" style="color: #f57c00;">
                    {ICONS['scissors']} SUGGESTED SPLITS
                </div>
            """

            for split in txn_splits:
                html += f"""
                <div class="suggestion-item">
                    <strong>{split.category_name}:</strong> ${abs(split.amount):.2f}
                    <br>
                    <span style="font-size: 12px; color: #6c757d;">{split.memo}</span>
                </div>
                """

            html += "</div>"

        # Add action buttons
        html += """
        <div class="action-buttons">
        """

        # Add categorize button for top suggestion
        if txn_suggestions and txn_suggestions[0].confidence >= 70:
            top_suggestion = txn_suggestions[0]
            action_url = self._generate_action_url(
                'categorize',
                transaction.id,
                top_suggestion.category_id,
                action_token
            )
            html += f"""
            <a href="{action_url}" class="action-button">
                {ICONS['check']} Categorize as {top_suggestion.category_name}
            </a>
            """

        # Add split button if suggested
        if txn_splits:
            action_url = self._generate_action_url(
                'split',
                transaction.id,
                None,
                action_token
            )
            html += f"""
            <a href="{action_url}" class="action-button secondary">
                {ICONS['scissors']} Apply Suggested Split
            </a>
            """

        # Add view/edit button - uses custom web app if configured
        transaction_url = self._get_transaction_url(transaction)
        button_text = "Edit Transaction" if self.web_app_url else "View in YNAB"
        html += f"""
            <a href="{transaction_url}" class="action-button secondary" target="_blank">
                {ICONS['link']} {button_text}
            </a>
        """

        html += """
        </div>
        </div>
        """

        return html

    def _get_confidence_class(self, confidence: float) -> str:
        """Get CSS class for confidence level"""
        if confidence >= 80:
            return "high"
        elif confidence >= 60:
            return "medium"
        else:
            return "low"

    def _get_transaction_url(self, transaction: Transaction) -> str:
        """
        Generate URL for viewing/editing a transaction.

        If YNAB_WEB_APP_URL is set, uses the custom web app for deep linking.
        Otherwise, falls back to YNAB's account-level URL.
        """
        if self.web_app_url:
            # Use custom web app for true deep linking
            return f"{self.web_app_url}/transactions/{transaction.id}"
        elif self.budget_id:
            # Fall back to YNAB account-level URL
            return f"https://app.ynab.com/{self.budget_id}/accounts/{transaction.account_id}"
        else:
            return "https://app.ynab.com"

    def _generate_action_token(self, transaction_id: str) -> str:
        """Generate secure action token"""
        # In production, use a proper secret and include timestamp
        secret = "your-secret-key"  # Should come from environment
        data = f"{transaction_id}:{secret}"
        hash_obj = hashlib.sha256(data.encode())
        return base64.urlsafe_b64encode(hash_obj.digest()[:16]).decode()

    def _generate_action_url(self,
                            action: str,
                            transaction_id: str,
                            category_id: Optional[str],
                            token: str) -> str:
        """Generate action URL for one-click categorization"""
        params = [
            f"action={action}",
            f"txn={transaction_id}",
            f"token={token}"
        ]

        if category_id:
            params.append(f"cat={category_id}")

        return f"{self.action_base_url}?{'&'.join(params)}"

    def send_no_transactions_email(self, to_email: str) -> bool:
        """Send email when there are no uncategorized transactions"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    text-align: center;
                }}
                .checkmark {{
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #2c3e50;
                    margin: 20px 0;
                }}
                p {{
                    color: #7f8c8d;
                    font-size: 16px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="checkmark">{ICONS['check_circle']}</div>
                <h1>All Caught Up!</h1>
                <p>Great job! All your YNAB transactions are categorized.</p>
                <p style="margin-top: 30px; font-size: 14px;">
                    No review needed today. Enjoy your evening!
                </p>
            </div>
        </body>
        </html>
        """

        return self.email_service.send_email(
            to=to_email,
            subject="[YNAB Review] All transactions categorized!",
            html_body=html
        )
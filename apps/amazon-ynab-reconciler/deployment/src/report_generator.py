"""
Report generator for creating and sending reconciliation email summaries.
Generates HTML reports with match details and statistics.
"""

import os
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# Add parent directory to path to import from other apps
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate and send reconciliation reports."""

    def __init__(self, config: Dict):
        """Initialize the report generator."""
        self.config = config
        self.enabled = config.get('enabled', True)
        self.recipient = config.get('recipient') or os.getenv('EMAIL_RECIPIENT')
        self.subject_template = config.get('subject', 'Amazon-YNAB Reconciliation Report - {date}')
        self.include_details = config.get('include_details', True)
        self.only_on_activity = config.get('only_on_activity', False)

        # Try to import email sender from love-brittany-tracker
        self.email_sender = None
        if self.enabled:
            try:
                from apps.love_brittany_tracker.src.email_sender import EmailSender
                self.email_sender = EmailSender()
                logger.info("Email sender initialized successfully")
            except ImportError:
                logger.warning("Could not import EmailSender, email reports disabled")
                self.enabled = False

    def validate_config(self) -> bool:
        """Validate email configuration."""
        if not self.enabled:
            return True  # Valid if disabled

        if not self.recipient:
            logger.error("Email recipient not configured")
            return False

        if not self.email_sender:
            logger.error("Email sender not available")
            return False

        return True

    def send_report(self, results: Dict) -> bool:
        """
        Generate and send reconciliation report.

        Args:
            results: Reconciliation results dictionary

        Returns:
            True if report sent successfully
        """
        if not self.enabled:
            logger.info("Email reports disabled")
            return True

        # Check if we should skip based on activity
        if self.only_on_activity:
            if not results['matches'] and not results['errors']:
                logger.info("No activity to report, skipping email")
                return True

        try:
            # Generate report HTML
            html_content = self._generate_html_report(results)

            # Generate subject
            subject = self.subject_template.format(
                date=datetime.now().strftime('%Y-%m-%d')
            )

            # Send email
            if self.email_sender:
                self.email_sender.send_email(
                    to=self.recipient,
                    subject=subject,
                    html_content=html_content
                )
                logger.info(f"Reconciliation report sent to {self.recipient}")
                return True
            else:
                # Fall back to saving report locally
                self._save_local_report(html_content)
                return True

        except Exception as e:
            logger.error(f"Failed to send report: {str(e)}")
            return False

    def _generate_html_report(self, results: Dict) -> str:
        """
        Generate HTML report from results.

        Args:
            results: Reconciliation results

        Returns:
            HTML content string
        """
        # Calculate statistics
        duration = results.get('duration', 0)
        matches = results.get('matches', [])
        unmatched_amazon = results.get('unmatched_amazon', [])
        unmatched_ynab = results.get('unmatched_ynab', [])
        errors = results.get('errors', [])

        # Calculate match statistics
        if matches:
            avg_confidence = sum(m['confidence'] for m in matches) / len(matches)
            high_confidence = sum(1 for m in matches if m['confidence'] >= 90)
            medium_confidence = sum(1 for m in matches if 70 <= m['confidence'] < 90)
            low_confidence = sum(1 for m in matches if m['confidence'] < 70)
        else:
            avg_confidence = 0
            high_confidence = medium_confidence = low_confidence = 0

        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Amazon-YNAB Reconciliation Report</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 900px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    padding: 30px;
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #34495e;
                    margin-top: 30px;
                    border-bottom: 1px solid #ecf0f1;
                    padding-bottom: 5px;
                }}
                .summary-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }}
                .stat-card {{
                    background: #f8f9fa;
                    border-radius: 6px;
                    padding: 15px;
                    border-left: 4px solid #3498db;
                }}
                .stat-value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #2c3e50;
                }}
                .stat-label {{
                    font-size: 12px;
                    color: #7f8c8d;
                    text-transform: uppercase;
                    margin-top: 5px;
                }}
                .success {{ color: #27ae60; }}
                .warning {{ color: #f39c12; }}
                .error {{ color: #e74c3c; }}
                .info {{ color: #3498db; }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th {{
                    background: #34495e;
                    color: white;
                    padding: 12px;
                    text-align: left;
                }}
                td {{
                    padding: 10px 12px;
                    border-bottom: 1px solid #ecf0f1;
                }}
                tr:nth-child(even) {{
                    background: #f8f9fa;
                }}
                .confidence-high {{ background: #d4edda !important; }}
                .confidence-medium {{ background: #fff3cd !important; }}
                .confidence-low {{ background: #f8d7da !important; }}
                .match-details {{
                    font-size: 12px;
                    color: #6c757d;
                }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #ecf0f1;
                    text-align: center;
                    color: #7f8c8d;
                    font-size: 12px;
                }}
                .alert {{
                    padding: 15px;
                    border-radius: 4px;
                    margin: 20px 0;
                }}
                .alert-error {{
                    background: #f8d7da;
                    color: #721c24;
                    border: 1px solid #f5c6cb;
                }}
                .alert-warning {{
                    background: #fff3cd;
                    color: #856404;
                    border: 1px solid #ffeeba;
                }}
                .alert-success {{
                    background: #d4edda;
                    color: #155724;
                    border: 1px solid #c3e6cb;
                }}
                .badge {{
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                    font-weight: bold;
                    margin-left: 5px;
                }}
                .badge-success {{ background: #27ae60; color: white; }}
                .badge-warning {{ background: #f39c12; color: white; }}
                .badge-danger {{ background: #e74c3c; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Amazon-YNAB Reconciliation Report</h1>
                <p><strong>Generated:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                <p><strong>Processing Time:</strong> {duration:.2f} seconds</p>
                <p><strong>Lookback Period:</strong> {results.get('lookback_days', 30)} days</p>

                <h2>Summary</h2>
                <div class="summary-grid">
                    <div class="stat-card">
                        <div class="stat-value">{len(results['amazon_transactions'])}</div>
                        <div class="stat-label">Amazon Transactions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{len(results['ynab_transactions'])}</div>
                        <div class="stat-label">YNAB Transactions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value success">{len(matches)}</div>
                        <div class="stat-label">Successful Matches</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{results.get('updates_applied', 0)}</div>
                        <div class="stat-label">Updates Applied</div>
                    </div>
                </div>
        """

        # Add match confidence breakdown
        if matches:
            html += f"""
                <h2>Match Confidence</h2>
                <div class="summary-grid">
                    <div class="stat-card">
                        <div class="stat-value">{avg_confidence:.1f}%</div>
                        <div class="stat-label">Average Confidence</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value success">{high_confidence}</div>
                        <div class="stat-label">High Confidence (90%+)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value warning">{medium_confidence}</div>
                        <div class="stat-label">Medium (70-89%)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value error">{low_confidence}</div>
                        <div class="stat-label">Low (<70%)</div>
                    </div>
                </div>
            """

        # Add errors if any
        if errors:
            html += f"""
                <div class="alert alert-error">
                    <strong>⚠️ Errors Encountered:</strong>
                    <ul>
            """
            for error in errors:
                html += f"<li>{error}</li>"
            html += "</ul></div>"

        # Add matched transactions table
        if matches and self.include_details:
            html += self._generate_matches_table(matches)

        # Add unmatched transactions
        if unmatched_amazon or unmatched_ynab:
            html += self._generate_unmatched_section(unmatched_amazon, unmatched_ynab)

        # Add footer
        html += f"""
                <div class="footer">
                    <p>Amazon-YNAB Reconciliation System v1.0</p>
                    <p>Report generated automatically • Terrance Brandon</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _generate_matches_table(self, matches: List[Dict]) -> str:
        """Generate HTML table for matched transactions."""
        html = """
            <h2>Matched Transactions</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Amount</th>
                        <th>Amazon Item</th>
                        <th>YNAB Payee</th>
                        <th>Confidence</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
        """

        for match in matches[:50]:  # Limit to 50 for email size
            confidence_class = ''
            if match['confidence'] >= 90:
                confidence_class = 'confidence-high'
                badge_class = 'badge-success'
            elif match['confidence'] >= 70:
                confidence_class = 'confidence-medium'
                badge_class = 'badge-warning'
            else:
                confidence_class = 'confidence-low'
                badge_class = 'badge-danger'

            html += f"""
                <tr class="{confidence_class}">
                    <td>{match['amazon_date'].strftime('%b %d')}</td>
                    <td>${match['amazon_total']:.2f}</td>
                    <td>
                        {match['amazon_data']['item_name']}
                        <div class="match-details">
                            Category: {match['amazon_data']['category']}
                        </div>
                    </td>
                    <td>
                        {match['ynab_data']['payee_name']}
                        <div class="match-details">
                            {match['ynab_data']['account_name']}
                        </div>
                    </td>
                    <td>
                        {match['confidence']:.1f}%
                        <span class="badge {badge_class}">
                            {match['date_diff_days']}d, ${match['amount_diff_cents']/100:.2f}
                        </span>
                    </td>
                    <td>
                        <span class="success">✓ Updated</span>
                    </td>
                </tr>
            """

        html += """
                </tbody>
            </table>
        """

        if len(matches) > 50:
            html += f"<p><em>Showing first 50 of {len(matches)} matches</em></p>"

        return html

    def _generate_unmatched_section(
        self,
        unmatched_amazon: List[Dict],
        unmatched_ynab: List[Dict]
    ) -> str:
        """Generate HTML section for unmatched transactions."""
        html = "<h2>Unmatched Transactions</h2>"

        if unmatched_amazon:
            html += f"""
                <div class="alert alert-warning">
                    <strong>📦 {len(unmatched_amazon)} Amazon transactions</strong> could not be matched to YNAB.
                    Total: ${sum(t['total'] for t in unmatched_amazon):.2f}
                </div>
            """

        if unmatched_ynab:
            html += f"""
                <div class="alert alert-warning">
                    <strong>💳 {len(unmatched_ynab)} YNAB transactions</strong> could not be matched to Amazon.
                    Total: ${sum(t['amount'] for t in unmatched_ynab):.2f}
                </div>
            """

        return html

    def _save_local_report(self, html_content: str):
        """Save report locally if email sending fails."""
        reports_dir = Path(__file__).parent.parent / 'reports'
        reports_dir.mkdir(exist_ok=True)

        filename = f"reconciliation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = reports_dir / filename

        with open(filepath, 'w') as f:
            f.write(html_content)

        logger.info(f"Report saved locally: {filepath}")
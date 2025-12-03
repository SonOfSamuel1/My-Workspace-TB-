"""
Budget Report Generator

Generates HTML email reports from budget analysis data using Jinja2 templates.
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import pytz
from jinja2 import Environment, FileSystemLoader, select_autoescape


class BudgetReportGenerator:
    """Generates HTML email reports from budget data."""

    def __init__(self, config: Dict, template_dir: Optional[str] = None):
        """Initialize report generator.

        Args:
            config: Configuration dictionary
            template_dir: Optional path to templates directory
        """
        self.logger = logging.getLogger(__name__)
        self.config = config

        # Setup Jinja2 environment
        if template_dir is None:
            template_dir = Path(__file__).parent / 'templates'
        else:
            template_dir = Path(template_dir)

        self.template_dir = template_dir
        self.use_templates = template_dir.exists()

        if self.use_templates:
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            # Add custom filters
            self.jinja_env.filters['format_currency'] = self._format_currency
            # Add custom functions
            self.jinja_env.globals['get_pace_status'] = self._get_pace_status
            self.logger.info(f"Using Jinja2 templates from {template_dir}")
        else:
            self.jinja_env = None
            self.logger.info("Templates not found, using legacy HTML generation")

    def _format_currency(self, value: float, decimals: int = 2) -> str:
        """Format a number as currency."""
        if decimals == 0:
            return f"${value:,.0f}"
        return f"${value:,.{decimals}f}"

    def _get_pace_status(self, pct_used: float, days_elapsed: int, total_days: int) -> str:
        """Determine pace status for template use."""
        if total_days == 0:
            return 'ok'
        expected_pct = (days_elapsed / total_days) * 100
        pace_ratio = pct_used / expected_pct if expected_pct > 0 else 0

        if pace_ratio >= 1.0:
            return 'danger'
        elif pace_ratio >= 0.8:
            return 'warning'
        elif pace_ratio < 0.5:
            return 'under'
        return 'ok'

    def generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML email report.

        Args:
            report_data: Report data dictionary with analysis results

        Returns:
            HTML string for email body
        """
        self.logger.info("Generating HTML budget report...")

        # Use Jinja2 templates if available
        if self.use_templates:
            return self._generate_with_templates(report_data)

        # Fall back to legacy HTML generation
        return self._generate_legacy_html(report_data)

    def generate_annual_report(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML annual budget report with Tiller-style dashboard.

        Args:
            report_data: Report data dictionary with analysis results including:
                - period: Weekly period info
                - analysis: Weekly transaction analysis
                - budget_comparison: Weekly budget comparison
                - alerts: Weekly + annual alerts
                - annual_budget: Annual budget summary
                - ytd_spending: Year-to-date spending analysis
                - projections: Year-end projections

        Returns:
            HTML string for email body
        """
        self.logger.info("Generating annual budget report...")

        if not self.use_templates:
            self.logger.warning("Templates not available, falling back to weekly report")
            return self.generate_html_report(report_data)

        template = self.jinja_env.get_template('annual_report.html')

        # Prepare context
        context = {
            'title': f"{report_data.get('annual_budget', {}).get('year', '')} Annual Budget Report",
            'period': report_data.get('period', {}),
            'summary': report_data.get('analysis', {}).get('summary', {}),
            'alerts': report_data.get('alerts', []),
            'budget_comparison': report_data.get('budget_comparison', {}),
            'category_breakdown': report_data.get('analysis', {}).get('category_breakdown', []),
            'payee_breakdown': report_data.get('analysis', {}).get('payee_breakdown', []),
            'notable_transactions': report_data.get('analysis', {}).get('notable_transactions', []),
            'account_breakdown': report_data.get('analysis', {}).get('account_breakdown', []),
            'annual_budget': report_data.get('annual_budget', {}),
            'ytd_spending': report_data.get('ytd_spending', {}),
            'projections': report_data.get('projections', {}),
            'current_date': datetime.now().strftime('%B %d, %Y'),
            'generated_at': datetime.now().strftime('%B %d, %Y at %I:%M %p')
        }

        return template.render(**context)

    def _generate_with_templates(self, report_data: Dict[str, Any]) -> str:
        """Generate report using Jinja2 templates."""
        template = self.jinja_env.get_template('weekly_report.html')

        # Prepare context
        context = {
            'title': 'Weekly Budget Report',
            'period': report_data.get('period', {}),
            'summary': report_data.get('analysis', {}).get('summary', {}),
            'alerts': report_data.get('alerts', []),
            'budget_comparison': report_data.get('budget_comparison', {}),
            'category_breakdown': report_data.get('analysis', {}).get('category_breakdown', []),
            'payee_breakdown': report_data.get('analysis', {}).get('payee_breakdown', []),
            'notable_transactions': report_data.get('analysis', {}).get('notable_transactions', []),
            'account_breakdown': report_data.get('analysis', {}).get('account_breakdown', []),
            'generated_at': datetime.now().strftime('%B %d, %Y at %I:%M %p')
        }

        return template.render(**context)

    def _generate_legacy_html(self, report_data: Dict[str, Any]) -> str:
        """Generate report using legacy inline HTML (fallback)."""
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
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
        }}
        .summary-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .summary-stat {{
            display: inline-block;
            margin: 10px 20px 10px 0;
        }}
        .summary-label {{
            font-size: 14px;
            opacity: 0.9;
            display: block;
        }}
        .summary-value {{
            font-size: 32px;
            font-weight: bold;
            display: block;
        }}
        .alert {{
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        .alert-critical {{
            background-color: #fee;
            border-left: 4px solid #e74c3c;
            color: #c0392b;
        }}
        .alert-warning {{
            background-color: #ffeaa7;
            border-left: 4px solid #fdcb6e;
            color: #d63031;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background-color: #34495e;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ecf0f1;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .amount {{
            font-weight: 600;
            font-family: 'Courier New', monospace;
        }}
        .positive {{
            color: #27ae60;
        }}
        .negative {{
            color: #e74c3c;
        }}
        .progress-bar {{
            background-color: #ecf0f1;
            border-radius: 10px;
            height: 20px;
            overflow: hidden;
            margin: 5px 0;
        }}
        .progress-fill {{
            background-color: #3498db;
            height: 100%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
            font-weight: bold;
        }}
        .progress-fill.over-budget {{
            background-color: #e74c3c;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 14px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-success {{
            background-color: #d4edda;
            color: #155724;
        }}
        .badge-danger {{
            background-color: #f8d7da;
            color: #721c24;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Weekly Budget Report</h1>
        <p><strong>Report Period:</strong> {report_data['period']['start_date']} to {report_data['period']['end_date']}</p>

        {self._generate_alerts_section(report_data.get('alerts', []))}
        {self._generate_summary_section(report_data)}
        {self._generate_budget_comparison_section(report_data.get('budget_comparison', {}))}
        {self._generate_category_section(report_data['analysis']['category_breakdown'])}
        {self._generate_payee_section(report_data['analysis']['payee_breakdown'])}
        {self._generate_notable_transactions_section(report_data['analysis']['notable_transactions'])}
        {self._generate_account_section(report_data['analysis']['account_breakdown'])}

        <div class="footer">
            <p>Generated by YNAB Weekly Budget Report</p>
            <p>Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _generate_alerts_section(self, alerts: list) -> str:
        """Generate alerts section."""
        if not alerts:
            return ""

        html = "<h2>Alerts</h2>"
        for alert in alerts:
            alert_class = f"alert-{alert['level']}"
            html += f"""
            <div class="alert {alert_class}">
                <strong>{alert['category']}:</strong> {alert['message']}
            </div>
            """
        return html

    def _generate_summary_section(self, report_data: Dict) -> str:
        """Generate executive summary section."""
        summary = report_data['analysis']['summary']

        return f"""
        <div class="summary-box">
            <div class="summary-stat">
                <span class="summary-label">Total Spent</span>
                <span class="summary-value">${summary['total_outflow']:,.2f}</span>
            </div>
            <div class="summary-stat">
                <span class="summary-label">Total Income</span>
                <span class="summary-value">${summary['total_inflow']:,.2f}</span>
            </div>
            <div class="summary-stat">
                <span class="summary-label">Net</span>
                <span class="summary-value {'positive' if summary['net'] >= 0 else 'negative'}">
                    ${summary['net']:,.2f}
                </span>
            </div>
            <div class="summary-stat">
                <span class="summary-label">Transactions</span>
                <span class="summary-value">{summary['transaction_count']}</span>
            </div>
        </div>
        """

    def _generate_budget_comparison_section(self, budget_comparison: Dict) -> str:
        """Generate budget vs actual comparison section."""
        if not budget_comparison:
            return ""

        total_budgeted = budget_comparison.get('total_budgeted', 0)
        total_spent = budget_comparison.get('total_spent', 0)
        overall_pct = budget_comparison.get('overall_percentage_used', 0)

        html = f"""
        <h2>Budget vs Actual</h2>
        <div style="margin: 20px 0;">
            <p><strong>Overall Budget Performance:</strong></p>
            <div class="progress-bar">
                <div class="progress-fill {'over-budget' if overall_pct > 100 else ''}"
                     style="width: {min(overall_pct, 100)}%;">
                    {overall_pct:.1f}%
                </div>
            </div>
            <p>Spent: ${total_spent:,.2f} of ${total_budgeted:,.2f} budgeted
               (${budget_comparison.get('total_remaining', 0):,.2f} remaining)</p>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Category</th>
                    <th>Budgeted</th>
                    <th>Spent</th>
                    <th>Remaining</th>
                    <th>% Used</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
        """

        for category in budget_comparison.get('categories', [])[:15]:  # Top 15
            status_badge = 'badge-danger' if category['over_budget'] else 'badge-success'
            status_text = 'Over' if category['over_budget'] else 'OK'

            html += f"""
                <tr>
                    <td>{category['category_name']}</td>
                    <td class="amount">${category['budgeted']:,.2f}</td>
                    <td class="amount">${category['spent']:,.2f}</td>
                    <td class="amount {'negative' if category['remaining'] < 0 else 'positive'}">
                        ${category['remaining']:,.2f}
                    </td>
                    <td>
                        <div class="progress-bar" style="height: 15px;">
                            <div class="progress-fill {'over-budget' if category['percentage_used'] > 100 else ''}"
                                 style="width: {min(category['percentage_used'], 100)}%; font-size: 10px;">
                                {category['percentage_used']:.0f}%
                            </div>
                        </div>
                    </td>
                    <td><span class="badge {status_badge}">{status_text}</span></td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        """
        return html

    def _generate_category_section(self, category_breakdown: list) -> str:
        """Generate category breakdown section."""
        if not category_breakdown:
            return ""

        html = """
        <h2>Spending by Category</h2>
        <table>
            <thead>
                <tr>
                    <th>Category</th>
                    <th>Group</th>
                    <th>Amount</th>
                    <th>Transactions</th>
                </tr>
            </thead>
            <tbody>
        """

        for category in category_breakdown:
            html += f"""
                <tr>
                    <td>{category['category_name']}</td>
                    <td>{category['category_group']}</td>
                    <td class="amount negative">${category['amount']:,.2f}</td>
                    <td>{category['transaction_count']}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        """
        return html

    def _generate_payee_section(self, payee_breakdown: list) -> str:
        """Generate payee breakdown section."""
        if not payee_breakdown:
            return ""

        html = """
        <h2>Top Merchants/Payees</h2>
        <table>
            <thead>
                <tr>
                    <th>Payee</th>
                    <th>Amount</th>
                    <th>Transactions</th>
                </tr>
            </thead>
            <tbody>
        """

        for payee in payee_breakdown:
            html += f"""
                <tr>
                    <td>{payee['payee_name']}</td>
                    <td class="amount negative">${payee['amount']:,.2f}</td>
                    <td>{payee['transaction_count']}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        """
        return html

    def _generate_notable_transactions_section(self, notable: list) -> str:
        """Generate notable transactions section."""
        if not notable:
            return ""

        # Dashboard URL for deep linking transactions
        dashboard_url = self.config.get('budget_report', {}).get(
            'transaction_dashboard_url',
            'https://ynab-reviewer.netlify.app'
        )

        html = """
        <h2>Notable Transactions</h2>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Payee</th>
                    <th>Category</th>
                    <th>Amount</th>
                    <th>Memo</th>
                </tr>
            </thead>
            <tbody>
        """

        for txn in notable:
            amount_class = 'positive' if txn['is_inflow'] else 'negative'
            amount_sign = '+' if txn['is_inflow'] else '-'

            # Create deep link to transaction dashboard
            txn_id = txn.get('id', '')
            if txn_id and dashboard_url:
                payee_link = f'<a href="{dashboard_url}/transactions/{txn_id}" style="color: #3498db; text-decoration: none;">{txn["payee"]}</a>'
            else:
                payee_link = txn['payee']

            html += f"""
                <tr>
                    <td>{txn['date']}</td>
                    <td>{payee_link}</td>
                    <td>{txn['category']}</td>
                    <td class="amount {amount_class}">{amount_sign}${txn['amount']:,.2f}</td>
                    <td>{txn['memo']}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        """
        return html

    def _generate_account_section(self, account_breakdown: list) -> str:
        """Generate account activity section."""
        if not account_breakdown:
            return ""

        html = """
        <h2>Account Activity</h2>
        <table>
            <thead>
                <tr>
                    <th>Account</th>
                    <th>Inflow</th>
                    <th>Outflow</th>
                    <th>Net</th>
                    <th>Transactions</th>
                </tr>
            </thead>
            <tbody>
        """

        for account in account_breakdown:
            net_class = 'positive' if account['net'] >= 0 else 'negative'

            html += f"""
                <tr>
                    <td>{account['account_name']}</td>
                    <td class="amount positive">${account['inflow']:,.2f}</td>
                    <td class="amount negative">${account['outflow']:,.2f}</td>
                    <td class="amount {net_class}">${account['net']:,.2f}</td>
                    <td>{account['transaction_count']}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        """
        return html

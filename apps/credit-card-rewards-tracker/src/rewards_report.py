"""
Rewards Report Generator for Credit Card Rewards Tracker

Generates HTML email reports for weekly rewards summaries.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, BaseLoader

logger = logging.getLogger(__name__)


# Inline HTML template (fallback when templates directory doesn't exist)
INLINE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly Rewards Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 700px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #1a1a1a;
            font-size: 28px;
            margin-bottom: 10px;
            border-bottom: 3px solid #EA580C;
            padding-bottom: 10px;
        }
        h2 {
            color: #333;
            font-size: 20px;
            margin-top: 30px;
            margin-bottom: 15px;
        }
        .subtitle {
            color: #666;
            font-size: 14px;
            margin-bottom: 25px;
        }
        .value-box {
            background: linear-gradient(135deg, #EA580C 0%, #DC2626 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin: 20px 0;
        }
        .value-box .amount {
            font-size: 36px;
            font-weight: bold;
        }
        .value-box .label {
            font-size: 14px;
            opacity: 0.9;
        }
        .balance-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .balance-card {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid #EA580C;
        }
        .balance-card .program {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .balance-card .points {
            font-size: 24px;
            font-weight: bold;
            color: #1a1a1a;
        }
        .balance-card .value {
            font-size: 14px;
            color: #EA580C;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background-color: #f8f9fa;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            color: #666;
        }
        .tip-box {
            background-color: #fff7ed;
            border-left: 4px solid #EA580C;
            padding: 15px;
            margin: 10px 0;
            border-radius: 0 8px 8px 0;
        }
        .tip-box.high {
            background-color: #fef2f2;
            border-left-color: #DC2626;
        }
        .tip-box .priority {
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
            color: #EA580C;
        }
        .tip-box.high .priority {
            color: #DC2626;
        }
        .tip-box .title {
            font-weight: 600;
            margin: 5px 0;
        }
        .tip-box .description {
            font-size: 14px;
            color: #666;
        }
        .category-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .category-row .category {
            font-weight: 500;
        }
        .category-row .card {
            color: #666;
        }
        .category-row .multiplier {
            color: #EA580C;
            font-weight: bold;
        }
        .fee-alert {
            background-color: #fef2f2;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }
        .fee-alert .card-name {
            font-weight: 600;
        }
        .fee-alert .details {
            font-size: 14px;
            color: #666;
        }
        .redemption-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .redemption-row .info {
            flex: 1;
        }
        .redemption-row .program {
            font-weight: 500;
        }
        .redemption-row .type {
            font-size: 12px;
            color: #666;
        }
        .redemption-row .value {
            font-weight: bold;
            color: #10B981;
        }
        .redemption-row .cpp {
            font-size: 12px;
            color: #666;
        }
        .footer {
            text-align: center;
            padding-top: 20px;
            margin-top: 30px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 12px;
        }
        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
        }
        .stat-row .label {
            color: #666;
        }
        .stat-row .value {
            font-weight: 600;
        }
        .positive {
            color: #10B981;
        }
        .negative {
            color: #DC2626;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Weekly Rewards Report</h1>
        <div class="subtitle">{{ generated_at[:10] }}</div>

        <!-- Total Value -->
        <div class="value-box">
            <div class="label">Total Rewards Value</div>
            <div class="amount">${{ "%.2f"|format(total_value.combined_cents / 100) }}</div>
        </div>

        <!-- Balances by Program -->
        <h2>Current Balances</h2>
        <div class="balance-grid">
            {% for program, balance in balances.points.items() %}
            <div class="balance-card">
                <div class="program">{{ program|replace('_', ' ')|title }}</div>
                <div class="points">{{ "{:,}".format(balance.points) }} pts</div>
                <div class="value">${{ "%.2f"|format(balance.value_cents / 100) }}</div>
            </div>
            {% endfor %}
            {% for card_id, balance in balances.cash_back.items() %}
            <div class="balance-card">
                <div class="program">Cash Back</div>
                <div class="points">${{ "%.2f"|format(balance.amount_cents / 100) }}</div>
                <div class="value">Ready to redeem</div>
            </div>
            {% endfor %}
        </div>

        <!-- Best Card by Category -->
        {% if category_recommendations %}
        <h2>Best Card by Category</h2>
        {% for category, rec in category_recommendations.items() %}
        <div class="category-row">
            <span class="category">{{ category|replace('_', ' ')|title }}</span>
            <span class="card">{{ rec.card_name }}</span>
            <span class="multiplier">{{ rec.multiplier }}x ({{ rec.effective_return }})</span>
        </div>
        {% endfor %}
        {% endif %}

        <!-- Recent Redemptions -->
        {% if recent_redemptions %}
        <h2>Recent Redemptions</h2>
        {% for red in recent_redemptions %}
        <div class="redemption-row">
            <div class="info">
                <div class="program">{{ red.program|replace('_', ' ')|title }}</div>
                <div class="type">{{ red.redemption_type|replace('_', ' ')|title }} - {{ red.date }}</div>
            </div>
            <div style="text-align: right;">
                <div class="value">${{ "%.2f"|format(red.value_received_cents / 100) }}</div>
                <div class="cpp">{{ "%.2f"|format(red.cents_per_point) }} cpp</div>
            </div>
        </div>
        {% endfor %}

        <!-- Redemption Stats -->
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 15px;">
            <div class="stat-row">
                <span class="label">YTD Redemptions</span>
                <span class="value">{{ ytd_redemption_stats.total_redemptions }}</span>
            </div>
            <div class="stat-row">
                <span class="label">Total Points Redeemed</span>
                <span class="value">{{ "{:,}".format(ytd_redemption_stats.total_points_redeemed) }}</span>
            </div>
            <div class="stat-row">
                <span class="label">Total Value Received</span>
                <span class="value positive">${{ "%.2f"|format(ytd_redemption_stats.total_value_received_cents / 100) }}</span>
            </div>
            <div class="stat-row">
                <span class="label">Average CPP</span>
                <span class="value">{{ "%.2f"|format(ytd_redemption_stats.average_cpp) }}</span>
            </div>
        </div>
        {% endif %}

        <!-- Upcoming Fees -->
        {% if upcoming_fees %}
        <h2>Upcoming Annual Fees</h2>
        {% for fee in upcoming_fees %}
        <div class="fee-alert">
            <div class="card-name">{{ fee.card_name }}</div>
            <div class="details">
                ${{ "%.0f"|format(fee.amount / 100) }} due in {{ fee.days_until }} days ({{ fee.due_date }})
            </div>
        </div>
        {% endfor %}
        {% endif %}

        <!-- Annual Summary -->
        {% if annual_summary.fees_paid_cents > 0 %}
        <h2>Annual Fee ROI</h2>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
            <div class="stat-row">
                <span class="label">Total Fees Paid</span>
                <span class="value negative">${{ "%.2f"|format(annual_summary.fees_paid_cents / 100) }}</span>
            </div>
            <div class="stat-row">
                <span class="label">Total Rewards Value</span>
                <span class="value positive">${{ "%.2f"|format(annual_summary.rewards_value_cents / 100) }}</span>
            </div>
            <div class="stat-row">
                <span class="label">Net Value</span>
                <span class="value {% if annual_summary.net_value_cents >= 0 %}positive{% else %}negative{% endif %}">
                    ${{ "%.2f"|format(annual_summary.net_value_cents / 100) }}
                </span>
            </div>
            <div class="stat-row">
                <span class="label">ROI</span>
                <span class="value {% if annual_summary.roi_percentage >= 100 %}positive{% else %}negative{% endif %}">
                    {{ "%.0f"|format(annual_summary.roi_percentage) }}%
                </span>
            </div>
        </div>
        {% endif %}

        <!-- Optimization Tips -->
        {% if optimization_tips %}
        <h2>Optimization Tips</h2>
        {% for tip in optimization_tips %}
        <div class="tip-box {% if tip.priority == 'high' %}high{% endif %}">
            <div class="priority">{{ tip.priority }}</div>
            <div class="title">{{ tip.title }}</div>
            <div class="description">{{ tip.description }}</div>
        </div>
        {% endfor %}
        {% endif %}

        <!-- Highlighted Cards -->
        {% if highlighted_cards %}
        <h2>Don't Forget These Bonuses</h2>
        {% for card in highlighted_cards %}
        <div class="category-row">
            <span class="category">{{ card.card_name }}</span>
            <span class="card">{{ card.category|title }}</span>
            <span class="multiplier">{{ card.multiplier }}x</span>
        </div>
        {% endfor %}
        {% endif %}

        <div class="footer">
            <p>Credit Card Rewards Tracker</p>
            <p>Report generated {{ generated_at[:19] }}</p>
        </div>
    </div>
</body>
</html>
"""


class RewardsReportGenerator:
    """Generates HTML email reports for rewards tracking."""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize report generator.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Try to load templates from file system, fall back to inline
        try:
            template_loader = FileSystemLoader('templates')
            self.env = Environment(loader=template_loader)
            self.use_file_templates = True
        except Exception:
            self.env = Environment(loader=BaseLoader())
            self.use_file_templates = False

    def generate_html_report(self, summary: Dict[str, Any]) -> str:
        """
        Generate HTML report from summary data.

        Args:
            summary: Summary data from RewardsAnalyzer.generate_weekly_summary()

        Returns:
            HTML string
        """
        try:
            if self.use_file_templates:
                template = self.env.get_template('weekly_report.html')
            else:
                template = self.env.from_string(INLINE_TEMPLATE)

            html = template.render(**summary)
            return html

        except Exception as e:
            logger.error(f"Error generating HTML report: {e}")
            return self._generate_fallback_report(summary)

    def _generate_fallback_report(self, summary: Dict[str, Any]) -> str:
        """Generate a simple fallback report if template fails."""
        total_value = summary.get('total_value', {})
        generated_at = summary.get('generated_at', datetime.now().isoformat())

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Weekly Rewards Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: 0 auto; }}
                h1 {{ color: #EA580C; }}
                .box {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .big {{ font-size: 32px; font-weight: bold; color: #EA580C; }}
            </style>
        </head>
        <body>
            <h1>Weekly Rewards Report</h1>
            <p>Generated: {generated_at[:10]}</p>

            <div class="box">
                <h2>Total Rewards Value</h2>
                <p class="big">${total_value.get('combined_cents', 0) / 100:,.2f}</p>
                <p>Points: ${total_value.get('points_value_cents', 0) / 100:,.2f}</p>
                <p>Cash Back: ${total_value.get('cash_back_cents', 0) / 100:,.2f}</p>
            </div>

            <p style="color: #999; font-size: 12px;">Credit Card Rewards Tracker</p>
        </body>
        </html>
        """

    def generate_annual_summary(self, year: int = None) -> str:
        """
        Generate annual summary report.

        Args:
            year: Year to generate report for (default: current year)

        Returns:
            HTML string
        """
        if year is None:
            year = datetime.now().year

        # This would need to be implemented with full data analysis
        # For now, return a placeholder
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Annual Rewards Summary - {year}</title>
        </head>
        <body>
            <h1>Annual Rewards Summary - {year}</h1>
            <p>Full annual summary coming soon...</p>
        </body>
        </html>
        """

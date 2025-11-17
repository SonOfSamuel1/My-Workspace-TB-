"""
Report Generator - Creates HTML email reports for follow-up notifications

Generates visually appealing HTML email reports summarizing
conversations that need follow-up.
"""

import logging
from datetime import datetime
from typing import List
import pytz

from message_analyzer import FollowUpItem
from action_recommender import ActionRecommendation

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates HTML reports for follow-up notifications."""

    def __init__(self, config: dict):
        """
        Initialize report generator.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.email_config = config.get('email', {})
        self.timezone = pytz.timezone(config.get('timezone', 'America/New_York'))

    def generate_html_report(
        self,
        follow_up_items: List[FollowUpItem],
        recommendations_by_item: dict = None
    ) -> str:
        """
        Generate HTML email report.

        Args:
            follow_up_items: List of follow-up items to include
            recommendations_by_item: Dict mapping FollowUpItem to list of ActionRecommendations

        Returns:
            HTML string
        """
        recommendations_by_item = recommendations_by_item or {}

        # Get current time in configured timezone
        now = datetime.now(self.timezone)
        report_date = now.strftime('%A, %B %d, %Y at %I:%M %p')

        # Group by priority
        grouped = self._group_by_priority(follow_up_items)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
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
            color: #1a1a1a;
            border-bottom: 3px solid #007AFF;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        .summary {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .priority-section {{
            margin: 25px 0;
        }}
        .follow-up-item {{
            background-color: #fff;
            border-left: 4px solid #ddd;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .follow-up-item.urgent {{
            border-left-color: #ff3b30;
            background-color: #fff5f5;
        }}
        .follow-up-item.high {{
            border-left-color: #ff9500;
            background-color: #fffaf0;
        }}
        .follow-up-item.medium {{
            border-left-color: #ffcc00;
            background-color: #fffef0;
        }}
        .follow-up-item.low {{
            border-left-color: #34c759;
            background-color: #f0fff4;
        }}
        .contact-name {{
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 8px;
        }}
        .reason {{
            color: #666;
            font-size: 14px;
            margin-bottom: 8px;
        }}
        .time-info {{
            color: #999;
            font-size: 13px;
            margin-bottom: 10px;
        }}
        .message-preview {{
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            font-size: 14px;
            font-style: italic;
            margin: 10px 0;
            color: #555;
        }}
        .analysis {{
            background-color: #e3f2fd;
            padding: 12px;
            border-radius: 4px;
            margin: 10px 0;
            border-left: 3px solid #2196F3;
        }}
        .analysis-title {{
            font-weight: 600;
            color: #1976D2;
            margin-bottom: 5px;
        }}
        .recommendations {{
            margin-top: 15px;
        }}
        .recommendation {{
            background-color: #f1f8e9;
            padding: 10px;
            margin: 8px 0;
            border-radius: 4px;
            border-left: 3px solid #8bc34a;
        }}
        .recommendation-title {{
            font-weight: 600;
            color: #558b2f;
            font-size: 14px;
        }}
        .recommendation-description {{
            color: #666;
            font-size: 13px;
            margin-top: 3px;
        }}
        .priority-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            margin-left: 10px;
        }}
        .priority-badge.urgent {{
            background-color: #ff3b30;
            color: white;
        }}
        .priority-badge.high {{
            background-color: #ff9500;
            color: white;
        }}
        .priority-badge.medium {{
            background-color: #ffcc00;
            color: #333;
        }}
        .priority-badge.low {{
            background-color: #34c759;
            color: white;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #999;
            font-size: 13px;
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-number {{
            font-size: 32px;
            font-weight: 700;
            color: #007AFF;
        }}
        .stat-label {{
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 iMessage Follow-up Report</h1>

        <div class="summary">
            <strong>Generated:</strong> {report_date}<br>
            <strong>Total conversations needing attention:</strong> {len(follow_up_items)}
        </div>

        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{len(grouped.get('urgent', []))}</div>
                <div class="stat-label">Urgent</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{len(grouped.get('high', []))}</div>
                <div class="stat-label">High Priority</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{len(grouped.get('medium', []))}</div>
                <div class="stat-label">Medium</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{len(grouped.get('low', []))}</div>
                <div class="stat-label">Low</div>
            </div>
        </div>
"""

        # Add each priority section
        for priority in ['urgent', 'high', 'medium', 'low']:
            items = grouped.get(priority, [])

            if not items:
                continue

            priority_label = priority.upper()
            html += f"""
        <div class="priority-section">
            <h2>{self._get_priority_emoji(priority)} {priority_label} Priority ({len(items)})</h2>
"""

            for item in items:
                html += self._generate_follow_up_item_html(item, recommendations_by_item.get(item, []))

            html += """
        </div>
"""

        # Footer
        html += f"""
        <div class="footer">
            <p>This report was automatically generated by iMessage Follow-up Automation</p>
            <p>To respond or take action, open the Messages app on your device</p>
        </div>
    </div>
</body>
</html>
"""

        return html

    def _generate_follow_up_item_html(
        self,
        item: FollowUpItem,
        recommendations: List[ActionRecommendation]
    ) -> str:
        """Generate HTML for a single follow-up item."""

        # Get last message preview
        last_message = item.conversation.last_incoming_message
        preview = ""

        if last_message and self.email_config.get('include_message_preview', True):
            max_length = self.email_config.get('preview_length', 200)
            message_text = last_message.text[:max_length]

            if len(last_message.text) > max_length:
                message_text += "..."

            preview = f"""
            <div class="message-preview">
                <strong>{item.contact_name}:</strong> {message_text}
            </div>
"""

        # Format time since last message
        hours = item.hours_since_last_message
        if hours < 24:
            time_str = f"{int(hours)} hours ago"
        else:
            days = int(hours / 24)
            time_str = f"{days} day{'s' if days != 1 else ''} ago"

        # AI Analysis
        analysis_html = ""
        if item.analysis:
            analysis_html = f"""
            <div class="analysis">
                <div class="analysis-title">💡 AI Analysis</div>
                <div>{item.analysis}</div>
            </div>
"""

        # Recommendations
        recommendations_html = ""
        if recommendations:
            recommendations_html = """
            <div class="recommendations">
                <strong>🎯 Recommended Actions:</strong>
"""

            for rec in recommendations:
                icon = self._get_recommendation_icon(rec.action_type)
                recommendations_html += f"""
                <div class="recommendation">
                    <div class="recommendation-title">{icon} {rec.title}</div>
                    <div class="recommendation-description">{rec.description}</div>
                </div>
"""

            recommendations_html += """
            </div>
"""

        html = f"""
            <div class="follow-up-item {item.priority}">
                <div class="contact-name">
                    {item.contact_name}
                    <span class="priority-badge {item.priority}">{item.priority}</span>
                </div>
                <div class="reason">📋 {item.reason}</div>
                <div class="time-info">⏰ Last message: {time_str}</div>
                {preview}
                {analysis_html}
                {recommendations_html}
            </div>
"""

        return html

    @staticmethod
    def _group_by_priority(items: List[FollowUpItem]) -> dict:
        """Group follow-up items by priority level."""
        grouped = {
            'urgent': [],
            'high': [],
            'medium': [],
            'low': []
        }

        for item in items:
            if item.priority in grouped:
                grouped[item.priority].append(item)

        return grouped

    @staticmethod
    def _get_priority_emoji(priority: str) -> str:
        """Get emoji for priority level."""
        emojis = {
            'urgent': '🚨',
            'high': '⚠️',
            'medium': '📌',
            'low': '💬'
        }
        return emojis.get(priority, '📱')

    @staticmethod
    def _get_recommendation_icon(action_type: str) -> str:
        """Get icon for recommendation type."""
        icons = {
            'respond': '💬',
            'task': '✅',
            'calendar': '📅',
            'automation': '🤖'
        }
        return icons.get(action_type, '•')

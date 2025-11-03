"""
HTML Email Report Generator for Relationship Tracking

Generates beautiful HTML email reports with:
- Executive summary and health score
- Date night tracking with alerts
- Gift, letter, and activity tracking
- Toggl time statistics
- Red alerts for critical items
"""

import logging
from datetime import datetime
from typing import Dict
import pytz

logger = logging.getLogger(__name__)


class RelationshipReportGenerator:
    """Generate HTML email reports for relationship tracking."""

    def __init__(self, config: Dict):
        """
        Initialize report generator.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.timezone = pytz.timezone(config.get('timezone', 'America/New_York'))

    def generate_html_report(self, report_data: Dict) -> str:
        """
        Generate HTML email report from tracking data.

        Args:
            report_data: Complete tracking data from RelationshipTracker

        Returns:
            HTML string for email
        """
        logger.info("Generating HTML report...")

        # Calculate overall health score
        health_score = self._calculate_health_score(report_data)

        # Build HTML sections
        html_parts = [
            self._get_html_header(),
            self._get_executive_summary(health_score, report_data),
            self._get_critical_alerts(report_data['alerts']),
            self._get_date_nights_section(report_data['date_nights']),
            self._get_gifts_section(report_data['gifts']),
            self._get_letters_section(report_data['letters']),
            self._get_action_plan_section(report_data),
            self._get_time_investment_section(report_data['toggl_stats']),
            self._get_monthly_activities_section(report_data),
            self._get_action_items(report_data['alerts']),
            self._get_html_footer()
        ]

        html_content = '\n'.join(html_parts)

        logger.info("HTML report generated successfully")
        return html_content

    def _calculate_health_score(self, report_data: Dict) -> int:
        """
        Calculate overall relationship health score (0-100).

        Args:
            report_data: Complete tracking data

        Returns:
            Integer score from 0-100
        """
        score = 100

        # Deduct points for critical issues
        critical_alerts = [a for a in report_data['alerts'] if a['level'] == 'critical']
        score -= len(critical_alerts) * 10

        # Deduct points for warning issues
        warning_alerts = [a for a in report_data['alerts'] if a['level'] == 'warning']
        score -= len(warning_alerts) * 5

        # Bonus points for good date night coverage
        date_coverage = report_data['date_nights'].get('coverage_percent', 0)
        if date_coverage >= 90:
            score += 5

        # Bonus points for consistent Toggl tracking
        toggl_hours = report_data['toggl_stats'].get('total_hours', 0)
        if toggl_hours >= 10:
            score += 5

        return max(0, min(100, score))

    def _get_health_score_color(self, score: int) -> str:
        """Get color based on health score."""
        if score >= 80:
            return '#27ae60'  # Green
        elif score >= 60:
            return '#f39c12'  # Orange
        else:
            return '#e74c3c'  # Red

    def _get_html_header(self) -> str:
        """Generate HTML header with styles."""
        return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.4;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 15px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            border-bottom: 2px solid #e91e63;
            padding-bottom: 12px;
            margin-bottom: 20px;
        }
        .header h1 {
            color: #e91e63;
            margin: 0;
            font-size: 26px;
        }
        .header .subtitle {
            color: #666;
            font-size: 13px;
            margin-top: 4px;
        }
        .health-score {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 8px;
            color: white;
            margin-bottom: 20px;
        }
        .health-score .score {
            font-size: 56px;
            font-weight: bold;
            margin: 0;
        }
        .health-score .label {
            font-size: 15px;
            opacity: 0.9;
        }
        .alert-box {
            border-left: 4px solid;
            padding: 10px 15px;
            margin: 10px 0;
            border-radius: 4px;
            background-color: #fff;
        }
        .alert-critical {
            border-color: #e74c3c;
            background-color: #fadbd8;
        }
        .alert-warning {
            border-color: #f39c12;
            background-color: #fef5e7;
        }
        .alert-info {
            border-color: #3498db;
            background-color: #d6eaf8;
        }
        .section {
            margin: 20px 0;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 6px;
        }
        .section h2 {
            color: #2c3e50;
            margin-top: 0;
            margin-bottom: 12px;
            border-bottom: 2px solid #e91e63;
            padding-bottom: 8px;
            font-size: 20px;
        }
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin: 12px 0;
        }
        @media (max-width: 600px) {
            .stat-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        .stat-card {
            background: white;
            padding: 12px;
            border-radius: 6px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .stat-card .value {
            font-size: 28px;
            font-weight: bold;
            color: #e91e63;
            margin: 6px 0;
        }
        .stat-card .label {
            color: #666;
            font-size: 13px;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
            margin: 4px;
        }
        .badge-success {
            background-color: #d4edda;
            color: #155724;
        }
        .badge-warning {
            background-color: #fff3cd;
            color: #856404;
        }
        .badge-danger {
            background-color: #f8d7da;
            color: #721c24;
        }
        .date-night-item {
            padding: 10px;
            margin: 8px 0;
            background: white;
            border-radius: 4px;
            border-left: 3px solid #3498db;
            font-size: 14px;
        }
        .date-night-item.incomplete {
            border-left-color: #e74c3c;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: #ecf0f1;
            border-radius: 10px;
            overflow: hidden;
            margin: 8px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 11px;
        }
        .action-item {
            padding: 10px;
            margin: 8px 0;
            background: white;
            border-radius: 4px;
            border-left: 3px solid #e74c3c;
            font-size: 14px;
        }
        .action-item .title {
            font-weight: bold;
            color: #e74c3c;
            margin-bottom: 4px;
        }
        .footer {
            text-align: center;
            margin-top: 25px;
            padding-top: 15px;
            border-top: 1px solid #ecf0f1;
            color: #95a5a6;
            font-size: 11px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Love Brittany Action Plan</h1>
            <p class="subtitle">Relationship Tracking Report</p>
        </div>
'''

    def _get_executive_summary(self, health_score: int, report_data: Dict) -> str:
        """Generate executive summary section."""
        now = datetime.now(self.timezone)
        critical_count = len([a for a in report_data['alerts'] if a['level'] == 'critical'])
        warning_count = len([a for a in report_data['alerts'] if a['level'] == 'warning'])

        score_color = self._get_health_score_color(health_score)

        summary_html = f'''
        <div class="health-score" style="background: linear-gradient(135deg, {score_color} 0%, {score_color}dd 100%);">
            <p class="score">{health_score}</p>
            <p class="label">Relationship Health Score</p>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <p><strong>Report Date:</strong> {now.strftime('%A, %B %d, %Y at %I:%M %p %Z')}</p>

            <div class="stat-grid">
                <div class="stat-card">
                    <div class="value">{critical_count}</div>
                    <div class="label">Critical Alerts</div>
                </div>
                <div class="stat-card">
                    <div class="value">{warning_count}</div>
                    <div class="label">Warnings</div>
                </div>
                <div class="stat-card">
                    <div class="value">{report_data['date_nights']['total_scheduled']}</div>
                    <div class="label">Date Nights Scheduled</div>
                </div>
                <div class="stat-card">
                    <div class="value">{report_data['toggl_stats']['total_hours']:.1f}h</div>
                    <div class="label">Time Investment (30d)</div>
                </div>
            </div>
        </div>
'''
        return summary_html

    def _get_critical_alerts(self, alerts: list) -> str:
        """Generate critical alerts section."""
        critical_alerts = [a for a in alerts if a['level'] == 'critical']

        if not critical_alerts:
            return '''
        <div class="section">
            <h2>Status</h2>
            <div class="alert-box" style="border-color: #27ae60; background-color: #d4edda;">
                <strong>Excellent!</strong> No critical issues detected. Keep up the great work!
            </div>
        </div>
'''

        alerts_html = '''
        <div class="section">
            <h2>Critical Alerts</h2>
            <p><strong>These items require immediate attention:</strong></p>
'''

        for alert in critical_alerts:
            alerts_html += f'''
            <div class="alert-box alert-critical">
                <div class="title"><strong>{alert['category']}:</strong> {alert['message']}</div>
                <div><strong>Action:</strong> {alert['action']}</div>
            </div>
'''

        alerts_html += '</div>'
        return alerts_html

    def _get_date_nights_section(self, date_nights: Dict) -> str:
        """Generate date nights section."""
        coverage = date_nights['coverage_percent']
        total = date_nights['total_scheduled']
        missing = len(date_nights['missing_months'])

        # Get restaurant page URL from config (default to localhost for local testing)
        restaurant_url = self.config.get('restaurant_page_url', 'http://localhost:5000')

        html = f'''
        <div class="section">
            <h2>Date Nights (Next 12 Months)</h2>

            <div class="stat-grid">
                <div class="stat-card">
                    <div class="value">{total}</div>
                    <div class="label">Scheduled</div>
                </div>
                <div class="stat-card">
                    <div class="value">{coverage:.0f}%</div>
                    <div class="label">Coverage</div>
                </div>
                <div class="stat-card">
                    <div class="value">{missing}</div>
                    <div class="label">Missing Months</div>
                </div>
            </div>

            <div class="progress-bar">
                <div class="progress-fill" style="width: {coverage}%;">
                    {coverage:.0f}% Complete
                </div>
            </div>

            <!-- Restaurant Discovery Button -->
            <div style="text-align: center; margin: 20px 0;">
                <a href="{restaurant_url}" target="_blank" style="display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 10px; font-weight: bold; font-size: 16px; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);">
                    🍽️ Discover Atlanta Restaurants for Date Night
                </a>
                <p style="margin-top: 10px; color: #666; font-size: 13px;">
                    Browse curated restaurants with one-click reservations • Auto-updates with your visit history
                </p>
            </div>
'''

        if date_nights['missing_months']:
            html += '<div style="margin: 10px 0;"><strong>Missing date nights in:</strong> '
            html += ', '.join(date_nights['missing_months'])
            html += '</div>'

        if date_nights['date_nights']:
            html += '<h3>Upcoming Date Nights:</h3>'

            for dn in date_nights['date_nights'][:5]:
                complete_class = '' if (dn['has_babysitter'] and dn['has_reservation']) else 'incomplete'

                html += f'''
            <div class="date-night-item {complete_class}">
                <strong>{dn['date']}</strong> - {dn['title']}<br>
                Babysitter: {dn.get('babysitter_name', 'Not booked')} {'[Booked]' if dn['has_babysitter'] else '[Not Booked]'}<br>
                Reservation: {'Confirmed' if dn['has_reservation'] else 'Not made'}
            </div>
'''

        html += '</div>'
        return html

    def _get_gifts_section(self, gifts: Dict) -> str:
        """Generate gifts tracking section."""
        last_date = gifts.get('last_gift_date', 'Never')
        days_since = gifts.get('days_since_last', 'N/A')
        next_due = gifts.get('next_due_date', 'N/A')
        is_overdue = gifts.get('is_overdue', True)

        status_badge = 'badge-danger' if is_overdue else 'badge-success'
        status_text = 'OVERDUE' if is_overdue else 'On Track'

        html = f'''
        <div class="section">
            <h2>Unexpected Gifts (Every 3 Months)</h2>

            <span class="status-badge {status_badge}">{status_text}</span>

            <div class="stat-grid">
                <div class="stat-card">
                    <div class="value">{last_date}</div>
                    <div class="label">Last Gift</div>
                </div>
                <div class="stat-card">
                    <div class="value">{days_since}</div>
                    <div class="label">Days Since</div>
                </div>
                <div class="stat-card">
                    <div class="value">{next_due}</div>
                    <div class="label">Next Due</div>
                </div>
            </div>
        </div>
'''
        return html

    def _get_letters_section(self, letters: Dict) -> str:
        """Generate letters tracking section."""
        last_date = letters.get('last_letter_date', 'Never')
        days_since = letters.get('days_since_last', 'N/A')
        next_due = letters.get('next_due_date', 'N/A')
        is_overdue = letters.get('is_overdue', True)

        status_badge = 'badge-danger' if is_overdue else 'badge-success'
        status_text = 'OVERDUE' if is_overdue else 'On Track'

        html = f'''
        <div class="section">
            <h2>Letters in Book (Every 3 Weeks)</h2>

            <span class="status-badge {status_badge}">{status_text}</span>

            <div class="stat-grid">
                <div class="stat-card">
                    <div class="value">{last_date}</div>
                    <div class="label">Last Letter</div>
                </div>
                <div class="stat-card">
                    <div class="value">{days_since}</div>
                    <div class="label">Days Since</div>
                </div>
                <div class="stat-card">
                    <div class="value">{next_due}</div>
                    <div class="label">Next Due</div>
                </div>
            </div>
        </div>
'''
        return html

    def _get_action_plan_section(self, report_data: Dict) -> str:
        """Generate action plan tracking section."""
        reviews = report_data['action_plan_reviews']
        gaps = report_data['daily_gaps']

        last_review = reviews.get('last_review_date', 'Never')
        days_since_review = reviews.get('days_since_last', 'N/A')

        completion_rate = gaps.get('completion_rate', 0)
        days_completed = gaps.get('days_completed', 0)
        days_tracked = gaps.get('days_tracked', 7)

        html = f'''
        <div class="section">
            <h2>Love Action Plan</h2>

            <h3>Plan Reviews</h3>
            <p><strong>Last Review:</strong> {last_review} ({days_since_review} days ago)</p>

            <h3>Daily 10-Minute Gaps (Last {days_tracked} Days)</h3>

            <div class="stat-grid">
                <div class="stat-card">
                    <div class="value">{days_completed}/{days_tracked}</div>
                    <div class="label">Days Completed</div>
                </div>
                <div class="stat-card">
                    <div class="value">{completion_rate:.0f}%</div>
                    <div class="label">Completion Rate</div>
                </div>
            </div>

            <div class="progress-bar">
                <div class="progress-fill" style="width: {completion_rate}%;">
                    {completion_rate:.0f}%
                </div>
            </div>
        </div>
'''
        return html

    def _get_time_investment_section(self, toggl_stats: Dict) -> str:
        """Generate time investment section."""
        total_hours = toggl_stats.get('total_hours', 0)
        total_days = toggl_stats.get('total_days', 0)
        avg_per_day = toggl_stats.get('avg_per_day', 0)
        entries_count = toggl_stats.get('entries_count', 0)

        html = f'''
        <div class="section">
            <h2>Time Investment (Last 30 Days)</h2>

            <div class="stat-grid">
                <div class="stat-card">
                    <div class="value">{total_hours:.1f}h</div>
                    <div class="label">Total Hours</div>
                </div>
                <div class="stat-card">
                    <div class="value">{total_days}</div>
                    <div class="label">Active Days</div>
                </div>
                <div class="stat-card">
                    <div class="value">{avg_per_day:.1f}h</div>
                    <div class="label">Avg Per Day</div>
                </div>
                <div class="stat-card">
                    <div class="value">{entries_count}</div>
                    <div class="label">Time Entries</div>
                </div>
            </div>
        </div>
'''
        return html

    def _get_monthly_activities_section(self, report_data: Dict) -> str:
        """Generate monthly activities section."""
        journal = report_data['journal_entries']
        suggestions = report_data['time_suggestions']
        goals = report_data['goal_support']

        html = '''
        <div class="section">
            <h2>Monthly Activities</h2>

            <div class="stat-grid">
'''

        # Journal entries
        journal_badge = 'badge-danger' if journal.get('is_overdue') else 'badge-success'
        journal_status = 'OVERDUE' if journal.get('is_overdue') else 'Current'

        html += f'''
                <div class="stat-card">
                    <div class="label">Journal Entry</div>
                    <span class="status-badge {journal_badge}">{journal_status}</span>
                    <div style="font-size: 12px; margin-top: 6px;">
                        Last: {journal.get('last_entry_date', 'Never')}
                    </div>
                </div>
'''

        # Time suggestions
        suggestion_badge = 'badge-danger' if suggestions.get('is_overdue') else 'badge-success'
        suggestion_status = 'OVERDUE' if suggestions.get('is_overdue') else 'Current'

        html += f'''
                <div class="stat-card">
                    <div class="label">Time Suggestion</div>
                    <span class="status-badge {suggestion_badge}">{suggestion_status}</span>
                    <div style="font-size: 12px; margin-top: 6px;">
                        Last: {suggestions.get('last_suggestion_date', 'Never')}
                    </div>
                </div>
'''

        # Goal support
        goal_badge = 'badge-danger' if goals.get('is_overdue') else 'badge-success'
        goal_status = 'OVERDUE' if goals.get('is_overdue') else 'Current'

        html += f'''
                <div class="stat-card">
                    <div class="label">Goal Support</div>
                    <span class="status-badge {goal_badge}">{goal_status}</span>
                    <div style="font-size: 12px; margin-top: 6px;">
                        Last: {goals.get('last_action_date', 'Never')}
                    </div>
                </div>
'''

        html += '''
            </div>
        </div>
'''
        return html

    def _get_action_items(self, alerts: list) -> str:
        """Generate action items section."""
        if not alerts:
            return ''

        html = '''
        <div class="section">
            <h2>Action Items</h2>
            <p><strong>Things to do this week:</strong></p>
'''

        for alert in alerts:
            html += f'''
            <div class="action-item">
                <div class="title">{alert['category']}</div>
                <div>{alert['action']}</div>
            </div>
'''

        html += '</div>'
        return html

    def _get_html_footer(self) -> str:
        """Generate HTML footer."""
        now = datetime.now(self.timezone)

        return f'''
        <div class="footer">
            <p>Generated on {now.strftime('%Y-%m-%d at %I:%M %p %Z')}</p>
            <p>Keep nurturing your relationship!</p>
        </div>
    </div>
</body>
</html>
'''

"""
Kaelin Development Report Generator

Generates beautiful HTML email reports for Kaelin development tracking.
"""

import logging
from datetime import datetime
from typing import Dict
import pytz

logger = logging.getLogger(__name__)


class KaelinReportGenerator:
    """Generates HTML reports for Kaelin development tracking."""

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
        Generate HTML email report.

        Args:
            report_data: Report data from KaelinTracker

        Returns:
            HTML string for email
        """
        logger.info("Generating HTML report...")

        now = datetime.now(self.timezone)
        report_date = now.strftime('%B %d, %Y')

        # Generate HTML sections
        html = self._generate_header(report_date)
        html += self._generate_executive_summary(report_data)
        html += self._generate_alerts_section(report_data['alerts'])
        html += self._generate_play_time_section(report_data['play_time'])
        html += self._generate_daddy_days_section(report_data['daddy_days'])
        html += self._generate_teachings_section(report_data['jesus_teachings'])
        html += self._generate_games_section(report_data['monthly_games'])
        html += self._generate_programs_section(report_data)
        html += self._generate_development_section(report_data)
        html += self._generate_activities_section(report_data)
        html += self._generate_field_trips_section(report_data['field_trips'])
        html += self._generate_planning_sections(report_data)
        html += self._generate_footer()

        return html

    def _generate_header(self, report_date: str) -> str:
        """Generate HTML header."""
        return f"""
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
            color: #2c5aa0;
            border-bottom: 3px solid #4a90e2;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        h2 {{
            color: #4a90e2;
            margin-top: 30px;
            border-left: 4px solid #4a90e2;
            padding-left: 15px;
        }}
        h3 {{
            color: #5a5a5a;
            margin-top: 20px;
        }}
        .summary-box {{
            background-color: #e8f4f8;
            border-left: 4px solid #4a90e2;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .alert {{
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
            border-left: 4px solid;
        }}
        .alert-critical {{
            background-color: #fee;
            border-color: #e74c3c;
            color: #c0392b;
        }}
        .alert-warning {{
            background-color: #fef5e7;
            border-color: #f39c12;
            color: #d68910;
        }}
        .alert-info {{
            background-color: #e8f8f5;
            border-color: #16a085;
            color: #117a65;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            border-left: 3px solid #4a90e2;
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: bold;
            color: #2c5aa0;
        }}
        .stat-label {{
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }}
        .progress-bar {{
            background-color: #e0e0e0;
            border-radius: 10px;
            height: 20px;
            margin: 10px 0;
            overflow: hidden;
        }}
        .progress-fill {{
            background-color: #4a90e2;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
            font-weight: bold;
        }}
        .progress-fill.low {{
            background-color: #e74c3c;
        }}
        .progress-fill.medium {{
            background-color: #f39c12;
        }}
        .progress-fill.high {{
            background-color: #27ae60;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th {{
            background-color: #4a90e2;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-success {{
            background-color: #d4edda;
            color: #155724;
        }}
        .badge-warning {{
            background-color: #fff3cd;
            color: #856404;
        }}
        .badge-danger {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #eee;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
        .emoji {{
            font-size: 1.2em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>💖 Love Kaelin Development Report</h1>
        <p style="color: #666; font-size: 16px;">Report Date: {report_date}</p>
"""

    def _generate_executive_summary(self, report_data: Dict) -> str:
        """Generate executive summary section."""
        play_time = report_data['play_time']
        daddy_days = report_data['daddy_days']
        teachings = report_data['jesus_teachings']
        field_trips = report_data['field_trips']

        # Calculate overall health score
        health_score = self._calculate_health_score(report_data)
        health_color = 'high' if health_score >= 80 else 'medium' if health_score >= 60 else 'low'

        critical_count = len([a for a in report_data['alerts'] if a['level'] == 'critical'])
        warning_count = len([a for a in report_data['alerts'] if a['level'] == 'warning'])

        return f"""
        <div class="summary-box">
            <h2 style="margin-top: 0; border: none; padding: 0;">📊 Executive Summary</h2>

            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-value">{health_score}%</div>
                    <div class="stat-label">Overall Health Score</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{play_time['days_played_last_7_days']}</div>
                    <div class="stat-label">Play Days (Last 7 Days)</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{play_time['rolling_100_avg_percentage']:.0f}%</div>
                    <div class="stat-label">100-Day Play Average</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{teachings['progress_percentage']:.0f}%</div>
                    <div class="stat-label">Teachings Progress</div>
                </div>
            </div>

            <p><strong>Overall Development Score:</strong></p>
            <div class="progress-bar">
                <div class="progress-fill {health_color}" style="width: {health_score}%;">
                    {health_score}%
                </div>
            </div>

            <p style="margin-top: 15px;">
                <strong>Alerts:</strong>
                <span class="badge badge-danger">{critical_count} Critical</span>
                <span class="badge badge-warning">{warning_count} Warnings</span>
            </p>
        </div>
"""

    def _generate_alerts_section(self, alerts: list) -> str:
        """Generate alerts section."""
        if not alerts:
            return """
        <h2>✅ Alerts</h2>
        <p style="color: #27ae60; font-weight: bold;">No alerts - Everything looks great!</p>
"""

        critical = [a for a in alerts if a['level'] == 'critical']
        warnings = [a for a in alerts if a['level'] == 'warning']
        info = [a for a in alerts if a['level'] == 'info']

        html = '<h2>🚨 Alerts & Action Items</h2>'

        if critical:
            html += '<h3 style="color: #e74c3c;">Critical Items</h3>'
            for alert in critical:
                html += f"""
        <div class="alert alert-critical">
            <strong>{alert['category']}:</strong> {alert['message']}<br>
            <strong>Action:</strong> {alert['action']}
        </div>
"""

        if warnings:
            html += '<h3 style="color: #f39c12;">Warnings</h3>'
            for alert in warnings:
                html += f"""
        <div class="alert alert-warning">
            <strong>{alert['category']}:</strong> {alert['message']}<br>
            <strong>Action:</strong> {alert['action']}
        </div>
"""

        if info:
            html += '<h3 style="color: #16a085;">Information</h3>'
            for alert in info:
                html += f"""
        <div class="alert alert-info">
            <strong>{alert['category']}:</strong> {alert['message']}<br>
            <strong>Action:</strong> {alert['action']}
        </div>
"""

        return html

    def _generate_play_time_section(self, play_time: Dict) -> str:
        """Generate play time section."""
        days_target = play_time['target_days_per_week']
        hours_target = play_time['target_hours_per_day']

        return f"""
        <h2>🎮 Play Time & Quality Time Together</h2>

        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value">{play_time['rolling_100_days_played']}</div>
                <div class="stat-label">Days Played (Last 100 Days)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{play_time['total_hours_100_days']:.1f}h</div>
                <div class="stat-label">Total Hours (100 Days)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{play_time['avg_hours_per_play_day']:.1f}h</div>
                <div class="stat-label">Avg Hours Per Play Day</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{play_time['days_since_last_play']}</div>
                <div class="stat-label">Days Since Last Play</div>
            </div>
        </div>

        <h3>Rolling 100-Day Average</h3>
        <div class="progress-bar">
            <div class="progress-fill {'high' if play_time['rolling_100_avg_percentage'] >= 70 else 'medium' if play_time['rolling_100_avg_percentage'] >= 50 else 'low'}"
                 style="width: {play_time['rolling_100_avg_percentage']}%;">
                {play_time['rolling_100_avg_percentage']:.1f}%
            </div>
        </div>

        <h3>Recent Play Sessions (Last 14 Days)</h3>
        <table>
            <tr>
                <th>Date</th>
                <th>Hours</th>
                <th>Status</th>
            </tr>
            {''.join([f"<tr><td>{date}</td><td>{hours:.1f}h</td><td><span class='badge badge-success'>✓ Played</span></td></tr>"
                     for date, hours in play_time['daily_breakdown'].items()])}
        </table>

        <p style="margin-top: 15px;">
            <strong>Targets:</strong> {days_target} days/week, {hours_target} hours/day<br>
            <strong>Last Play Date:</strong> {play_time['last_play_date'] or 'No recent play time recorded'}
        </p>
"""

    def _generate_daddy_days_section(self, daddy_days: Dict) -> str:
        """Generate daddy days section."""
        html = f"""
        <h2>👨‍👧 Daddy Days Planning</h2>

        <p><strong>Quarterly Planning Status:</strong> {daddy_days['total_planned']} Daddy Days planned for next {daddy_days['quarters_checked']} quarters</p>

        <div class="progress-bar">
            <div class="progress-fill {'high' if daddy_days['coverage_percentage'] >= 75 else 'medium' if daddy_days['coverage_percentage'] >= 50 else 'low'}"
                 style="width: {daddy_days['coverage_percentage']}%;">
                {daddy_days['coverage_percentage']:.0f}% Coverage
            </div>
        </div>

        <h3>Upcoming Quarters</h3>
        <table>
            <tr>
                <th>Quarter</th>
                <th>Status</th>
                <th>Planned Event</th>
            </tr>
"""

        for quarter in daddy_days['quarters']:
            status_badge = 'success' if quarter['has_plan'] else 'danger'
            status_text = '✓ Planned' if quarter['has_plan'] else '✗ Missing'
            event_text = ', '.join([e['title'] for e in quarter['events']]) if quarter['events'] else '-'

            html += f"""
            <tr>
                <td>{quarter['label']}</td>
                <td><span class="badge badge-{status_badge}">{status_text}</span></td>
                <td>{event_text}</td>
            </tr>
"""

        html += '</table>'

        if daddy_days['missing_quarters']:
            html += f"""
        <div class="alert alert-warning">
            <strong>Action Needed:</strong> Plan Daddy Days for: {', '.join(daddy_days['missing_quarters'])}
        </div>
"""

        return html

    def _generate_teachings_section(self, teachings: Dict) -> str:
        """Generate Jesus teachings section."""
        return f"""
        <h2>✝️ Jesus Teachings Progress</h2>

        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value">{teachings['taught_count']}/{teachings['total_teachings']}</div>
                <div class="stat-label">Teachings Completed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{teachings['progress_percentage']:.0f}%</div>
                <div class="stat-label">Progress</div>
            </div>
        </div>

        <div class="progress-bar">
            <div class="progress-fill {'high' if teachings['progress_percentage'] >= 60 else 'medium' if teachings['progress_percentage'] >= 30 else 'low'}"
                 style="width: {teachings['progress_percentage']}%;">
                {teachings['progress_percentage']:.0f}%
            </div>
        </div>

        <h3>Recently Taught</h3>
        {'<ul>' + ''.join([f"<li><strong>{t['name']}</strong> - {t['date']} (Understanding: {t['understanding']})</li>" for t in teachings['recent_teachings']]) + '</ul>' if teachings['recent_teachings'] else '<p>No teachings recorded yet</p>'}

        <h3>Next to Teach</h3>
        {'<ul>' + ''.join([f"<li>{t}</li>" for t in teachings['not_taught_teachings'][:5]]) + '</ul>' if teachings['not_taught_teachings'] else '<p>All teachings completed!</p>'}
"""

    def _generate_games_section(self, games: Dict) -> str:
        """Generate monthly games section."""
        status_badge = 'success' if games['game_this_month'] else 'warning'
        status_text = '✓ Game Introduced' if games['game_this_month'] else '✗ No Game This Month'

        return f"""
        <h2>🎲 Monthly Games</h2>

        <p>
            <strong>This Month:</strong> <span class="badge badge-{status_badge}">{status_text}</span><br>
            <strong>Total Games Introduced:</strong> {games['total_games']}<br>
            <strong>Last Game:</strong> {games['last_game_month'] or 'None recorded'}<br>
            <strong>Days Since Last Game:</strong> {games['days_since_last_game'] or 'N/A'}
        </p>

        <h3>Recent Games (Last 6 Months)</h3>
        {'<table><tr><th>Month</th><th>Game</th><th>Type</th><th>Response</th></tr>' + ''.join([f"<tr><td>{g['month']}</td><td>{g['name']}</td><td>{g['type']}</td><td>{g['response']}</td></tr>" for g in games['recent_games']]) + '</table>' if games['recent_games'] else '<p>No games recorded yet</p>'}
"""

    def _generate_programs_section(self, report_data: Dict) -> str:
        """Generate programs section (Ivy League & Social)."""
        ivy = report_data['ivy_league_programs']
        social = report_data['social_programs']

        return f"""
        <h2>📚 Development Programs</h2>

        <h3>Ivy League Preparation Programs</h3>
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value">{ivy['researched_count']}</div>
                <div class="stat-label">Programs Researched</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{ivy['enrolled_count']}</div>
                <div class="stat-label">Currently Enrolled</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{ivy['completed_count']}</div>
                <div class="stat-label">Completed</div>
            </div>
        </div>

        <h3>Social Development Programs</h3>
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value">{social['active_programs']}</div>
                <div class="stat-label">Active Programs</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{social['total_programs']}</div>
                <div class="stat-label">Total Programs</div>
            </div>
        </div>

        {'<p><strong>Active Programs:</strong> ' + ', '.join([p['name'] for p in social['programs']['active']]) + '</p>' if social['programs']['active'] else '<p>No active social programs</p>'}
"""

    def _generate_development_section(self, report_data: Dict) -> str:
        """Generate spiritual development section."""
        spiritual = report_data['spiritual_development']

        status_badge = 'success' if spiritual['planning_status'] == 'Complete' else 'warning'

        return f"""
        <h2>🙏 Spiritual Development</h2>

        <p>
            <strong>6-Month Planning Status:</strong> <span class="badge badge-{status_badge}">{spiritual['planning_status']}</span><br>
            <strong>Months Planned:</strong> {spiritual['months_planned']}/{spiritual['target_months']}<br>
            <strong>Months Completed:</strong> {spiritual['months_completed']}<br>
            <strong>Completion Rate:</strong> {spiritual['completion_percentage']:.0f}%
        </p>

        <div class="progress-bar">
            <div class="progress-fill {'high' if spiritual['months_planned'] >= spiritual['target_months'] else 'low'}"
                 style="width: {(spiritual['months_planned'] / spiritual['target_months'] * 100) if spiritual['target_months'] > 0 else 0}%;">
                {spiritual['months_planned']}/{spiritual['target_months']} Months
            </div>
        </div>
"""

    def _generate_activities_section(self, report_data: Dict) -> str:
        """Generate activities section (crafting, imaginative play, contests)."""
        crafting = report_data['crafting_activities']
        play = report_data['imaginative_play']
        contests = report_data['fun_contests']

        return f"""
        <h2>🎨 Creative Activities</h2>

        <h3>Crafting Activities</h3>
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value">{crafting['completed_crafts']}</div>
                <div class="stat-label">Crafts Completed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{crafting['success_rate']:.0f}%</div>
                <div class="stat-label">High Enjoyment Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{crafting['planned_crafts']}</div>
                <div class="stat-label">Crafts Planned</div>
            </div>
        </div>

        <h3>Imaginative Play Games</h3>
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value">{play['games_played']}</div>
                <div class="stat-label">Games Played</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{play['engagement_rate']:.0f}%</div>
                <div class="stat-label">High Engagement Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{play['games_planned']}</div>
                <div class="stat-label">Games Planned</div>
            </div>
        </div>

        <h3>Fun Contests</h3>
        <p>
            <strong>Contests Held:</strong> {contests['contests_held']}<br>
            <strong>Contest Ideas:</strong> {contests['contest_ideas']}
        </p>
"""

    def _generate_field_trips_section(self, field_trips: Dict) -> str:
        """Generate field trips section."""
        status_badge = 'success' if field_trips['target_met'] else 'warning'
        status_text = '✓ Target Met' if field_trips['target_met'] else '✗ Below Target'

        return f"""
        <h2>🚌 Field Trips</h2>

        <p>
            <strong>Annual Target:</strong> {field_trips['target_per_year']} trips/year<br>
            <strong>This Year:</strong> {field_trips['trips_this_year']} <span class="badge badge-{status_badge}">{status_text}</span><br>
            <strong>Last Trip:</strong> {field_trips['last_trip_date'] or 'No trips recorded'}<br>
            <strong>Days Since Last Trip:</strong> {field_trips['days_since_last_trip'] or 'N/A'}
        </p>

        <div class="progress-bar">
            <div class="progress-fill {'high' if field_trips['target_met'] else 'medium'}"
                 style="width: {min(100, (field_trips['trips_this_year'] / field_trips['target_per_year'] * 100))}%;">
                {field_trips['trips_this_year']}/{field_trips['target_per_year']}
            </div>
        </div>

        <h3>Recent Trips</h3>
        {'<table><tr><th>Date</th><th>Trip</th></tr>' + ''.join([f"<tr><td>{t['date']}</td><td>{t['title']}</td></tr>" for t in field_trips['recent_trips']]) + '</table>' if field_trips['recent_trips'] else '<p>No field trips recorded yet</p>'}
"""

    def _generate_planning_sections(self, report_data: Dict) -> str:
        """Generate planning sections (Christmas, gifts)."""
        christmas = report_data['christmas_planning']
        gifts = report_data['gift_planning']

        return f"""
        <h2>🎄 Christmas Planning</h2>
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value">{christmas['traditions_planned']}</div>
                <div class="stat-label">Traditions Planned</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{christmas['activities_planned']}</div>
                <div class="stat-label">Activities Planned</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{christmas['experiences_planned']}</div>
                <div class="stat-label">Experiences Planned</div>
            </div>
        </div>

        <h2>🎁 Gift Planning</h2>
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value">{gifts['total_gift_ideas']}</div>
                <div class="stat-label">Gift Ideas</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{gifts['purchased_count']}</div>
                <div class="stat-label">Purchased</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{gifts['ready_to_give']}</div>
                <div class="stat-label">Ready to Give</div>
            </div>
        </div>
"""

    def _generate_footer(self) -> str:
        """Generate HTML footer."""
        return """
        <div class="footer">
            <p>💖 Generated with Love for Kaelin 💖</p>
            <p style="font-size: 12px;">
                This automated report tracks your relationship and development activities with Kaelin.<br>
                Continue being an amazing daddy!
            </p>
        </div>
    </div>
</body>
</html>
"""

    def _calculate_health_score(self, report_data: Dict) -> int:
        """
        Calculate overall development health score.

        Args:
            report_data: Report data dictionary

        Returns:
            Health score (0-100)
        """
        scores = []

        # Play time score (30% weight)
        play_avg = report_data['play_time']['rolling_100_avg_percentage']
        scores.append(min(100, play_avg) * 0.30)

        # Daddy days score (15% weight)
        daddy_coverage = report_data['daddy_days']['coverage_percentage']
        scores.append(daddy_coverage * 0.15)

        # Teachings score (20% weight)
        teaching_progress = report_data['jesus_teachings']['progress_percentage']
        scores.append(teaching_progress * 0.20)

        # Field trips score (10% weight)
        trips = report_data['field_trips']
        trip_score = min(100, (trips['trips_this_year'] / trips['target_per_year']) * 100)
        scores.append(trip_score * 0.10)

        # Monthly games score (10% weight)
        game_score = 100 if report_data['monthly_games']['game_this_month'] else 50
        scores.append(game_score * 0.10)

        # Spiritual development score (15% weight)
        spiritual = report_data['spiritual_development']
        spiritual_score = (spiritual['months_planned'] / spiritual['target_months'] * 100) if spiritual['target_months'] > 0 else 0
        scores.append(min(100, spiritual_score) * 0.15)

        total_score = sum(scores)
        return int(total_score)

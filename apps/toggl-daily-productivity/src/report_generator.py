"""
Report Generator

Generates HTML email reports showing ACTUAL logged projects from Toggl.
Clean, minimalist Apple-inspired design.
"""

import logging
from typing import Dict
from datetime import datetime


class ReportGenerator:
    """Generates HTML productivity reports with actual project data."""

    def __init__(self):
        """Initialize ReportGenerator."""
        self.logger = logging.getLogger(__name__)

    def generate_html_report(self, report_data: Dict, period: str = "Evening") -> str:
        """
        Generate HTML email report showing actual logged projects.

        Args:
            report_data: Dictionary with productivity metrics and actual projects
            period: "Morning" or "Evening" to indicate report time

        Returns:
            HTML string for the email
        """
        report_date = report_data.get('report_date', datetime.now())
        date_str = report_date.strftime('%B %d, %Y')

        # Generate project rows for yesterday
        yesterday_projects_html = self._generate_project_rows(
            report_data.get('yesterday_projects', [])
        )

        # Generate 7-day breakdown
        rolling_7_days_html = self._generate_rolling_7_days(
            report_data.get('rolling_7_days', [])
        )

        # Generate weekly projects summary
        week_projects_html = self._generate_project_rows(
            report_data.get('week_projects', [])
        )

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Productivity Report</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f5f5f7;
            color: #1d1d1f;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }}
        .wrapper {{
            max-width: 640px;
            margin: 0 auto;
            padding: 32px 20px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 28px;
        }}
        .header h1 {{
            font-size: 24px;
            font-weight: 600;
            letter-spacing: -0.02em;
            color: #1d1d1f;
            margin: 0 0 6px 0;
        }}
        .header .subtitle {{
            font-size: 14px;
            color: #86868b;
            font-weight: 400;
        }}
        .stats-row {{
            display: flex;
            gap: 10px;
            margin-bottom: 28px;
        }}
        .stat-card {{
            flex: 1;
            background: #ffffff;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }}
        .stat-card.hero {{
            background: linear-gradient(135deg, #1d1d1f 0%, #3d3d3f 100%);
        }}
        .stat-card.hero .stat-label {{
            color: rgba(255,255,255,0.7);
        }}
        .stat-card.hero .stat-value {{
            color: #ffffff;
        }}
        .stat-label {{
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #86868b;
            margin-bottom: 4px;
        }}
        .stat-value {{
            font-size: 22px;
            font-weight: 700;
            color: #1d1d1f;
            letter-spacing: -0.02em;
        }}
        .stat-percent {{
            font-size: 13px;
            font-weight: 500;
            color: #86868b;
            margin-left: 2px;
        }}
        .stat-card.hero .stat-percent {{
            color: rgba(255,255,255,0.6);
        }}
        .section {{
            margin-bottom: 24px;
        }}
        .section-title {{
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #86868b;
            margin-bottom: 10px;
            padding-left: 4px;
        }}
        .card {{
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }}
        .project-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 16px;
            border-bottom: 1px solid #f0f0f0;
        }}
        .project-row:last-child {{
            border-bottom: none;
        }}
        .project-name {{
            font-size: 14px;
            font-weight: 500;
            color: #1d1d1f;
        }}
        .project-time {{
            font-size: 14px;
            font-weight: 600;
            color: #1d1d1f;
            text-align: right;
        }}
        .project-time .mins {{
            font-size: 12px;
            font-weight: 400;
            color: #86868b;
            margin-left: 4px;
        }}
        .day-row {{
            padding: 14px 16px;
            border-bottom: 1px solid #f0f0f0;
        }}
        .day-row:last-child {{
            border-bottom: none;
        }}
        .day-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .day-date {{
            font-size: 13px;
            font-weight: 600;
            color: #1d1d1f;
        }}
        .day-total {{
            font-size: 13px;
            font-weight: 600;
            color: #1d1d1f;
        }}
        .day-projects {{
            font-size: 12px;
            color: #86868b;
            line-height: 1.6;
        }}
        .score-badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            margin-left: 8px;
        }}
        .score-low {{
            background-color: #ffebeb;
            color: #ff3b30;
        }}
        .score-medium {{
            background-color: #fff5e6;
            color: #ff9500;
        }}
        .score-high {{
            background-color: #e5f7ed;
            color: #34c759;
        }}
        .empty-state {{
            padding: 24px 16px;
            text-align: center;
            color: #86868b;
            font-size: 13px;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #86868b;
            font-size: 11px;
        }}
        @media (max-width: 500px) {{
            .stats-row {{
                flex-wrap: wrap;
            }}
            .stat-card {{
                min-width: calc(50% - 5px);
            }}
            .stat-card.hero {{
                min-width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="header">
            <h1>Productivity Report</h1>
            <div class="subtitle">{date_str} &middot; {period}</div>
        </div>

        <div class="stats-row">
            <div class="stat-card hero">
                <div class="stat-label">Yesterday</div>
                <div class="stat-value">{report_data['yesterday_total']}<span class="stat-percent">{report_data['yesterday_percent']}%</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">7-Day Avg</div>
                <div class="stat-value">{report_data['week_avg']}<span class="stat-percent">{report_data['week_avg_percent']}%</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">30-Day Avg</div>
                <div class="stat-value">{report_data['month_avg']}<span class="stat-percent">{report_data['month_avg_percent']}%</span></div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Yesterday's Projects</div>
            <div class="card">
                {yesterday_projects_html if yesterday_projects_html else '<div class="empty-state">No time logged yesterday</div>'}
            </div>
        </div>

        <div class="section">
            <div class="section-title">Last 7 Days</div>
            <div class="card">
                {rolling_7_days_html}
            </div>
        </div>

        <div class="section">
            <div class="section-title">7-Day Project Totals</div>
            <div class="card">
                {week_projects_html if week_projects_html else '<div class="empty-state">No time logged this week</div>'}
            </div>
        </div>

        <div class="footer">
            Goal: {report_data['daily_goal']} min/day &middot; Toggl Productivity Report
        </div>
    </div>
</body>
</html>
"""
        return html

    def _generate_project_rows(self, projects: list) -> str:
        """Generate HTML rows for project breakdown."""
        if not projects:
            return ""

        rows = []
        for project in projects:
            name = project.get('name', 'Unknown')
            formatted = project.get('formatted', '0m')
            minutes = project.get('minutes', 0)

            rows.append(f"""
                <div class="project-row">
                    <span class="project-name">{name}</span>
                    <span class="project-time">{formatted}<span class="mins">({minutes} min)</span></span>
                </div>
            """)

        return '\n'.join(rows)

    def _generate_rolling_7_days(self, days: list) -> str:
        """Generate HTML for rolling 7 days breakdown."""
        if not days:
            return '<div class="empty-state">No data available</div>'

        rows = []
        for day in days:
            date_display = day.get('date_display', day.get('date', ''))
            total_mins = day.get('total_mins', 0)
            formatted = day.get('formatted', '0m')
            score = day.get('score', 0)
            score_class = self._get_score_class(score)

            # Build project list string
            projects = day.get('projects', [])
            if projects:
                project_strs = [f"{p['name']} ({p['formatted']})" for p in projects[:4]]
                if len(projects) > 4:
                    project_strs.append(f"+{len(projects) - 4} more")
                projects_html = " &bull; ".join(project_strs)
            else:
                projects_html = "No time logged"

            rows.append(f"""
                <div class="day-row">
                    <div class="day-header">
                        <span class="day-date">{date_display}</span>
                        <span class="day-total">{formatted}<span class="score-badge {score_class}">{score}%</span></span>
                    </div>
                    <div class="day-projects">{projects_html}</div>
                </div>
            """)

        return '\n'.join(rows)

    def _get_score_class(self, score: int) -> str:
        """Get CSS class for score coloring."""
        if score >= 80:
            return 'score-high'
        elif score >= 50:
            return 'score-medium'
        else:
            return 'score-low'

    def generate_text_report(self, report_data: Dict, period: str = "Evening") -> str:
        """
        Generate plain text version of the report.

        Args:
            report_data: Dictionary with productivity metrics
            period: "Morning" or "Evening"

        Returns:
            Plain text string
        """
        report_date = report_data.get('report_date', datetime.now())
        date_str = report_date.strftime('%B %d, %Y')

        text = f"""
PRODUCTIVITY REPORT
{date_str} - {period}
{'=' * 40}

SUMMARY
-------
Yesterday: {report_data['yesterday_total']} mins ({report_data['yesterday_percent']}%)
7-Day Avg: {report_data['week_avg']} mins ({report_data['week_avg_percent']}%)
30-Day Avg: {report_data['month_avg']} mins ({report_data['month_avg_percent']}%)
Goal: {report_data['daily_goal']} mins/day

YESTERDAY'S PROJECTS
--------------------
"""
        for p in report_data.get('yesterday_projects', []):
            text += f"  {p['name']}: {p['formatted']} ({p['minutes']} min)\n"

        text += "\nLAST 7 DAYS\n-----------\n"
        for day in report_data.get('rolling_7_days', []):
            text += f"{day['date_display']}: {day['formatted']} ({day['score']}%)\n"
            for p in day.get('projects', []):
                text += f"    - {p['name']}: {p['formatted']}\n"

        return text


if __name__ == "__main__":
    # Test with sample data
    sample_data = {
        'report_date': datetime.now(),
        'daily_goal': 360,
        'yesterday_total': 362,
        'yesterday_percent': 101,
        'week_avg': 280,
        'week_avg_percent': 78,
        'month_avg': 310,
        'month_avg_percent': 86,
        'yesterday_projects': [
            {'name': 'Good Portion', 'minutes': 180, 'formatted': '3h 0m'},
            {'name': 'Deep Scripture Study', 'minutes': 90, 'formatted': '1h 30m'},
            {'name': 'Personal', 'minutes': 60, 'formatted': '1h 0m'},
            {'name': 'ATL: Christ + Friends', 'minutes': 32, 'formatted': '32m'},
        ],
        'week_projects': [
            {'name': 'Good Portion', 'minutes': 720, 'formatted': '12h 0m'},
            {'name': 'Personal', 'minutes': 300, 'formatted': '5h 0m'},
            {'name': 'Deep Scripture Study', 'minutes': 210, 'formatted': '3h 30m'},
        ],
        'rolling_7_days': [
            {
                'date': '2024-12-02',
                'date_display': 'Mon Dec 02',
                'total_mins': 362,
                'formatted': '6h 2m',
                'score': 101,
                'projects': [
                    {'name': 'Good Portion', 'formatted': '3h 0m'},
                    {'name': 'Deep Scripture Study', 'formatted': '1h 30m'},
                ]
            },
        ],
    }

    generator = ReportGenerator()
    html = generator.generate_html_report(sample_data)

    # Save preview
    with open('preview_report.html', 'w') as f:
        f.write(html)
    print("Preview saved to preview_report.html")

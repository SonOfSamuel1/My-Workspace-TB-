"""
Productivity Service

Calculates productivity metrics from Toggl time entries.
Reports on ACTUAL logged projects - no predefined categories.
Optimized to minimize API calls.
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from toggl_service import TogglService


class ProductivityService:
    """Service for calculating productivity metrics from Toggl data."""

    def __init__(self, config: Dict):
        """
        Initialize ProductivityService.

        Args:
            config: Configuration dictionary with goals
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.toggl = TogglService()

        # Load configuration
        self.daily_goal = config.get('daily_goal_minutes', 360)
        self.timezone = config.get('timezone', 'America/New_York')

        self.logger.info("ProductivityService initialized")

    def get_productivity_report(self, report_date: Optional[datetime] = None) -> Dict:
        """
        Generate a complete productivity report with ACTUAL logged projects.
        Optimized to use a single API call for all data.

        Args:
            report_date: Date to generate report for (defaults to today)

        Returns:
            Dictionary with all report data
        """
        if report_date is None:
            report_date = datetime.now()

        self.logger.info(f"Generating productivity report for {report_date.strftime('%Y-%m-%d')}")

        # Calculate date ranges
        today = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        month_start = today - timedelta(days=30)

        # SINGLE API CALL - get all entries for the last 30 days
        all_entries = self.toggl.get_time_entries(month_start, today)

        # Filter entries by date locally
        yesterday_entries = self._filter_entries_by_date(all_entries, yesterday)
        week_entries = self._filter_entries_by_date_range(all_entries, today - timedelta(days=7), today)
        month_entries = all_entries  # Already the full 30 days

        # Calculate metrics
        yesterday_total = self._calculate_total_minutes(yesterday_entries)
        week_total = self._calculate_total_minutes(week_entries)
        month_total = self._calculate_total_minutes(month_entries)
        week_avg = week_total // 7 if week_total else 0
        month_avg = month_total // 30 if month_total else 0

        # Get actual projects breakdown for yesterday
        yesterday_projects = self._get_project_breakdown(yesterday_entries)

        # Get 7-day project breakdown
        week_projects = self._get_project_breakdown(week_entries)

        # Get rolling 7 days detail (local filtering, no additional API calls)
        rolling_7_days = self._get_rolling_7_days_detail_from_entries(all_entries, today)

        # Build report data
        report = {
            'report_date': report_date,
            'daily_goal': self.daily_goal,

            # Header stats
            'yesterday_total': yesterday_total,
            'yesterday_percent': self._calculate_percent(yesterday_total, self.daily_goal),
            'week_avg': week_avg,
            'week_avg_percent': self._calculate_percent(week_avg, self.daily_goal),
            'month_avg': month_avg,
            'month_avg_percent': self._calculate_percent(month_avg, self.daily_goal),

            # Actual projects logged yesterday
            'yesterday_projects': yesterday_projects,

            # 7-day project breakdown
            'week_projects': week_projects,

            # Rolling 7 days detail
            'rolling_7_days': rolling_7_days,
        }

        return report

    def _filter_entries_by_date(self, entries: List[Dict], date: datetime) -> List[Dict]:
        """Filter entries for a specific date."""
        target_date = date.date()
        return [e for e in entries if e.get('start_time') and e['start_time'].date() == target_date]

    def _filter_entries_by_date_range(self, entries: List[Dict], start: datetime, end: datetime) -> List[Dict]:
        """Filter entries for a date range."""
        start_date = start.date()
        end_date = end.date()
        return [e for e in entries if e.get('start_time') and start_date <= e['start_time'].date() < end_date]

    def _calculate_total_minutes(self, entries: List[Dict]) -> int:
        """Calculate total minutes from entries."""
        total_seconds = sum(e.get('duration_seconds', 0) for e in entries)
        return total_seconds // 60

    def _calculate_percent(self, actual: int, goal: int) -> int:
        """Calculate percentage of goal achieved."""
        if goal <= 0:
            return 0
        return min(round((actual / goal) * 100), 999)

    def _get_project_breakdown(self, entries: List[Dict]) -> List[Dict]:
        """
        Get breakdown of time by ACTUAL project names.

        Returns list of projects sorted by time (descending).
        """
        projects = defaultdict(lambda: {'seconds': 0, 'entries': []})

        for entry in entries:
            project_name = entry.get('project_name') or 'No Project'
            projects[project_name]['seconds'] += entry.get('duration_seconds', 0)
            projects[project_name]['entries'].append(entry)

        # Convert to list and sort by time
        result = []
        for name, data in projects.items():
            seconds = data['seconds']
            minutes = seconds // 60
            result.append({
                'name': name,
                'minutes': minutes,
                'formatted': self._format_duration(seconds),
                'entry_count': len(data['entries'])
            })

        # Sort by minutes descending
        result.sort(key=lambda x: x['minutes'], reverse=True)

        return result

    def _get_rolling_7_days_detail_from_entries(self, all_entries: List[Dict], today: datetime) -> List[Dict]:
        """Get detailed breakdown for the last 7 days using pre-fetched entries."""
        days = []

        for i in range(7):
            date = today - timedelta(days=i + 1)
            # Filter entries for this day locally
            day_entries = self._filter_entries_by_date(all_entries, date)

            # Get actual projects for this day
            projects = self._get_project_breakdown(day_entries)
            total_mins = sum(p['minutes'] for p in projects)

            day_data = {
                'date': date.strftime('%Y-%m-%d'),
                'date_display': date.strftime('%a %b %d'),
                'projects': projects,
                'total_mins': total_mins,
                'formatted': self._format_duration(total_mins * 60),
                'score': self._calculate_percent(total_mins, self.daily_goal)
            }
            days.append(day_data)

        return days

    def _format_duration(self, seconds: int) -> str:
        """Format seconds as Xh Ym."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def validate_configuration(self) -> bool:
        """Validate service configuration."""
        try:
            if not self.toggl.validate_credentials():
                self.logger.error("Toggl credentials invalid")
                return False

            self.logger.info("Configuration validated successfully")
            return True

        except Exception as e:
            self.logger.error(f"Configuration validation failed: {str(e)}")
            return False


if __name__ == "__main__":
    import yaml

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = yaml.safe_load(f)
        productivity_config = config.get('productivity_report', {})
    else:
        productivity_config = {'daily_goal_minutes': 360}

    service = ProductivityService(productivity_config)

    if service.validate_configuration():
        print("Configuration valid!")
        report = service.get_productivity_report()

        print(f"\n=== Yesterday's Projects ===")
        for p in report['yesterday_projects']:
            print(f"  {p['name']}: {p['formatted']} ({p['minutes']} mins)")

        print(f"\nTotal: {report['yesterday_total']} mins ({report['yesterday_percent']}%)")
        print(f"7-day average: {report['week_avg']} mins ({report['week_avg_percent']}%)")
        print(f"30-day average: {report['month_avg']} mins ({report['month_avg_percent']}%)")
    else:
        print("Configuration invalid - check your Toggl credentials")

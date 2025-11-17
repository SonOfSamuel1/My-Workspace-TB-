"""
Daily Report Generator for Toggl Track

Aggregates time tracking data and generates daily performance reports.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict


class DailyReportGenerator:
    """Generates daily performance reports from Toggl time entries."""

    def __init__(self, toggl_service, config: Dict):
        """
        Initialize Daily Report Generator.

        Args:
            toggl_service: TogglService instance for fetching time entries
            config: Configuration dictionary
        """
        self.toggl = toggl_service
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Get configuration values
        self.daily_goal_hours = config.get('report', {}).get('daily_goal_hours', 8.0)
        self.week_start_day = config.get('report', {}).get('week_start_day', 0)  # Monday

    def generate_daily_report(self, target_date: Optional[datetime] = None) -> Dict:
        """
        Generate a daily performance report for the specified date.

        Args:
            target_date: Date to generate report for (defaults to today)

        Returns:
            Dictionary containing report data
        """
        if not target_date:
            target_date = datetime.now()

        # Set date boundaries
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=0)

        self.logger.info(f"Generating daily report for {target_date.strftime('%Y-%m-%d')}")

        # Fetch time entries for the day
        entries = self.toggl.get_time_entries(start_date=start_of_day, end_date=end_of_day)

        if not entries:
            self.logger.warning(f"No time entries found for {target_date.strftime('%Y-%m-%d')}")

        # Calculate metrics
        report_data = {
            'date': target_date,
            'date_formatted': target_date.strftime('%A, %B %d, %Y'),
            'total_hours': self._calculate_total_hours(entries),
            'project_breakdown': self._calculate_project_breakdown(entries),
            'billable_breakdown': self._calculate_billable_breakdown(entries),
            'daily_goal_comparison': self._calculate_goal_comparison(entries),
            'week_to_date_summary': self._calculate_week_summary(target_date),
            'entry_count': len(entries),
            'entries': entries
        }

        self.logger.info(
            f"Report generated: {report_data['total_hours']:.2f} hours tracked, "
            f"{report_data['entry_count']} entries"
        )

        return report_data

    def _calculate_total_hours(self, entries: List[Dict]) -> float:
        """Calculate total hours from time entries."""
        total_seconds = sum(entry.get('duration_seconds', 0) for entry in entries)
        return total_seconds / 3600.0

    def _calculate_project_breakdown(self, entries: List[Dict]) -> List[Dict]:
        """
        Calculate time breakdown by project.

        Returns:
            List of dictionaries with project name and hours, sorted by hours (descending)
        """
        project_hours = defaultdict(float)

        for entry in entries:
            project_name = entry.get('project_name') or '(No Project)'
            hours = entry.get('duration_seconds', 0) / 3600.0
            project_hours[project_name] += hours

        # Convert to list of dicts and sort by hours (descending)
        breakdown = [
            {
                'project': project,
                'hours': hours,
                'percentage': 0.0  # Will be calculated after we know total
            }
            for project, hours in project_hours.items()
        ]

        # Calculate percentages
        total_hours = sum(item['hours'] for item in breakdown)
        if total_hours > 0:
            for item in breakdown:
                item['percentage'] = (item['hours'] / total_hours) * 100

        # Sort by hours (descending)
        breakdown.sort(key=lambda x: x['hours'], reverse=True)

        return breakdown

    def _calculate_billable_breakdown(self, entries: List[Dict]) -> Dict:
        """
        Calculate billable vs non-billable hours.

        Returns:
            Dictionary with billable and non_billable hours and percentages
        """
        billable_seconds = sum(
            entry.get('duration_seconds', 0)
            for entry in entries
            if entry.get('billable', False)
        )

        non_billable_seconds = sum(
            entry.get('duration_seconds', 0)
            for entry in entries
            if not entry.get('billable', False)
        )

        billable_hours = billable_seconds / 3600.0
        non_billable_hours = non_billable_seconds / 3600.0
        total_hours = billable_hours + non_billable_hours

        billable_percentage = (billable_hours / total_hours * 100) if total_hours > 0 else 0
        non_billable_percentage = (non_billable_hours / total_hours * 100) if total_hours > 0 else 0

        return {
            'billable_hours': billable_hours,
            'non_billable_hours': non_billable_hours,
            'total_hours': total_hours,
            'billable_percentage': billable_percentage,
            'non_billable_percentage': non_billable_percentage
        }

    def _calculate_goal_comparison(self, entries: List[Dict]) -> Dict:
        """
        Compare actual hours to daily goal.

        Returns:
            Dictionary with goal, actual, difference, and achievement percentage
        """
        actual_hours = self._calculate_total_hours(entries)
        goal_hours = self.daily_goal_hours
        difference = actual_hours - goal_hours
        percentage = (actual_hours / goal_hours * 100) if goal_hours > 0 else 0

        # Determine status
        if percentage >= 100:
            status = 'goal_met'
            status_text = '✓ Goal Met'
        elif percentage >= 80:
            status = 'close'
            status_text = '~ Close to Goal'
        else:
            status = 'below_goal'
            status_text = '✗ Below Goal'

        return {
            'goal_hours': goal_hours,
            'actual_hours': actual_hours,
            'difference': difference,
            'percentage': percentage,
            'status': status,
            'status_text': status_text
        }

    def _calculate_week_summary(self, target_date: datetime) -> Dict:
        """
        Calculate week-to-date summary.

        Args:
            target_date: Reference date for the week

        Returns:
            Dictionary with week summary data
        """
        # Calculate week start (based on configured week_start_day)
        days_since_week_start = (target_date.weekday() - self.week_start_day) % 7
        week_start = target_date - timedelta(days=days_since_week_start)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        # Week end is the target date
        week_end = target_date.replace(hour=23, minute=59, second=59, microsecond=0)

        self.logger.debug(
            f"Calculating week summary from {week_start.strftime('%Y-%m-%d')} "
            f"to {week_end.strftime('%Y-%m-%d')}"
        )

        # Fetch all entries for the week
        week_entries = self.toggl.get_time_entries(start_date=week_start, end_date=week_end)

        # Calculate total week hours
        total_week_hours = self._calculate_total_hours(week_entries)

        # Calculate days elapsed in week (including today)
        days_elapsed = days_since_week_start + 1

        # Calculate average hours per day
        average_hours_per_day = total_week_hours / days_elapsed if days_elapsed > 0 else 0

        # Calculate expected hours (goal * days elapsed)
        expected_hours = self.daily_goal_hours * days_elapsed

        # Week-to-date percentage
        wtd_percentage = (total_week_hours / expected_hours * 100) if expected_hours > 0 else 0

        return {
            'week_start': week_start,
            'week_start_formatted': week_start.strftime('%B %d'),
            'week_end_formatted': week_end.strftime('%B %d, %Y'),
            'total_hours': total_week_hours,
            'days_elapsed': days_elapsed,
            'average_hours_per_day': average_hours_per_day,
            'expected_hours': expected_hours,
            'difference': total_week_hours - expected_hours,
            'percentage': wtd_percentage,
            'entry_count': len(week_entries)
        }

    def get_detailed_entries(self, target_date: Optional[datetime] = None) -> List[Dict]:
        """
        Get detailed time entries for the specified date.

        Args:
            target_date: Date to get entries for (defaults to today)

        Returns:
            List of formatted time entries
        """
        if not target_date:
            target_date = datetime.now()

        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=0)

        entries = self.toggl.get_time_entries(start_date=start_of_day, end_date=end_of_day)

        # Sort by start time
        entries.sort(key=lambda x: x.get('start_time', datetime.min))

        return entries


if __name__ == "__main__":
    # Test the report generator
    import sys
    import yaml
    sys.path.append('..')
    from toggl_service import TogglService

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        # Load config
        with open('../config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        # Initialize services
        toggl = TogglService('../.env')
        generator = DailyReportGenerator(toggl, config)

        # Generate report
        report = generator.generate_daily_report()

        # Print summary
        print(f"\n{'='*60}")
        print(f"Daily Report for {report['date_formatted']}")
        print(f"{'='*60}\n")
        print(f"Total Hours: {report['total_hours']:.2f}h")
        print(f"Daily Goal: {report['daily_goal_comparison']['goal_hours']:.2f}h")
        print(f"Achievement: {report['daily_goal_comparison']['percentage']:.1f}%")
        print(f"Status: {report['daily_goal_comparison']['status_text']}\n")

        print("Project Breakdown:")
        for project in report['project_breakdown']:
            print(f"  • {project['project']}: {project['hours']:.2f}h ({project['percentage']:.1f}%)")

        print(f"\nBillable: {report['billable_breakdown']['billable_hours']:.2f}h "
              f"({report['billable_breakdown']['billable_percentage']:.1f}%)")
        print(f"Non-Billable: {report['billable_breakdown']['non_billable_hours']:.2f}h "
              f"({report['billable_breakdown']['non_billable_percentage']:.1f}%)")

        print(f"\nWeek-to-Date ({report['week_to_date_summary']['week_start_formatted']} - "
              f"{report['week_to_date_summary']['week_end_formatted']}):")
        print(f"  Total: {report['week_to_date_summary']['total_hours']:.2f}h")
        print(f"  Average/Day: {report['week_to_date_summary']['average_hours_per_day']:.2f}h")
        print(f"  Expected: {report['week_to_date_summary']['expected_hours']:.2f}h")
        print(f"  Achievement: {report['week_to_date_summary']['percentage']:.1f}%")

    except Exception as e:
        print(f"Error generating report: {str(e)}")
        import traceback
        traceback.print_exc()

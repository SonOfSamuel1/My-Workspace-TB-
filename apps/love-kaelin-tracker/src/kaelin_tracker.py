"""
Kaelin Development Tracking Service

This module monitors father-daughter development activities including:
- Daily play time with rolling 100-day average
- Daddy Days planning (quarterly)
- Jesus teachings progress
- Monthly game introductions
- Ivy League preparation programs
- Social development programs
- Spiritual development planning
- Christmas planning
- Crafting activities
- Imaginative play games
- Field trips (minimum 3/year)
- Gift planning
- Fun contests
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import pytz

logger = logging.getLogger(__name__)


class KaelinTracker:
    """Main service for tracking Kaelin development activities."""

    def __init__(
        self,
        calendar_service,
        docs_service,
        toggl_service,
        config: Dict
    ):
        """
        Initialize Kaelin Tracker.

        Args:
            calendar_service: Google Calendar service instance
            docs_service: Google Docs service instance
            toggl_service: Toggl service instance
            config: Configuration dictionary
        """
        self.calendar_service = calendar_service
        self.docs_service = docs_service
        self.toggl_service = toggl_service
        self.config = config
        self.timezone = pytz.timezone(config.get('timezone', 'America/New_York'))

    def generate_report(self) -> Dict:
        """
        Generate comprehensive Kaelin development tracking report.

        Returns:
            Dictionary containing all tracking data and alerts
        """
        logger.info("Generating Kaelin development tracking report...")

        report = {
            'timestamp': datetime.now(self.timezone).isoformat(),
            'play_time': self._check_play_time(),
            'daddy_days': self._check_daddy_days(),
            'jesus_teachings': self._check_jesus_teachings(),
            'monthly_games': self._check_monthly_games(),
            'ivy_league_programs': self._check_ivy_league_programs(),
            'social_programs': self._check_social_programs(),
            'spiritual_development': self._check_spiritual_development(),
            'christmas_planning': self._check_christmas_planning(),
            'crafting_activities': self._check_crafting(),
            'imaginative_play': self._check_imaginative_play(),
            'field_trips': self._check_field_trips(),
            'gift_planning': self._check_gift_planning(),
            'fun_contests': self._check_fun_contests(),
            'toggl_stats': self._get_toggl_statistics(),
            'alerts': []
        }

        # Generate alerts based on findings
        report['alerts'] = self._generate_alerts(report)

        logger.info(f"Report generated with {len(report['alerts'])} alerts")
        return report

    def _check_play_time(self) -> Dict:
        """
        Check daily play time and calculate rolling 100-day average.

        Returns:
            Dictionary with play time statistics
        """
        logger.info("Checking play time with rolling 100-day average...")

        now = datetime.now(self.timezone)
        rolling_start = now - timedelta(days=100)

        # Get play time from calendar
        play_events = self.calendar_service.get_events(
            start_date=rolling_start,
            end_date=now,
            search_terms=self.config.get('calendar', {}).get('play_time_terms', [
                'play with kaelin', 'kaelin time', 'daddy daughter time'
            ])
        )

        # Calculate daily play time
        daily_play = defaultdict(float)
        for event in play_events:
            date_key = event['start'].strftime('%Y-%m-%d')
            duration = (event['end'] - event['start']).total_seconds() / 3600  # hours
            daily_play[date_key] += duration

        # Calculate statistics
        total_days_with_play = len(daily_play)
        total_hours = sum(daily_play.values())

        # Rolling 100-day average (days played)
        rolling_days_avg = (total_days_with_play / 100) * 100  # percentage

        # Average hours per play day
        avg_hours_per_play_day = total_hours / total_days_with_play if total_days_with_play > 0 else 0

        # Recent 7 days
        week_ago = now - timedelta(days=7)
        recent_days = sum(1 for date_str in daily_play.keys()
                         if datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=self.timezone) >= week_ago)

        # Get last play date
        last_play_date = max(daily_play.keys()) if daily_play else None
        days_since_play = 0
        if last_play_date:
            last_date = datetime.strptime(last_play_date, '%Y-%m-%d').replace(tzinfo=self.timezone)
            days_since_play = (now - last_date).days

        return {
            'rolling_100_days_played': total_days_with_play,
            'rolling_100_avg_percentage': rolling_days_avg,
            'total_hours_100_days': round(total_hours, 1),
            'avg_hours_per_play_day': round(avg_hours_per_play_day, 1),
            'days_played_last_7_days': recent_days,
            'last_play_date': last_play_date,
            'days_since_last_play': days_since_play,
            'target_days_per_week': self.config.get('tracking_periods', {}).get('play_days_per_week_target', 5),
            'target_hours_per_day': self.config.get('tracking_periods', {}).get('play_hours_per_day_target', 2.0),
            'daily_breakdown': dict(sorted(daily_play.items(), reverse=True)[:14])  # Last 14 days
        }

    def _check_daddy_days(self) -> Dict:
        """
        Check Daddy Days planned for next 4 quarters.

        Returns:
            Dictionary with daddy day planning status
        """
        logger.info("Checking Daddy Days planning...")

        now = datetime.now(self.timezone)
        quarters_to_check = self.config.get('tracking_periods', {}).get('daddy_day_quarters_ahead', 4)

        # Calculate quarters
        quarters = []
        for i in range(quarters_to_check):
            quarter_start = now + timedelta(days=90 * i)
            quarter_end = quarter_start + timedelta(days=90)
            quarters.append({
                'number': i + 1,
                'start': quarter_start,
                'end': quarter_end,
                'label': f"Q{((quarter_start.month - 1) // 3) + 1} {quarter_start.year}"
            })

        # Get daddy day events from calendar
        end_date = now + timedelta(days=90 * quarters_to_check)
        daddy_day_events = self.calendar_service.get_events(
            start_date=now,
            end_date=end_date,
            search_terms=self.config.get('calendar', {}).get('daddy_day_terms', [
                'daddy day', 'kaelin daddy day', 'special day kaelin'
            ])
        )

        # Map events to quarters
        for quarter in quarters:
            quarter['events'] = [
                {
                    'date': event['start'].strftime('%Y-%m-%d'),
                    'title': event.get('summary', 'Daddy Day'),
                    'description': event.get('description', '')
                }
                for event in daddy_day_events
                if quarter['start'] <= event['start'] <= quarter['end']
            ]
            quarter['has_plan'] = len(quarter['events']) > 0

        missing_quarters = [q['label'] for q in quarters if not q['has_plan']]

        return {
            'quarters_checked': quarters_to_check,
            'quarters': quarters,
            'total_planned': sum(len(q['events']) for q in quarters),
            'missing_quarters': missing_quarters,
            'coverage_percentage': ((quarters_to_check - len(missing_quarters)) / quarters_to_check) * 100
        }

    def _check_jesus_teachings(self) -> Dict:
        """
        Check progress on teaching Jesus's teachings to Kaelin.

        Returns:
            Dictionary with teaching progress
        """
        logger.info("Checking Jesus teachings progress...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        teachings_section = self._parse_section(doc_data, 'JESUS TEACHINGS PROGRESS')

        total_teachings = len(self.config.get('jesus_teachings', {}).get('teachings', []))

        # Parse teaching entries
        taught_teachings = []
        not_taught = []

        for line in teachings_section:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('**'):
                continue

            # Look for teaching entries with dates
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3:
                    teaching_name = parts[0].lstrip('0123456789. ')
                    date_taught = parts[1]

                    if date_taught and date_taught != 'Not yet taught' and date_taught != '-':
                        taught_teachings.append({
                            'name': teaching_name,
                            'date': date_taught,
                            'understanding': parts[2] if len(parts) > 2 else 'Unknown',
                            'notes': parts[3] if len(parts) > 3 else ''
                        })
                    else:
                        not_taught.append(teaching_name)

        return {
            'total_teachings': total_teachings,
            'taught_count': len(taught_teachings),
            'not_taught_count': len(not_taught),
            'progress_percentage': (len(taught_teachings) / total_teachings * 100) if total_teachings > 0 else 0,
            'taught_teachings': taught_teachings,
            'not_taught_teachings': not_taught[:5],  # First 5 not taught
            'recent_teachings': taught_teachings[-3:] if taught_teachings else []  # Last 3 taught
        }

    def _check_monthly_games(self) -> Dict:
        """
        Check monthly game introduction tracking.

        Returns:
            Dictionary with game introduction data
        """
        logger.info("Checking monthly games introduced...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        games_section = self._parse_section(doc_data, 'MONTHLY GAMES INTRODUCED')

        now = datetime.now(self.timezone)
        current_month = now.strftime('%Y-%m')

        games = []
        game_introduced_this_month = False
        last_game_date = None

        for line in games_section:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('**'):
                continue

            # Parse game entries: YYYY-MM | Game Name | Type | Response
            if '|' in line and line[0].isdigit():
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2:
                    month = parts[0]
                    game_name = parts[1]

                    games.append({
                        'month': month,
                        'name': game_name,
                        'type': parts[2] if len(parts) > 2 else 'Unknown',
                        'response': parts[3] if len(parts) > 3 else ''
                    })

                    if month == current_month:
                        game_introduced_this_month = True

                    # Track most recent
                    if not last_game_date or month > last_game_date:
                        last_game_date = month

        # Calculate days since last game
        days_since_last_game = None
        if last_game_date:
            last_date = datetime.strptime(last_game_date + '-01', '%Y-%m-%d').replace(tzinfo=self.timezone)
            days_since_last_game = (now - last_date).days

        return {
            'total_games': len(games),
            'game_this_month': game_introduced_this_month,
            'last_game_month': last_game_date,
            'days_since_last_game': days_since_last_game,
            'recent_games': games[-6:] if games else [],  # Last 6 months
            'frequency_target_days': self.config.get('tracking_periods', {}).get('new_game_frequency_days', 30)
        }

    def _check_ivy_league_programs(self) -> Dict:
        """
        Check Ivy League preparation programs researched and enrolled.

        Returns:
            Dictionary with program tracking data
        """
        logger.info("Checking Ivy League preparation programs...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        programs_section = self._parse_section(doc_data, 'IVY LEAGUE PREPARATION PROGRAMS')

        categories = self.config.get('development_areas', {}).get('ivy_league_prep', [])

        programs = {
            'researched': 0,
            'enrolled': 0,
            'completed': 0,
            'programs': []
        }

        current_program = {}
        for line in programs_section:
            line = line.strip()

            if line.startswith('- Program Name:'):
                if current_program:
                    programs['programs'].append(current_program)
                current_program = {'name': line.split(':', 1)[1].strip()}
            elif line.startswith('- Type:') and current_program:
                current_program['type'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Status:') and current_program:
                status = line.split(':', 1)[1].strip().lower()
                current_program['status'] = status
                if 'researched' in status:
                    programs['researched'] += 1
                if 'enrolled' in status:
                    programs['enrolled'] += 1
                if 'completed' in status:
                    programs['completed'] += 1

        if current_program:
            programs['programs'].append(current_program)

        return {
            'total_programs': len(programs['programs']),
            'researched_count': programs['researched'],
            'enrolled_count': programs['enrolled'],
            'completed_count': programs['completed'],
            'categories_available': len(categories),
            'programs': programs['programs']
        }

    def _check_social_programs(self) -> Dict:
        """
        Check social development programs for making friends.

        Returns:
            Dictionary with social program data
        """
        logger.info("Checking social development programs...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        programs_section = self._parse_section(doc_data, 'SOCIAL DEVELOPMENT PROGRAMS')

        active_programs = []
        past_programs = []

        current_program = {}
        for line in programs_section:
            line = line.strip()

            if line.startswith('- Program Name:'):
                if current_program:
                    if current_program.get('status', '').lower() == 'active':
                        active_programs.append(current_program)
                    else:
                        past_programs.append(current_program)
                current_program = {'name': line.split(':', 1)[1].strip()}
            elif line.startswith('- Frequency:') and current_program:
                current_program['frequency'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Status:') and current_program:
                current_program['status'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Friends Made:') and current_program:
                current_program['friends'] = line.split(':', 1)[1].strip()

        if current_program:
            if current_program.get('status', '').lower() == 'active':
                active_programs.append(current_program)
            else:
                past_programs.append(current_program)

        return {
            'active_programs': len(active_programs),
            'past_programs': len(past_programs),
            'total_programs': len(active_programs) + len(past_programs),
            'programs': {
                'active': active_programs,
                'past': past_programs
            }
        }

    def _check_spiritual_development(self) -> Dict:
        """
        Check 6-month spiritual development planning.

        Returns:
            Dictionary with spiritual planning data
        """
        logger.info("Checking spiritual development planning...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        spiritual_section = self._parse_section(doc_data, 'SPIRITUAL DEVELOPMENT PLAN')

        months_planned = 0
        months_completed = 0
        current_month = None

        for line in spiritual_section:
            line = line.strip()

            if line.startswith('**Month'):
                # Extract month info
                if '-' in line:
                    month_name = line.split('-')[1].split('**')[0].strip()
                    current_month = month_name
            elif line.startswith('- Status:') and current_month:
                status = line.split(':', 1)[1].strip().lower()
                months_planned += 1
                if 'complete' in status:
                    months_completed += 1

        target_months = self.config.get('tracking_periods', {}).get('spiritual_planning_months', 6)

        return {
            'target_months': target_months,
            'months_planned': months_planned,
            'months_completed': months_completed,
            'planning_status': 'Complete' if months_planned >= target_months else 'Incomplete',
            'completion_percentage': (months_completed / months_planned * 100) if months_planned > 0 else 0
        }

    def _check_christmas_planning(self) -> Dict:
        """
        Check Christmas planning status.

        Returns:
            Dictionary with Christmas planning data
        """
        logger.info("Checking Christmas planning...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        christmas_section = self._parse_section(doc_data, 'CHRISTMAS PLANNING')

        traditions_planned = 0
        activities_planned = 0
        experiences_planned = 0

        for line in christmas_section:
            line = line.strip().lower()

            if 'tradition:' in line or 'activity:' in line or 'experience:' in line:
                if 'planned' in line or 'completed' in line:
                    if 'tradition' in line:
                        traditions_planned += 1
                    elif 'activity' in line:
                        activities_planned += 1
                    elif 'experience' in line:
                        experiences_planned += 1

        total_planned = traditions_planned + activities_planned + experiences_planned

        return {
            'traditions_planned': traditions_planned,
            'activities_planned': activities_planned,
            'experiences_planned': experiences_planned,
            'total_planned': total_planned,
            'has_spiritual_focus': 'spiritual focus' in '\n'.join(christmas_section).lower()
        }

    def _check_crafting(self) -> Dict:
        """
        Check crafting activities completed and planned.

        Returns:
            Dictionary with crafting data
        """
        logger.info("Checking crafting activities...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        crafting_section = self._parse_section(doc_data, 'CRAFTING ACTIVITIES')

        completed_crafts = 0
        planned_crafts = 0
        high_enjoyment = 0

        for line in crafting_section:
            line = line.strip()

            if line.startswith('- Date:') and line.count('|') > 0:
                completed_crafts += 1
                if 'high' in line.lower():
                    high_enjoyment += 1
            elif line.startswith('- Craft Idea:'):
                planned_crafts += 1

        return {
            'completed_crafts': completed_crafts,
            'planned_crafts': planned_crafts,
            'high_enjoyment_count': high_enjoyment,
            'success_rate': (high_enjoyment / completed_crafts * 100) if completed_crafts > 0 else 0
        }

    def _check_imaginative_play(self) -> Dict:
        """
        Check imaginative play games.

        Returns:
            Dictionary with imaginative play data
        """
        logger.info("Checking imaginative play games...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        play_section = self._parse_section(doc_data, 'IMAGINATIVE PLAY GAMES')

        games_played = 0
        games_planned = 0
        high_engagement = 0

        for line in play_section:
            line = line.strip()

            if line.startswith('- Date:'):
                games_played += 1
                if 'high' in line.lower():
                    high_engagement += 1
            elif line.startswith('- Game Idea:'):
                games_planned += 1

        return {
            'games_played': games_played,
            'games_planned': games_planned,
            'high_engagement_count': high_engagement,
            'engagement_rate': (high_engagement / games_played * 100) if games_played > 0 else 0
        }

    def _check_field_trips(self) -> Dict:
        """
        Check field trips (minimum 3 per year).

        Returns:
            Dictionary with field trip data
        """
        logger.info("Checking field trips...")

        now = datetime.now(self.timezone)
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0)

        # Get field trips from calendar
        field_trip_events = self.calendar_service.get_events(
            start_date=year_start,
            end_date=now,
            search_terms=self.config.get('calendar', {}).get('field_trip_terms', [
                'kaelin field trip', 'field trip', 'kaelin outing'
            ])
        )

        trips_this_year = len(field_trip_events)
        target = self.config.get('tracking_periods', {}).get('field_trips_per_year_target', 3)

        # Get last trip date
        last_trip_date = None
        days_since_trip = None
        if field_trip_events:
            last_trip = max(field_trip_events, key=lambda x: x['start'])
            last_trip_date = last_trip['start'].strftime('%Y-%m-%d')
            days_since_trip = (now - last_trip['start']).days

        return {
            'trips_this_year': trips_this_year,
            'target_per_year': target,
            'target_met': trips_this_year >= target,
            'last_trip_date': last_trip_date,
            'days_since_last_trip': days_since_trip,
            'recent_trips': [
                {
                    'date': event['start'].strftime('%Y-%m-%d'),
                    'title': event.get('summary', 'Field Trip'),
                    'description': event.get('description', '')
                }
                for event in sorted(field_trip_events, key=lambda x: x['start'], reverse=True)[:5]
            ]
        }

    def _check_gift_planning(self) -> Dict:
        """
        Check gift planning list.

        Returns:
            Dictionary with gift planning data
        """
        logger.info("Checking gift planning...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        gift_section = self._parse_section(doc_data, 'GIFT PLANNING')

        total_ideas = 0
        purchased = 0
        wrapped = 0

        for line in gift_section:
            line = line.strip().lower()

            if 'gift idea:' in line:
                total_ideas += 1
            if 'status:' in line:
                if 'purchased' in line:
                    purchased += 1
                if 'wrapped' in line:
                    wrapped += 1

        return {
            'total_gift_ideas': total_ideas,
            'purchased_count': purchased,
            'wrapped_count': wrapped,
            'ready_to_give': wrapped
        }

    def _check_fun_contests(self) -> Dict:
        """
        Check fun contests created.

        Returns:
            Dictionary with contest data
        """
        logger.info("Checking fun contests...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        contest_section = self._parse_section(doc_data, 'FUN CONTESTS')

        contests_held = 0
        contest_ideas = 0

        for line in contest_section:
            line = line.strip()

            # Count completed contests (have a date)
            if line.startswith('-') and '|' in line and any(c.isdigit() for c in line.split('|')[0]):
                contests_held += 1
            # Count ideas
            elif 'contest idea' in line.lower() or line.startswith('- '):
                contest_ideas += 1

        now = datetime.now(self.timezone)
        current_month = now.strftime('%Y-%m')

        return {
            'contests_held': contests_held,
            'contest_ideas': contest_ideas,
            'current_month': current_month
        }

    def _get_toggl_statistics(self) -> Dict:
        """
        Get time tracking statistics from Toggl.

        Returns:
            Dictionary with time tracking stats
        """
        logger.info("Getting Toggl time tracking statistics...")

        project_name = self.config.get('toggl_project_name', 'Love Kaelin')

        try:
            # Get last 30 days of time entries
            stats = self.toggl_service.get_time_statistics(
                project_name=project_name,
                days=30
            )
            return stats
        except Exception as e:
            logger.warning(f"Could not fetch Toggl statistics: {e}")
            return {
                'total_hours': 0,
                'days_tracked': 0,
                'avg_hours_per_day': 0,
                'error': str(e)
            }

    def _parse_section(self, doc_content: str, section_name: str) -> List[str]:
        """
        Parse a specific section from the tracking document.

        Args:
            doc_content: Full document content
            section_name: Name of section to extract

        Returns:
            List of lines in the section
        """
        lines = doc_content.split('\n')
        in_section = False
        section_lines = []

        for line in lines:
            # Check if we're entering the section
            if section_name.upper() in line.upper() and (line.startswith('#') or line.startswith('##')):
                in_section = True
                continue

            # Check if we're exiting the section (next section starts)
            if in_section and line.strip().startswith('#'):
                break

            # Collect lines in section
            if in_section:
                section_lines.append(line)

        return section_lines

    def _generate_alerts(self, report: Dict) -> List[Dict]:
        """
        Generate alerts based on report findings.

        Args:
            report: Report data dictionary

        Returns:
            List of alert dictionaries
        """
        alerts = []
        alert_config = self.config.get('alerts', {})

        # Play time alerts
        play_time = report['play_time']
        if play_time['days_since_last_play'] >= alert_config.get('no_play_critical_days', 3):
            alerts.append({
                'level': 'critical',
                'category': 'Play Time',
                'message': f"No play time recorded for {play_time['days_since_last_play']} days!",
                'action': 'Schedule play time with Kaelin today'
            })
        elif play_time['days_since_last_play'] >= alert_config.get('no_play_warning_days', 2):
            alerts.append({
                'level': 'warning',
                'category': 'Play Time',
                'message': f"{play_time['days_since_last_play']} days without play time",
                'action': 'Plan play session soon'
            })

        # Rolling average alert
        target_percentage = alert_config.get('play_average_warning_threshold', 70)
        if play_time['rolling_100_avg_percentage'] < target_percentage:
            alerts.append({
                'level': 'warning',
                'category': 'Play Time Average',
                'message': f"Rolling 100-day average is {play_time['rolling_100_avg_percentage']:.1f}% (target: {target_percentage}%)",
                'action': 'Increase frequency of play time'
            })

        # Daddy Days alerts
        daddy_days = report['daddy_days']
        if len(daddy_days['missing_quarters']) > 0:
            alerts.append({
                'level': 'warning',
                'category': 'Daddy Days',
                'message': f"Missing Daddy Day plans for: {', '.join(daddy_days['missing_quarters'])}",
                'action': 'Schedule Daddy Days for upcoming quarters'
            })

        # Jesus Teachings alerts
        teachings = report['jesus_teachings']
        warning_threshold = alert_config.get('teaching_warning_threshold', 15)
        if teachings['not_taught_count'] >= warning_threshold:
            alerts.append({
                'level': 'info',
                'category': 'Jesus Teachings',
                'message': f"{teachings['not_taught_count']} teachings not yet taught",
                'action': 'Continue teaching Jesus\'s lessons regularly'
            })

        # Monthly Games alerts
        games = report['monthly_games']
        if not games['game_this_month']:
            alerts.append({
                'level': 'warning',
                'category': 'Monthly Games',
                'message': 'No new game introduced this month',
                'action': 'Introduce or purchase a new game'
            })

        # Field Trips alerts
        field_trips = report['field_trips']
        if not field_trips['target_met']:
            remaining = field_trips['target_per_year'] - field_trips['trips_this_year']
            alerts.append({
                'level': 'info',
                'category': 'Field Trips',
                'message': f"Need {remaining} more field trip(s) to meet annual goal",
                'action': 'Plan upcoming field trips'
            })

        # Spiritual Development alerts
        spiritual = report['spiritual_development']
        if spiritual['planning_status'] == 'Incomplete':
            alerts.append({
                'level': 'warning',
                'category': 'Spiritual Development',
                'message': f"Only {spiritual['months_planned']} of {spiritual['target_months']} months planned",
                'action': 'Complete 6-month spiritual development plan'
            })

        return alerts

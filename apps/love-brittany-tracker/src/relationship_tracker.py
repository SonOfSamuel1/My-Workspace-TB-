"""
Relationship Tracking Service - Love Brittany Action Plan Tracker

This module monitors relationship activities including:
- Date nights and babysitter bookings
- Unexpected gifts (quarterly)
- Letters written (every 3 weeks)
- Love action plan reviews
- Journal entries (monthly)
- Time together suggestions (monthly)
- Goal support actions (monthly)
- Toggl time tracking statistics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pytz

logger = logging.getLogger(__name__)


class RelationshipTracker:
    """Main service for tracking relationship activities."""

    def __init__(
        self,
        calendar_service,
        docs_service,
        toggl_service,
        config: Dict
    ):
        """
        Initialize Relationship Tracker.

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
        Generate comprehensive relationship tracking report.

        Returns:
            Dictionary containing all tracking data and alerts
        """
        logger.info("Generating relationship tracking report...")

        report = {
            'timestamp': datetime.now(self.timezone).isoformat(),
            'date_nights': self._check_date_nights(),
            'gifts': self._check_gifts(),
            'letters': self._check_letters(),
            'action_plan_reviews': self._check_action_plan_reviews(),
            'daily_gaps': self._check_daily_gaps(),
            'toggl_stats': self._get_toggl_statistics(),
            'journal_entries': self._check_journal_entries(),
            'time_suggestions': self._check_time_suggestions(),
            'goal_support': self._check_goal_support(),
            'alerts': []
        }

        # Generate alerts based on findings
        report['alerts'] = self._generate_alerts(report)

        logger.info(f"Report generated with {len(report['alerts'])} alerts")
        return report

    def _check_date_nights(self) -> Dict:
        """
        Check for date nights in next 12 months and verify babysitter bookings.

        Returns:
            Dictionary with date night status and alerts
        """
        logger.info("Checking date nights for next 12 months...")

        now = datetime.now(self.timezone)
        end_date = now + timedelta(days=365)

        # Get all events from calendar
        events = self.calendar_service.get_events(
            start_date=now,
            end_date=end_date,
            search_terms=['date night', 'date', 'romantic dinner']
        )

        date_nights = []
        missing_months = []

        # Check each month for date night coverage
        for month_offset in range(12):
            month_start = now + timedelta(days=30 * month_offset)
            month_end = month_start + timedelta(days=30)

            # Find date nights in this month
            month_events = [
                e for e in events
                if month_start <= e['start'] <= month_end
            ]

            if not month_events:
                missing_months.append(month_start.strftime('%B %Y'))
            else:
                # Check each date night for babysitter
                for event in month_events:
                    babysitter = self._check_babysitter_for_date(event)
                    date_nights.append({
                        'date': event['start'].strftime('%Y-%m-%d'),
                        'title': event.get('summary', 'Date Night'),
                        'has_babysitter': babysitter['found'],
                        'babysitter_name': babysitter.get('name'),
                        'has_reservation': self._check_reservation(event)
                    })

        return {
            'total_scheduled': len(date_nights),
            'date_nights': date_nights,
            'missing_months': missing_months,
            'coverage_percent': ((12 - len(missing_months)) / 12) * 100
        }

    def _check_babysitter_for_date(self, date_event: Dict) -> Dict:
        """
        Check if babysitter is scheduled for a date night.

        Args:
            date_event: Date night calendar event

        Returns:
            Dictionary with babysitter booking status
        """
        event_date = date_event['start']

        # Search for babysitter events on same day
        babysitter_events = self.calendar_service.get_events(
            start_date=event_date.replace(hour=0, minute=0),
            end_date=event_date.replace(hour=23, minute=59),
            search_terms=['babysitter', 'sitter', 'childcare']
        )

        if babysitter_events:
            return {
                'found': True,
                'name': babysitter_events[0].get('summary', 'Babysitter')
            }

        # Also check event description for babysitter mention
        description = date_event.get('description', '').lower()
        if any(term in description for term in ['babysitter', 'sitter', 'childcare']):
            return {'found': True, 'name': 'Mentioned in event'}

        return {'found': False}

    def _check_reservation(self, event: Dict) -> bool:
        """
        Check if reservation is made for date night.

        Args:
            event: Calendar event

        Returns:
            True if reservation confirmed
        """
        description = event.get('description', '').lower()
        summary = event.get('summary', '').lower()

        reservation_keywords = [
            'reservation', 'booked', 'confirmed', 'table',
            'reserved', 'booking', 'rsvp'
        ]

        return any(
            keyword in description or keyword in summary
            for keyword in reservation_keywords
        )

    def _check_gifts(self) -> Dict:
        """
        Check for unexpected gifts (should be every 3 months).

        Returns:
            Dictionary with gift tracking status
        """
        logger.info("Checking gift log...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        gifts = self._parse_section(doc_data, 'GIFTS')

        # Filter out placeholder/invalid dates
        valid_gifts = []
        for gift in gifts:
            try:
                datetime.strptime(gift['date'], '%Y-%m-%d')
                valid_gifts.append(gift)
            except ValueError:
                continue

        if not valid_gifts:
            return {
                'last_gift_date': None,
                'days_since_last': None,
                'is_overdue': True,
                'next_due_date': None,
                'gifts': []
            }

        # Sort gifts by date
        sorted_gifts = sorted(
            valid_gifts,
            key=lambda g: datetime.strptime(g['date'], '%Y-%m-%d'),
            reverse=True
        )

        last_gift_date = datetime.strptime(sorted_gifts[0]['date'], '%Y-%m-%d')
        days_since = (datetime.now() - last_gift_date).days
        is_overdue = days_since > 90  # 3 months

        next_due = last_gift_date + timedelta(days=90)

        return {
            'last_gift_date': last_gift_date.strftime('%Y-%m-%d'),
            'days_since_last': days_since,
            'is_overdue': is_overdue,
            'next_due_date': next_due.strftime('%Y-%m-%d'),
            'gifts': sorted_gifts[:5]  # Last 5 gifts
        }

    def _check_letters(self) -> Dict:
        """
        Check for letters written in book (every 3 weeks).

        Returns:
            Dictionary with letter tracking status
        """
        logger.info("Checking letter log...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        letters = self._parse_section(doc_data, 'LETTERS')

        # Filter out placeholder/invalid dates
        valid_letters = []
        for letter in letters:
            try:
                datetime.strptime(letter['date'], '%Y-%m-%d')
                valid_letters.append(letter)
            except ValueError:
                continue

        if not valid_letters:
            return {
                'last_letter_date': None,
                'days_since_last': None,
                'is_overdue': True,
                'next_due_date': None,
                'letters': []
            }

        sorted_letters = sorted(
            valid_letters,
            key=lambda l: datetime.strptime(l['date'], '%Y-%m-%d'),
            reverse=True
        )

        last_letter_date = datetime.strptime(sorted_letters[0]['date'], '%Y-%m-%d')
        days_since = (datetime.now() - last_letter_date).days
        is_overdue = days_since > 21  # 3 weeks

        next_due = last_letter_date + timedelta(days=21)

        return {
            'last_letter_date': last_letter_date.strftime('%Y-%m-%d'),
            'days_since_last': days_since,
            'is_overdue': is_overdue,
            'next_due_date': next_due.strftime('%Y-%m-%d'),
            'letters': sorted_letters[:5]
        }

    def _check_action_plan_reviews(self) -> Dict:
        """
        Check for action plan reviews and updates.

        Returns:
            Dictionary with review tracking status
        """
        logger.info("Checking action plan reviews...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        reviews = self._parse_section(doc_data, 'ACTION PLAN REVIEWS')

        # Filter out placeholder/invalid dates
        valid_reviews = []
        for review in reviews:
            try:
                datetime.strptime(review['date'], '%Y-%m-%d')
                valid_reviews.append(review)
            except ValueError:
                continue

        if not valid_reviews:
            return {
                'last_review_date': None,
                'days_since_last': None,
                'reviews': []
            }

        sorted_reviews = sorted(
            valid_reviews,
            key=lambda r: datetime.strptime(r['date'], '%Y-%m-%d'),
            reverse=True
        )

        last_review_date = datetime.strptime(sorted_reviews[0]['date'], '%Y-%m-%d')
        days_since = (datetime.now() - last_review_date).days

        return {
            'last_review_date': last_review_date.strftime('%Y-%m-%d'),
            'days_since_last': days_since,
            'reviews': sorted_reviews[:5]
        }

    def _check_daily_gaps(self) -> Dict:
        """
        Check calendar for daily 10-minute gaps for love action plan work.

        Returns:
            Dictionary with daily gap tracking
        """
        logger.info("Checking daily 10-minute gaps...")

        # Check last 7 days for gap entries
        now = datetime.now(self.timezone)
        start_date = now - timedelta(days=7)

        gap_events = self.calendar_service.get_events(
            start_date=start_date,
            end_date=now,
            search_terms=['love action', 'brittany time', 'relationship work']
        )

        # Count days with gaps
        days_with_gaps = len(set(e['start'].date() for e in gap_events))

        return {
            'days_tracked': 7,
            'days_completed': days_with_gaps,
            'completion_rate': (days_with_gaps / 7) * 100,
            'recent_gaps': gap_events[:10]
        }

    def _get_toggl_statistics(self) -> Dict:
        """
        Get Toggl time tracking statistics for Love Brittany project.

        Returns:
            Dictionary with time tracking stats
        """
        logger.info("Fetching Toggl statistics...")

        project_name = self.config.get('toggl_project_name', 'Love Brittany')

        # Get time entries for last 30 days
        now = datetime.now(self.timezone)
        start_date = now - timedelta(days=30)

        entries = self.toggl_service.get_time_entries(
            start_date=start_date,
            end_date=now
        )

        # Filter entries by project name
        if project_name:
            entries = [e for e in entries if e.get('project_name') == project_name]

        if not entries:
            return {
                'total_hours': 0,
                'total_days': 0,
                'entries_count': 0,
                'avg_per_day': 0,
                'recent_entries': []
            }

        total_seconds = sum(e.get('duration_seconds', 0) for e in entries)
        total_hours = total_seconds / 3600

        # Count unique days
        unique_days = len(set(
            datetime.fromisoformat(e['start']).date()
            for e in entries
        ))

        avg_per_day = total_hours / 30 if total_hours > 0 else 0

        return {
            'total_hours': round(total_hours, 2),
            'total_days': unique_days,
            'entries_count': len(entries),
            'avg_per_day': round(avg_per_day, 2),
            'recent_entries': entries[:10]
        }

    def _check_journal_entries(self) -> Dict:
        """
        Check for monthly journal entries about ways she expresses love.

        Returns:
            Dictionary with journal tracking status
        """
        logger.info("Checking journal entries...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        entries = self._parse_section(doc_data, 'JOURNAL ENTRIES')

        # Filter out placeholder/invalid dates
        valid_entries = []
        for entry in entries:
            try:
                datetime.strptime(entry['date'], '%Y-%m-%d')
                valid_entries.append(entry)
            except ValueError:
                continue

        if not valid_entries:
            return {
                'last_entry_date': None,
                'days_since_last': None,
                'is_overdue': True,
                'entries': []
            }

        sorted_entries = sorted(
            valid_entries,
            key=lambda e: datetime.strptime(e['date'], '%Y-%m-%d'),
            reverse=True
        )

        last_entry_date = datetime.strptime(sorted_entries[0]['date'], '%Y-%m-%d')
        days_since = (datetime.now() - last_entry_date).days
        is_overdue = days_since > 30  # Monthly

        return {
            'last_entry_date': last_entry_date.strftime('%Y-%m-%d'),
            'days_since_last': days_since,
            'is_overdue': is_overdue,
            'entries': sorted_entries[:5]
        }

    def _check_time_suggestions(self) -> Dict:
        """
        Check for monthly time together suggestions.

        Returns:
            Dictionary with suggestion tracking status
        """
        logger.info("Checking time together suggestions...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        suggestions = self._parse_section(doc_data, 'TIME TOGETHER')

        # Filter out placeholder/invalid dates
        valid_suggestions = []
        for suggestion in suggestions:
            try:
                datetime.strptime(suggestion['date'], '%Y-%m-%d')
                valid_suggestions.append(suggestion)
            except ValueError:
                continue

        if not valid_suggestions:
            return {
                'last_suggestion_date': None,
                'days_since_last': None,
                'is_overdue': True,
                'suggestions': []
            }

        sorted_suggestions = sorted(
            valid_suggestions,
            key=lambda s: datetime.strptime(s['date'], '%Y-%m-%d'),
            reverse=True
        )

        last_suggestion_date = datetime.strptime(sorted_suggestions[0]['date'], '%Y-%m-%d')
        days_since = (datetime.now() - last_suggestion_date).days
        is_overdue = days_since > 30  # Monthly

        return {
            'last_suggestion_date': last_suggestion_date.strftime('%Y-%m-%d'),
            'days_since_last': days_since,
            'is_overdue': is_overdue,
            'suggestions': sorted_suggestions[:5]
        }

    def _check_goal_support(self) -> Dict:
        """
        Check for monthly goal support actions.

        Returns:
            Dictionary with goal support tracking status
        """
        logger.info("Checking goal support actions...")

        doc_data = self.docs_service.get_document_content(
            self.config['tracking_doc_id']
        )

        actions = self._parse_section(doc_data, 'GOAL SUPPORT')

        # Filter out placeholder/invalid dates
        valid_actions = []
        for action in actions:
            try:
                # Try to parse the date - this will fail for placeholders like "YYYY-MM-DD"
                datetime.strptime(action['date'], '%Y-%m-%d')
                valid_actions.append(action)
            except ValueError:
                # Skip invalid/placeholder dates
                continue

        if not valid_actions:
            return {
                'last_action_date': None,
                'days_since_last': None,
                'is_overdue': True,
                'actions': []
            }

        sorted_actions = sorted(
            valid_actions,
            key=lambda a: datetime.strptime(a['date'], '%Y-%m-%d'),
            reverse=True
        )

        last_action_date = datetime.strptime(sorted_actions[0]['date'], '%Y-%m-%d')
        days_since = (datetime.now() - last_action_date).days
        is_overdue = days_since > 30  # Monthly

        return {
            'last_action_date': last_action_date.strftime('%Y-%m-%d'),
            'days_since_last': days_since,
            'is_overdue': is_overdue,
            'actions': sorted_actions[:5]
        }

    def _parse_section(self, doc_content: str, section_name: str) -> List[Dict]:
        """
        Parse a specific section from the tracking document.

        Args:
            doc_content: Full document content
            section_name: Name of section to parse

        Returns:
            List of parsed entries
        """
        entries = []

        # Find section markers
        section_marker = f"[{section_name}]"
        if section_marker not in doc_content:
            logger.warning(f"Section {section_name} not found in document")
            return entries

        # Extract section content
        section_start = doc_content.index(section_marker)
        section_end = doc_content.find('[', section_start + 1)

        if section_end == -1:
            section_content = doc_content[section_start:]
        else:
            section_content = doc_content[section_start:section_end]

        # Parse entries (format: □ Date: YYYY-MM-DD | Details)
        lines = section_content.split('\n')
        for line in lines:
            if 'Date:' in line:
                try:
                    # Extract date
                    date_part = line.split('Date:')[1].split('|')[0].strip()

                    # Extract details (everything after |)
                    details = ''
                    if '|' in line:
                        details = line.split('|', 1)[1].strip()

                    entries.append({
                        'date': date_part,
                        'details': details,
                        'completed': '☑' in line or '[x]' in line.lower()
                    })
                except (IndexError, ValueError) as e:
                    logger.warning(f"Failed to parse line: {line}, error: {e}")
                    continue

        return entries

    def _generate_alerts(self, report: Dict) -> List[Dict]:
        """
        Generate alerts based on report findings.

        Args:
            report: Complete tracking report

        Returns:
            List of alert dictionaries
        """
        alerts = []

        # Date night alerts
        date_nights = report['date_nights']
        if date_nights['missing_months']:
            alerts.append({
                'level': 'critical',
                'category': 'Date Nights',
                'message': f"Missing date nights in {len(date_nights['missing_months'])} months: {', '.join(date_nights['missing_months'][:3])}",
                'action': 'Schedule date nights for missing months'
            })

        # Check for date nights without babysitters
        no_sitter = [dn for dn in date_nights['date_nights'] if not dn['has_babysitter']]
        if no_sitter:
            alerts.append({
                'level': 'critical',
                'category': 'Babysitters',
                'message': f"{len(no_sitter)} date nights missing babysitter bookings",
                'action': 'Book babysitters for upcoming date nights'
            })

        # Gift alerts
        gifts = report['gifts']
        if gifts['is_overdue']:
            days_overdue = gifts['days_since_last'] - 90 if gifts['days_since_last'] else 0
            alerts.append({
                'level': 'critical',
                'category': 'Gifts',
                'message': f"Unexpected gift is overdue by {days_overdue} days",
                'action': 'Purchase and give an unexpected gift soon'
            })

        # Letter alerts
        letters = report['letters']
        if letters['is_overdue']:
            days_overdue = letters['days_since_last'] - 21 if letters['days_since_last'] else 0
            alerts.append({
                'level': 'critical',
                'category': 'Letters',
                'message': f"Letter in book is overdue by {days_overdue} days",
                'action': 'Write a love letter in the book'
            })

        # Journal alerts
        journal = report['journal_entries']
        if journal['is_overdue']:
            alerts.append({
                'level': 'warning',
                'category': 'Journal',
                'message': "Monthly journal entry about her love expressions is overdue",
                'action': 'Create journal entry documenting ways she shows love'
            })

        # Time suggestions alerts
        suggestions = report['time_suggestions']
        if suggestions['is_overdue']:
            alerts.append({
                'level': 'warning',
                'category': 'Time Together',
                'message': "Monthly time together suggestion is overdue",
                'action': 'Suggest ways to spend quality time together'
            })

        # Goal support alerts
        goals = report['goal_support']
        if goals['is_overdue']:
            alerts.append({
                'level': 'warning',
                'category': 'Goals',
                'message': "Monthly goal support action is overdue",
                'action': 'Take action to help her achieve her goals'
            })

        # Daily gaps alerts
        gaps = report['daily_gaps']
        if gaps['completion_rate'] < 50:
            alerts.append({
                'level': 'warning',
                'category': 'Daily Practice',
                'message': f"Only {gaps['completion_rate']:.0f}% daily 10-minute gaps completed this week",
                'action': 'Schedule daily 10-minute relationship focus time'
            })

        # Toggl tracking alerts
        toggl = report['toggl_stats']
        if toggl['total_hours'] < 5:  # Less than 5 hours in 30 days
            alerts.append({
                'level': 'info',
                'category': 'Time Investment',
                'message': f"Only {toggl['total_hours']} hours tracked in last 30 days",
                'action': 'Increase time dedicated to Love Brittany project'
            })

        return alerts

#!/usr/bin/env python3
"""
Email Builder Module

Generates styled HTML email digests for homeschool events
with inline CSS and Google Calendar 'Add to Calendar' buttons.
"""

import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import List

from event_parser import Event

logger = logging.getLogger(__name__)

# Category color mapping
CATEGORY_COLORS = {
    "field trips": {"bg": "#E8F5E9", "text": "#2E7D32", "border": "#4CAF50"},
    "co-ops": {"bg": "#E3F2FD", "text": "#1565C0", "border": "#42A5F5"},
    "workshops": {"bg": "#FFF3E0", "text": "#E65100", "border": "#FF9800"},
    "classes": {"bg": "#F3E5F5", "text": "#6A1B9A", "border": "#AB47BC"},
    "meetups": {"bg": "#E0F7FA", "text": "#00695C", "border": "#26C6DA"},
    "sports": {"bg": "#FBE9E7", "text": "#BF360C", "border": "#FF7043"},
    "arts": {"bg": "#FCE4EC", "text": "#AD1457", "border": "#EC407A"},
    "science fairs": {"bg": "#E8EAF6", "text": "#283593", "border": "#5C6BC0"},
    "support groups": {"bg": "#FFF8E1", "text": "#F57F17", "border": "#FFCA28"},
    "library programs": {"bg": "#E0F2F1", "text": "#004D40", "border": "#26A69A"},
    "parks & rec": {"bg": "#F1F8E9", "text": "#33691E", "border": "#8BC34A"},
}

DEFAULT_COLORS = {"bg": "#F5F5F5", "text": "#424242", "border": "#9E9E9E"}


class EmailBuilder:
    """Builds styled HTML email digests for homeschool events."""

    def __init__(self, timezone: str = "America/New_York"):
        self.timezone = timezone

    def build_html(self, events: List[Event], date_range: str = None) -> str:
        """Build the complete HTML email."""
        if not events:
            return self._build_no_events_html(date_range)

        # Sort events by date
        events_sorted = sorted(events, key=lambda e: e.date)

        # Calculate stats
        categories = Counter(e.category.lower() for e in events_sorted)
        unique_dates = len(set(e.date for e in events_sorted))

        if not date_range:
            first = events_sorted[0].date
            last = events_sorted[-1].date
            try:
                first_dt = datetime.strptime(first, "%Y-%m-%d")
                last_dt = datetime.strptime(last, "%Y-%m-%d")
                date_range = (
                    f"{first_dt.strftime('%b %d')} - {last_dt.strftime('%b %d, %Y')}"
                )
            except ValueError:
                date_range = f"{first} to {last}"

        # Build event cards
        event_cards_html = ""
        current_date = None
        for event in events_sorted:
            # Date section header
            if event.date != current_date:
                current_date = event.date
                try:
                    dt = datetime.strptime(event.date, "%Y-%m-%d")
                    date_display = dt.strftime("%A, %B %d, %Y")
                except ValueError:
                    date_display = event.date

                event_cards_html += f"""
                <tr>
                    <td style="padding: 20px 0 8px 0;">
                        <table width="100%" cellpadding="0" cellspacing="0" border="0">
                            <tr>
                                <td style="font-size: 16px; font-weight: bold; color: #1a237e; border-bottom: 2px solid #3f51b5; padding-bottom: 6px;">
                                    {date_display}
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>"""

            event_cards_html += self._build_event_card(event)

        # Build stats bar
        top_categories = categories.most_common(4)
        stats_items = ""
        for cat, count in top_categories:
            colors = CATEGORY_COLORS.get(cat, DEFAULT_COLORS)
            stats_items += f"""
                <td style="padding: 4px 8px; text-align: center;">
                    <span style="display: inline-block; background: {colors['bg']}; color: {colors['text']}; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold;">{cat.title()} ({count})</span>
                </td>"""

        # Next digest date (next Monday)
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)
        next_digest = next_monday.strftime("%B %d, %Y")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Homeschool Events in Gwinnett County</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f0f2f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f0f2f5;">
        <tr>
            <td align="center" style="padding: 20px 10px;">
                <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; width: 100%;">

                    <!-- Header -->
                    <tr>
                        <td style="border-top: 4px solid #00e5ff; background: linear-gradient(135deg, #4a148c 0%, #00695c 100%); padding: 32px 28px; border-radius: 12px 12px 0 0;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="font-size: 28px; font-weight: bold; color: #ffffff; text-transform: uppercase; letter-spacing: 1px; padding-bottom: 4px;">
                                        Homeschool Events
                                    </td>
                                </tr>
                                <tr>
                                    <td><div style="height: 2px; width: 40px; background: rgba(255,255,255,0.5); margin: 8px 0;"></div></td>
                                </tr>
                                <tr>
                                    <td style="font-size: 15px; color: rgba(255,255,255,0.8); padding-bottom: 16px;">
                                        Gwinnett County, GA
                                    </td>
                                </tr>
                                <tr>
                                    <td>
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 14px; color: rgba(255,255,255,0.85);">
                                                    {date_range}
                                                </td>
                                                <td align="right">
                                                    <span style="display: inline-block; background: rgba(255,255,255,0.2); color: #ffffff; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: bold;">&#x25CF; {len(events_sorted)} events</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Stats Bar -->
                    <tr>
                        <td style="background-color: #ffffff; padding: 14px 24px; border-bottom: 1px solid #e0e0e0;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="font-size: 13px; color: #757575; padding-bottom: 8px;">
                                        <strong>{len(events_sorted)}</strong> events &middot; <strong>{len(categories)}</strong> categories &middot; <strong>{unique_dates}</strong> days
                                    </td>
                                </tr>
                                <tr>
                                    {stats_items}
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Event Cards -->
                    <tr>
                        <td style="background-color: #ffffff; padding: 0 24px 24px 24px;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                {event_cards_html}
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f5f5f5; padding: 20px 24px; border-radius: 0 0 12px 12px; border-top: 1px solid #e0e0e0;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="font-size: 12px; color: #9e9e9e; line-height: 1.6;">
                                        Please verify all event details directly with organizers before attending. Dates, times, and locations are subject to change.
                                    </td>
                                </tr>
                                <tr>
                                    <td style="font-size: 12px; color: #9e9e9e; padding-top: 10px;">
                                        Next digest: {next_digest}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

        return html

    def _build_event_card(self, event: Event) -> str:
        """Build HTML for a single event card."""
        colors = CATEGORY_COLORS.get(event.category.lower(), DEFAULT_COLORS)

        # Category badge
        badge = f"""<span style="display: inline-block; background: {colors['bg']}; color: {colors['text']}; border: 1px solid {colors['border']}; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; text-transform: uppercase;">{event.category}</span>"""

        # Time display
        time_display = ""
        if event.start_time:
            time_display = event.start_time
            if event.end_time:
                time_display += f" - {event.end_time}"
        elif event.is_all_day:
            time_display = "All Day"

        # Location display
        location_html = ""
        if event.location:
            location_html = f"""
                <tr>
                    <td style="font-size: 13px; color: #616161; padding: 3px 0;">
                        &#x1F4CD; {event.location}
                    </td>
                </tr>"""

        # Description
        desc_html = ""
        if event.description:
            desc_html = f"""
                <tr>
                    <td style="font-size: 13px; color: #757575; padding: 6px 0; line-height: 1.5;">
                        {event.description}
                    </td>
                </tr>"""

        # Source
        source_html = ""
        if event.source:
            source_html = f"""
                <tr>
                    <td style="font-size: 11px; color: #9e9e9e; padding: 2px 0;">
                        Source: {event.source}
                    </td>
                </tr>"""

        # Buttons
        calendar_url = event.to_calendar_url()
        buttons_html = f"""
                <tr>
                    <td style="padding: 10px 0 0 0;">
                        <a href="{calendar_url}" target="_blank" style="display: inline-block; background-color: #1a73e8; color: #ffffff; padding: 8px 18px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: bold; margin-right: 8px;">&#x1F4C5; Add to Calendar</a>"""

        if event.url:
            buttons_html += f"""
                        <a href="{event.url}" target="_blank" style="display: inline-block; background-color: #ffffff; color: #1a73e8; padding: 8px 18px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: bold; border: 1px solid #1a73e8;">More Info</a>"""

        buttons_html += """
                    </td>
                </tr>"""

        return f"""
                <tr>
                    <td style="padding: 14px 0;">
                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #fafafa; border-radius: 10px; border-left: 4px solid {colors['border']};">
                            <tr>
                                <td style="padding: 16px;">
                                    <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                        <tr>
                                            <td style="padding-bottom: 6px;">
                                                {badge}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="font-size: 17px; font-weight: bold; color: #212121; padding: 4px 0;">
                                                {event.title}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="font-size: 13px; color: #1a73e8; font-weight: bold; padding: 3px 0;">
                                                &#x1F4C5; {time_display}
                                            </td>
                                        </tr>
                                        {location_html}
                                        {desc_html}
                                        {source_html}
                                        {buttons_html}
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>"""

    def _build_no_events_html(self, date_range: str = None) -> str:
        """Build HTML for when no events are found."""
        if not date_range:
            today = datetime.now()
            end = today + timedelta(days=30)
            date_range = f"{today.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Homeschool Events - No Events Found</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f0f2f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f0f2f5;">
        <tr>
            <td align="center" style="padding: 20px 10px;">
                <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; width: 100%;">
                    <tr>
                        <td style="border-top: 4px solid #00e5ff; background: linear-gradient(135deg, #4a148c 0%, #00695c 100%); padding: 32px 28px; border-radius: 12px 12px 0 0;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="font-size: 28px; font-weight: bold; color: #ffffff; text-transform: uppercase; letter-spacing: 1px; padding-bottom: 4px;">
                                        Homeschool Events
                                    </td>
                                </tr>
                                <tr>
                                    <td><div style="height: 2px; width: 40px; background: rgba(255,255,255,0.5); margin: 8px 0;"></div></td>
                                </tr>
                                <tr>
                                    <td style="font-size: 15px; color: rgba(255,255,255,0.8); padding-bottom: 16px;">
                                        Gwinnett County, GA
                                    </td>
                                </tr>
                                <tr>
                                    <td style="font-size: 14px; color: rgba(255,255,255,0.85);">
                                        {date_range}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color: #ffffff; padding: 40px 24px; text-align: center; border-radius: 0 0 12px 12px;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="font-size: 48px; padding-bottom: 16px;">&#x1F50D;</td>
                                </tr>
                                <tr>
                                    <td style="font-size: 18px; font-weight: bold; color: #424242; padding-bottom: 8px;">
                                        No Events Found This Week
                                    </td>
                                </tr>
                                <tr>
                                    <td style="font-size: 14px; color: #757575; line-height: 1.6;">
                                        We couldn't find any upcoming homeschool events in Gwinnett County for the selected date range. Check back next week for new listings!
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    def build_plain_text(self, events: List[Event], date_range: str = None) -> str:
        """Build a plain-text version of the digest."""
        if not events:
            return "Homeschool Events in Gwinnett County\n\nNo events found for this period.\n"

        events_sorted = sorted(events, key=lambda e: e.date)

        if not date_range:
            first = events_sorted[0].date
            last = events_sorted[-1].date
            date_range = f"{first} to {last}"

        lines = [
            "HOMESCHOOL EVENTS IN GWINNETT COUNTY",
            f"{date_range} | {len(events_sorted)} events found",
            "=" * 50,
            "",
        ]

        current_date = None
        for event in events_sorted:
            if event.date != current_date:
                current_date = event.date
                try:
                    dt = datetime.strptime(event.date, "%Y-%m-%d")
                    date_display = dt.strftime("%A, %B %d, %Y")
                except ValueError:
                    date_display = event.date
                lines.append(f"\n--- {date_display} ---\n")

            lines.append(f"[{event.category.upper()}] {event.title}")

            time_str = ""
            if event.start_time:
                time_str = f"  Time: {event.start_time}"
                if event.end_time:
                    time_str += f" - {event.end_time}"
            elif event.is_all_day:
                time_str = "  Time: All Day"
            if time_str:
                lines.append(time_str)

            if event.location:
                lines.append(f"  Location: {event.location}")
            if event.description:
                lines.append(f"  {event.description}")
            if event.url:
                lines.append(f"  More info: {event.url}")
            lines.append(f"  Add to Calendar: {event.to_calendar_url()}")
            if event.source:
                lines.append(f"  Source: {event.source}")
            lines.append("")

        lines.extend(
            [
                "-" * 50,
                "Please verify all event details directly with organizers.",
                "",
            ]
        )

        return "\n".join(lines)

    def generate_subject(self, events: List[Event], date_range: str = None) -> str:
        """Generate the email subject line."""
        if not date_range:
            today = datetime.now()
            end = today + timedelta(days=30)
            date_range = f"{today.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"

        count = len(events) if events else 0
        if count > 0:
            return (
                f"Homeschool Events in Gwinnett County - {date_range} ({count} events)"
            )
        return f"Homeschool Events in Gwinnett County - {date_range}"

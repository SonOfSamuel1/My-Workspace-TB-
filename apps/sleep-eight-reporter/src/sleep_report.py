#!/usr/bin/env python3
"""
Sleep Report Generator Module

Generates beautiful HTML email reports from Eight Sleep data.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SleepReportGenerator:
    """
    Generates HTML sleep reports from Eight Sleep data.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize report generator.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.report_config = self.config.get('sleep_report', {}).get('report', {})

    def generate_html_report(self, data: Dict[str, Any]) -> str:
        """
        Generate HTML email report from sleep data.

        Args:
            data: Sleep data dictionary from EightSleepService.get_full_report_data()

        Returns:
            HTML string for email
        """
        sleep_data = data.get('sleep_data', {})
        device_data = data.get('device_data', {})
        quality = data.get('quality_assessment', 'Unknown')

        # Format metrics
        sleep_score = sleep_data.get('sleep_score')
        fitness_score = sleep_data.get('sleep_fitness_score')
        routine_score = sleep_data.get('sleep_routine_score')

        time_slept = sleep_data.get('time_slept')
        time_slept_str = self._format_duration(time_slept)

        heart_rate = sleep_data.get('heart_rate')
        hrv = sleep_data.get('hrv')
        breath_rate = sleep_data.get('breath_rate')

        bed_temp = sleep_data.get('bed_temp')
        room_temp = device_data.get('room_temp')

        # Determine score colors
        score_color = self._get_score_color(sleep_score)
        quality_color = self._get_quality_color(quality)

        # Build HTML
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Sleep Report</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f7;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f5f5f7;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" cellpadding="0" cellspacing="0" width="600" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">

                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; border-radius: 12px 12px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 600;">
                                Sleep Report
                            </h1>
                            <p style="margin: 8px 0 0 0; color: #a0a0b0; font-size: 14px;">
                                {datetime.now().strftime('%A, %B %d, %Y')}
                            </p>
                        </td>
                    </tr>

                    <!-- Sleep Score Hero -->
                    <tr>
                        <td style="padding: 30px; text-align: center; border-bottom: 1px solid #e5e5e7;">
                            <div style="display: inline-block; background: {score_color}; border-radius: 50%; width: 120px; height: 120px; line-height: 120px; margin-bottom: 15px;">
                                <span style="color: white; font-size: 42px; font-weight: 700;">{sleep_score if sleep_score else '--'}</span>
                            </div>
                            <h2 style="margin: 0; color: #1a1a2e; font-size: 24px; font-weight: 600;">Sleep Score</h2>
                            <p style="margin: 8px 0 0 0; color: {quality_color}; font-size: 16px; font-weight: 500;">
                                {quality}
                            </p>
                        </td>
                    </tr>

                    <!-- Sleep Duration -->
                    <tr>
                        <td style="padding: 25px 30px; border-bottom: 1px solid #e5e5e7;">
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td width="60" style="vertical-align: top;">
                                        <div style="width: 50px; height: 50px; background-color: #e8f4fd; border-radius: 10px; text-align: center; line-height: 50px;">
                                            <span style="font-size: 24px;">&#128564;</span>
                                        </div>
                                    </td>
                                    <td style="vertical-align: middle; padding-left: 15px;">
                                        <p style="margin: 0; color: #86868b; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Time Asleep</p>
                                        <p style="margin: 4px 0 0 0; color: #1a1a2e; font-size: 24px; font-weight: 600;">{time_slept_str}</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Scores Grid -->
                    <tr>
                        <td style="padding: 25px 30px; border-bottom: 1px solid #e5e5e7;">
                            <h3 style="margin: 0 0 20px 0; color: #1a1a2e; font-size: 18px; font-weight: 600;">Sleep Quality Breakdown</h3>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td width="33%" style="text-align: center; padding: 10px;">
                                        <div style="background-color: #f5f5f7; border-radius: 10px; padding: 20px;">
                                            <p style="margin: 0; color: #86868b; font-size: 12px; text-transform: uppercase;">Fitness</p>
                                            <p style="margin: 8px 0 0 0; color: #1a1a2e; font-size: 28px; font-weight: 600;">{fitness_score if fitness_score else '--'}</p>
                                        </div>
                                    </td>
                                    <td width="33%" style="text-align: center; padding: 10px;">
                                        <div style="background-color: #f5f5f7; border-radius: 10px; padding: 20px;">
                                            <p style="margin: 0; color: #86868b; font-size: 12px; text-transform: uppercase;">Routine</p>
                                            <p style="margin: 8px 0 0 0; color: #1a1a2e; font-size: 28px; font-weight: 600;">{routine_score if routine_score else '--'}</p>
                                        </div>
                                    </td>
                                    <td width="33%" style="text-align: center; padding: 10px;">
                                        <div style="background-color: #f5f5f7; border-radius: 10px; padding: 20px;">
                                            <p style="margin: 0; color: #86868b; font-size: 12px; text-transform: uppercase;">HRV</p>
                                            <p style="margin: 8px 0 0 0; color: #1a1a2e; font-size: 28px; font-weight: 600;">{hrv if hrv else '--'}</p>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Biometrics -->
                    <tr>
                        <td style="padding: 25px 30px; border-bottom: 1px solid #e5e5e7;">
                            <h3 style="margin: 0 0 20px 0; color: #1a1a2e; font-size: 18px; font-weight: 600;">Biometrics</h3>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td width="50%" style="padding: 10px 10px 10px 0;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #fef2f2; border-radius: 10px; padding: 15px;">
                                            <tr>
                                                <td style="padding: 15px;">
                                                    <p style="margin: 0; color: #991b1b; font-size: 12px; text-transform: uppercase;">Avg Heart Rate</p>
                                                    <p style="margin: 8px 0 0 0; color: #7f1d1d; font-size: 24px; font-weight: 600;">
                                                        {heart_rate if heart_rate else '--'} <span style="font-size: 14px; font-weight: 400;">bpm</span>
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td width="50%" style="padding: 10px 0 10px 10px;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #ecfdf5; border-radius: 10px; padding: 15px;">
                                            <tr>
                                                <td style="padding: 15px;">
                                                    <p style="margin: 0; color: #166534; font-size: 12px; text-transform: uppercase;">Breath Rate</p>
                                                    <p style="margin: 8px 0 0 0; color: #14532d; font-size: 24px; font-weight: 600;">
                                                        {breath_rate if breath_rate else '--'} <span style="font-size: 14px; font-weight: 400;">/min</span>
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Temperature -->
                    <tr>
                        <td style="padding: 25px 30px; border-bottom: 1px solid #e5e5e7;">
                            <h3 style="margin: 0 0 20px 0; color: #1a1a2e; font-size: 18px; font-weight: 600;">Temperature</h3>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td width="50%" style="padding: 10px 10px 10px 0;">
                                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; padding: 20px;">
                                            <p style="margin: 0; color: rgba(255,255,255,0.8); font-size: 12px; text-transform: uppercase;">Bed Temp</p>
                                            <p style="margin: 8px 0 0 0; color: white; font-size: 24px; font-weight: 600;">
                                                {self._format_temp(bed_temp)}
                                            </p>
                                        </div>
                                    </td>
                                    <td width="50%" style="padding: 10px 0 10px 10px;">
                                        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 10px; padding: 20px;">
                                            <p style="margin: 0; color: rgba(255,255,255,0.8); font-size: 12px; text-transform: uppercase;">Room Temp</p>
                                            <p style="margin: 8px 0 0 0; color: white; font-size: 24px; font-weight: 600;">
                                                {self._format_temp(room_temp)}
                                            </p>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Insights -->
                    {self._generate_insights_section(sleep_data, device_data)}

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 25px 30px; text-align: center; background-color: #f5f5f7; border-radius: 0 0 12px 12px;">
                            <p style="margin: 0; color: #86868b; font-size: 12px;">
                                Powered by Eight Sleep + AWS Lambda
                            </p>
                            <p style="margin: 8px 0 0 0; color: #a0a0a0; font-size: 11px;">
                                Report generated at {datetime.now().strftime('%I:%M %p %Z')}
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''

        return html

    def _format_duration(self, seconds: Optional[int]) -> str:
        """Format duration in seconds to human readable string."""
        if seconds is None:
            return '--'

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def _format_temp(self, temp: Optional[float]) -> str:
        """Format temperature value."""
        if temp is None:
            return '--'

        # If temp is in Celsius, convert to Fahrenheit
        if -50 <= temp <= 50:  # Likely Celsius
            fahrenheit = (temp * 9/5) + 32
            return f"{fahrenheit:.0f}F"

        # Already Fahrenheit or raw value
        return f"{temp:.0f}"

    def _get_score_color(self, score: Optional[int]) -> str:
        """Get color based on sleep score."""
        if score is None:
            return '#86868b'

        if score >= 85:
            return '#22c55e'  # Green
        elif score >= 70:
            return '#3b82f6'  # Blue
        elif score >= 55:
            return '#f59e0b'  # Amber
        else:
            return '#ef4444'  # Red

    def _get_quality_color(self, quality: str) -> str:
        """Get color based on quality assessment."""
        colors = {
            'Excellent': '#22c55e',
            'Good': '#3b82f6',
            'Fair': '#f59e0b',
            'Needs Improvement': '#ef4444',
            'Unknown': '#86868b'
        }
        return colors.get(quality, '#86868b')

    def _generate_insights_section(
        self,
        sleep_data: Dict[str, Any],
        device_data: Dict[str, Any]
    ) -> str:
        """Generate insights section based on sleep data."""
        insights = []

        # Sleep score insight
        score = sleep_data.get('sleep_score')
        if score is not None:
            if score >= 85:
                insights.append(("Great night!", "Your sleep quality was excellent. Keep it up!"))
            elif score >= 70:
                insights.append(("Good sleep", "You had a solid night's rest."))
            elif score >= 55:
                insights.append(("Room for improvement", "Try going to bed earlier tonight."))
            else:
                insights.append(("Poor sleep", "Consider adjusting your sleep environment or routine."))

        # HRV insight
        hrv = sleep_data.get('hrv')
        if hrv is not None:
            if hrv >= 50:
                insights.append(("Strong recovery", f"Your HRV of {hrv} indicates good recovery."))
            elif hrv < 30:
                insights.append(("Recovery needed", "Your HRV suggests you may need more rest today."))

        # Time slept insight
        time_slept = sleep_data.get('time_slept')
        if time_slept is not None:
            hours = time_slept / 3600
            if hours >= 7:
                insights.append(("Adequate sleep", f"You got {hours:.1f} hours of sleep."))
            else:
                insights.append(("Sleep deficit", f"Only {hours:.1f} hours. Try to get 7-9 hours tonight."))

        if not insights:
            return ''

        insights_html = ''
        for title, text in insights[:3]:  # Limit to 3 insights
            insights_html += f'''
                <tr>
                    <td style="padding: 10px 0;">
                        <p style="margin: 0; color: #1a1a2e; font-size: 14px; font-weight: 600;">{title}</p>
                        <p style="margin: 4px 0 0 0; color: #86868b; font-size: 13px;">{text}</p>
                    </td>
                </tr>'''

        return f'''
                    <tr>
                        <td style="padding: 25px 30px; border-bottom: 1px solid #e5e5e7;">
                            <h3 style="margin: 0 0 15px 0; color: #1a1a2e; font-size: 18px; font-weight: 600;">Insights</h3>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                                {insights_html}
                            </table>
                        </td>
                    </tr>'''

    def generate_text_report(self, data: Dict[str, Any]) -> str:
        """
        Generate plain text version of sleep report.

        Args:
            data: Sleep data dictionary

        Returns:
            Plain text report string
        """
        sleep_data = data.get('sleep_data', {})
        device_data = data.get('device_data', {})
        quality = data.get('quality_assessment', 'Unknown')

        lines = [
            "=" * 50,
            f"DAILY SLEEP REPORT - {datetime.now().strftime('%A, %B %d, %Y')}",
            "=" * 50,
            "",
            f"Sleep Score: {sleep_data.get('sleep_score', '--')} ({quality})",
            f"Time Asleep: {self._format_duration(sleep_data.get('time_slept'))}",
            "",
            "QUALITY BREAKDOWN",
            "-" * 30,
            f"  Fitness Score:  {sleep_data.get('sleep_fitness_score', '--')}",
            f"  Routine Score:  {sleep_data.get('sleep_routine_score', '--')}",
            "",
            "BIOMETRICS",
            "-" * 30,
            f"  Heart Rate:     {sleep_data.get('heart_rate', '--')} bpm",
            f"  HRV:            {sleep_data.get('hrv', '--')}",
            f"  Breath Rate:    {sleep_data.get('breath_rate', '--')} /min",
            "",
            "TEMPERATURE",
            "-" * 30,
            f"  Bed Temp:       {self._format_temp(sleep_data.get('bed_temp'))}",
            f"  Room Temp:      {self._format_temp(device_data.get('room_temp'))}",
            "",
            "=" * 50,
            f"Report generated at {datetime.now().strftime('%I:%M %p')}",
            "Powered by Eight Sleep + AWS Lambda",
        ]

        return "\n".join(lines)

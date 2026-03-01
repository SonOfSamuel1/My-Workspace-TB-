#!/usr/bin/env python3
"""
Meal Report Generator

Generates HTML emails with Factor 75 meal options for user selection.
Supports responsive design for mobile viewing and clear reply instructions.
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import pytz
from factor75_scraper import MealOption
from jinja2 import BaseLoader, Environment, FileSystemLoader

logger = logging.getLogger(__name__)


# Inline HTML template (fallback if file template not found)
INLINE_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Factor 75 Meal Selection</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #2d5a27 0%, #4a7c43 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 25px;
            text-align: center;
        }
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 28px;
        }
        .deadline-box {
            background-color: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 25px;
            text-align: center;
        }
        .deadline-box .deadline-label {
            font-weight: bold;
            color: #856404;
            font-size: 14px;
            text-transform: uppercase;
        }
        .deadline-box .deadline-time {
            font-size: 24px;
            font-weight: bold;
            color: #d63384;
            margin: 5px 0;
        }
        .selection-count {
            background-color: #e7f3ff;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 25px;
            text-align: center;
            font-size: 18px;
        }
        .selection-count strong {
            color: #0066cc;
            font-size: 24px;
        }
        .meals-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .meal-card {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .meal-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        }
        .meal-number {
            background-color: #2d5a27;
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 18px;
            position: absolute;
            top: 10px;
            left: 10px;
            z-index: 1;
        }
        .meal-image-container {
            position: relative;
            height: 180px;
            overflow: hidden;
            background-color: #f0f0f0;
        }
        .meal-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .meal-content {
            padding: 15px;
        }
        .meal-name {
            font-size: 18px;
            font-weight: bold;
            color: #2d5a27;
            margin: 0 0 8px 0;
        }
        .meal-description {
            font-size: 14px;
            color: #666;
            margin: 0 0 12px 0;
            line-height: 1.4;
        }
        .meal-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 12px;
        }
        .meal-tag {
            background-color: #e8f5e9;
            color: #2d5a27;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 11px;
            font-weight: 500;
        }
        .meal-nutrition {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            padding-top: 12px;
            border-top: 1px solid #eee;
        }
        .nutrition-item {
            text-align: center;
        }
        .nutrition-value {
            font-weight: bold;
            font-size: 16px;
            color: #333;
        }
        .nutrition-label {
            font-size: 10px;
            color: #888;
            text-transform: uppercase;
        }
        .instructions-box {
            background-color: #f8f9fa;
            border: 2px solid #dee2e6;
            border-radius: 12px;
            padding: 25px;
            margin: 30px 0;
        }
        .instructions-box h2 {
            margin-top: 0;
            color: #2d5a27;
        }
        .instructions-box code {
            background-color: #e9ecef;
            padding: 3px 8px;
            border-radius: 4px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 16px;
        }
        .instructions-box .example {
            background-color: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin: 15px 0;
            border-radius: 0 8px 8px 0;
        }
        .footer {
            text-align: center;
            padding: 20px;
            color: #888;
            font-size: 12px;
        }

        /* Mobile responsive */
        @media (max-width: 600px) {
            body {
                padding: 10px;
            }
            .header {
                padding: 20px;
            }
            .header h1 {
                font-size: 22px;
            }
            .meals-grid {
                grid-template-columns: 1fr;
            }
            .meal-nutrition {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🍽️ Factor 75 Meal Selection</h1>
        <p>Week of {{ week_of or 'This Week' }}</p>
    </div>

    {% if deadline %}
    <div class="deadline-box">
        <div class="deadline-label">Selection Deadline</div>
        <div class="deadline-time">{{ deadline_formatted }}</div>
        <div>{{ time_remaining }}</div>
    </div>
    {% endif %}

    <div class="selection-count">
        Please select <strong>{{ meal_count }}</strong> meals for this week
    </div>

    <div class="meals-grid">
        {% for meal in meals %}
        <div class="meal-card">
            <div class="meal-image-container">
                <div class="meal-number">{{ loop.index }}</div>
                {% if meal.image_url %}
                <img src="{{ meal.image_url }}" alt="{{ meal.name }}" class="meal-image" />
                {% else %}
                <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #999;">
                    No image available
                </div>
                {% endif %}
            </div>
            <div class="meal-content">
                <h3 class="meal-name">{{ meal.name }}</h3>
                <p class="meal-description">{{ meal.description }}</p>
                {% if meal.tags %}
                <div class="meal-tags">
                    {% for tag in meal.tags %}
                    <span class="meal-tag">{{ tag }}</span>
                    {% endfor %}
                </div>
                {% endif %}
                <div class="meal-nutrition">
                    <div class="nutrition-item">
                        <div class="nutrition-value">{{ meal.calories }}</div>
                        <div class="nutrition-label">Cal</div>
                    </div>
                    <div class="nutrition-item">
                        <div class="nutrition-value">{{ meal.protein }}g</div>
                        <div class="nutrition-label">Protein</div>
                    </div>
                    <div class="nutrition-item">
                        <div class="nutrition-value">{{ meal.carbs }}g</div>
                        <div class="nutrition-label">Carbs</div>
                    </div>
                    <div class="nutrition-item">
                        <div class="nutrition-value">{{ meal.fat }}g</div>
                        <div class="nutrition-label">Fat</div>
                    </div>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>

    <div class="instructions-box">
        <h2>📧 How to Select Your Meals</h2>
        <p>Simply <strong>reply to this email</strong> with the meal numbers you want.</p>

        <div class="example">
            <strong>Example reply for {{ meal_count }} meals:</strong><br>
            <code>{{ example_selection }}</code>
        </div>

        <p><strong>Want duplicates?</strong> Just repeat the number:</p>
        <div class="example">
            <code>{{ example_with_duplicates }}</code><br>
            <small>(This selects meal #1 twice and meal #3 twice)</small>
        </div>

        <p style="margin-top: 20px; padding: 10px; background-color: #fff3cd; border-radius: 8px;">
            <strong>⚡ Quick tip:</strong> Make sure your total equals <strong>{{ meal_count }}</strong> meals!
        </p>
    </div>

    <div class="footer">
        <p>This email was automatically generated by Factor 75 Meal Selector.</p>
        <p>{{ generated_at }}</p>
    </div>
</body>
</html>
"""


class MealReportGenerator:
    """
    Generates HTML email reports for Factor 75 meal selection.
    """

    def __init__(
        self, config: Optional[Dict] = None, template_dir: Optional[str] = None
    ):
        """
        Initialize the report generator.

        Args:
            config: Configuration dictionary
            template_dir: Directory containing Jinja2 templates
        """
        self.config = config or {}
        self.meal_count = self.config.get("factor75", {}).get("meal_count", 10)
        self.timezone = pytz.timezone("America/New_York")

        # Set up Jinja2 environment
        if template_dir and os.path.exists(template_dir):
            self.jinja_env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=True,
            )
        else:
            # Use inline template
            self.jinja_env = Environment(
                loader=BaseLoader(),
                autoescape=True,
            )

    def generate_selection_email(
        self,
        meals: List[MealOption],
        deadline: Optional[datetime] = None,
        week_of: Optional[str] = None,
    ) -> str:
        """
        Generate HTML email with meal options.

        Args:
            meals: List of available meals
            deadline: Selection deadline datetime
            week_of: Week of string (e.g., "December 16")

        Returns:
            HTML string
        """
        now = datetime.now(self.timezone)

        # Format deadline
        deadline_formatted = ""
        time_remaining = ""
        if deadline:
            if deadline.tzinfo is None:
                deadline = self.timezone.localize(deadline)
            deadline_formatted = deadline.strftime("%A, %B %d at %I:%M %p %Z")
            delta = deadline - now
            if delta.total_seconds() > 0:
                days = delta.days
                hours = delta.seconds // 3600
                if days > 0:
                    time_remaining = f"{days} day{'s' if days != 1 else ''}, {hours} hour{'s' if hours != 1 else ''} remaining"
                else:
                    time_remaining = (
                        f"{hours} hour{'s' if hours != 1 else ''} remaining"
                    )
            else:
                time_remaining = "Deadline passed!"

        # Generate example selections
        example_numbers = list(range(1, min(len(meals) + 1, self.meal_count + 1)))
        if len(example_numbers) < self.meal_count:
            # Pad with duplicates if not enough meals
            while len(example_numbers) < self.meal_count:
                example_numbers.append(
                    example_numbers[len(example_numbers) % len(meals)]
                )
        example_selection = ", ".join(
            str(n) for n in example_numbers[: self.meal_count]
        )

        # Example with duplicates
        dup_numbers = [1, 1, 3, 3]
        remaining = self.meal_count - 4
        dup_numbers.extend(range(5, 5 + remaining))
        example_with_duplicates = ", ".join(
            str(n) for n in dup_numbers[: self.meal_count]
        )

        # Template context
        context = {
            "meals": meals,
            "meal_count": self.meal_count,
            "deadline": deadline,
            "deadline_formatted": deadline_formatted,
            "time_remaining": time_remaining,
            "week_of": week_of,
            "example_selection": example_selection,
            "example_with_duplicates": example_with_duplicates,
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        }

        # Try file template first, fall back to inline
        try:
            template = self.jinja_env.get_template("meal_selection_email.html")
        except Exception:
            template = self.jinja_env.from_string(INLINE_EMAIL_TEMPLATE)

        return template.render(**context)

    def generate_confirmation_email(
        self,
        selected_meals: List[MealOption],
        week_of: Optional[str] = None,
    ) -> str:
        """
        Generate confirmation email after selections are submitted.

        Args:
            selected_meals: List of meals that were selected
            week_of: Week of string

        Returns:
            HTML string
        """
        now = datetime.now(self.timezone)

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Factor 75 Selection Confirmed</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 25px;
        }}
        .header h1 {{ margin: 0; }}
        .success-icon {{ font-size: 48px; margin-bottom: 10px; }}
        .meal-list {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .meal-item {{
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}
        .meal-item:last-child {{ border-bottom: none; }}
        .meal-name {{ font-weight: bold; color: #2d5a27; }}
        .meal-nutrition {{ color: #888; font-size: 14px; }}
        .footer {{
            text-align: center;
            color: #888;
            font-size: 12px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="success-icon">✅</div>
        <h1>Meals Selected!</h1>
        <p>Week of {week_of or 'This Week'}</p>
    </div>

    <div class="meal-list">
        <h2>Your {len(selected_meals)} Meals:</h2>
"""

        for i, meal in enumerate(selected_meals, 1):
            html += f"""
        <div class="meal-item">
            <div class="meal-name">{i}. {meal.name}</div>
            <div class="meal-nutrition">{meal.calories} cal | {meal.protein}g protein | {meal.carbs}g carbs | {meal.fat}g fat</div>  # noqa: E501
        </div>
"""

        html += f"""
    </div>

    <div class="footer">
        <p>Your selections have been submitted to Factor 75.</p>
        <p>Confirmed at {now.strftime("%Y-%m-%d %H:%M:%S %Z")}</p>
    </div>
</body>
</html>
"""
        return html

    def generate_reminder_email(
        self,
        deadline: datetime,
        hours_remaining: int,
        week_of: Optional[str] = None,
    ) -> str:
        """
        Generate reminder email when deadline is approaching.

        Args:
            deadline: Selection deadline
            hours_remaining: Hours until deadline
            week_of: Week of string

        Returns:
            HTML string
        """
        deadline_str = deadline.strftime("%A, %B %d at %I:%M %p %Z")

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Factor 75 Selection Reminder</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 25px;
        }}
        .header h1 {{ margin: 0; }}
        .warning-icon {{ font-size: 48px; margin-bottom: 10px; }}
        .content {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            text-align: center;
        }}
        .deadline {{
            font-size: 24px;
            font-weight: bold;
            color: #dc3545;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            color: #888;
            font-size: 12px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="warning-icon">⏰</div>
        <h1>Meal Selection Reminder</h1>
        <p>Week of {week_of or 'This Week'}</p>
    </div>

    <div class="content">
        <p>You haven't selected your meals yet!</p>
        <div class="deadline">
            Only {hours_remaining} hour{'s' if hours_remaining != 1 else ''} remaining
        </div>
        <p>Deadline: <strong>{deadline_str}</strong></p>
        <p>Reply to the original meal selection email with your choices.</p>
    </div>

    <div class="footer">
        <p>Factor 75 Meal Selector Reminder</p>
    </div>
</body>
</html>
"""
        return html

    def generate_error_email(
        self,
        error_message: str,
        suggestions: Optional[List[str]] = None,
    ) -> str:
        """
        Generate error notification email.

        Args:
            error_message: Description of the error
            suggestions: List of suggested actions

        Returns:
            HTML string
        """
        suggestions = suggestions or []

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Factor 75 Selection Error</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 25px;
        }}
        .content {{
            background: white;
            border-radius: 12px;
            padding: 25px;
        }}
        .error-box {{
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .suggestions {{
            background-color: #e7f3ff;
            border-radius: 8px;
            padding: 15px;
        }}
        .suggestions ul {{ margin: 10px 0 0 0; padding-left: 20px; }}
        .footer {{
            text-align: center;
            color: #888;
            font-size: 12px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>❌ Selection Error</h1>
    </div>

    <div class="content">
        <div class="error-box">
            <strong>Error:</strong> {error_message}
        </div>
"""

        if suggestions:
            html += """
        <div class="suggestions">
            <strong>Suggestions:</strong>
            <ul>
"""
            for suggestion in suggestions:
                html += f"                <li>{suggestion}</li>\n"
            html += """
            </ul>
        </div>
"""

        html += """
    </div>

    <div class="footer">
        <p>Factor 75 Meal Selector</p>
    </div>
</body>
</html>
"""
        return html

    def get_subject_line(self, week_of: Optional[str] = None) -> str:
        """
        Generate email subject line.

        Args:
            week_of: Week of string

        Returns:
            Subject line string
        """
        template = self.config.get("email", {}).get(
            "subject_template", "Factor 75 Meal Selection - Week of {date}"
        )
        date_str = week_of or datetime.now(self.timezone).strftime("%B %d")
        return template.format(date=date_str)

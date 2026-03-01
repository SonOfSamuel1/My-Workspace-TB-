#!/usr/bin/env python3
"""
Selection Submitter

Submits meal selections to Factor 75 website using Playwright MCP.
This module provides the interface and logic for submission,
with actual browser automation performed via Playwright MCP.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from factor75_scraper import MealOption

logger = logging.getLogger(__name__)


@dataclass
class SubmissionResult:
    """Result of submitting meal selections."""

    success: bool
    meals_submitted: List[str]  # List of meal names submitted
    confirmation_number: Optional[str] = None
    submitted_at: Optional[datetime] = None
    error_message: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class SelectionSubmitter:
    """
    Submits meal selections to Factor 75.

    This class defines the submission interface and provides instructions
    for Playwright MCP to perform the actual browser automation.
    """

    MENU_URL = "https://www.factor75.com/menu"

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the submitter.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.timeout = self.config.get("scraping", {}).get("timeout_ms", 30000)

    def get_submission_instructions(
        self,
        meal_numbers: List[int],
        quantities: Dict[int, int],
    ) -> Dict:
        """
        Get instructions for Playwright MCP to submit selections.

        Args:
            meal_numbers: List of meal numbers to select (1-indexed)
            quantities: Map of meal number to quantity

        Returns:
            Dictionary with step-by-step Playwright instructions
        """
        steps = [
            {
                "action": "navigate",
                "url": self.MENU_URL,
                "description": "Navigate to Factor 75 menu page",
            },
            {
                "action": "wait",
                "timeout": 3000,
                "description": "Wait for menu to load",
            },
        ]

        # Add step to clear existing selections if any
        steps.append(
            {
                "action": "evaluate",
                "script": """
                // Look for and click "Clear All" or similar button if exists
                const clearBtn = document.querySelector('[data-testid="clear-selections"], .clear-all, button:contains("Clear")');  # noqa: E501
                if (clearBtn) clearBtn.click();
            """,
                "description": "Clear any existing selections",
            }
        )

        # Add steps to select each meal
        for meal_num, qty in quantities.items():
            for _ in range(qty):
                steps.append(
                    {
                        "action": "click_meal",
                        "meal_number": meal_num,
                        "description": f"Select meal #{meal_num}",
                        "selector_hints": [
                            f".meal-card:nth-child({meal_num})",
                            f"[data-meal-index='{meal_num - 1}']",
                            f"[data-meal-number='{meal_num}']",
                        ],
                    }
                )

        # Add confirmation step
        steps.append(
            {
                "action": "click",
                "selector": 'button[type="submit"], button:has-text("Confirm"), button:has-text("Save"), button:has-text("Submit"), .confirm-selections',  # noqa: E501
                "description": "Confirm meal selections",
            }
        )

        # Verify success
        steps.append(
            {
                "action": "wait_for",
                "selector": '.success-message, .confirmation, [data-testid="selection-confirmed"]',
                "timeout": 10000,
                "description": "Wait for confirmation message",
            }
        )

        return {
            "steps": steps,
            "total_meals": sum(quantities.values()),
            "meal_numbers": meal_numbers,
        }

    def get_click_meal_instruction(self, meal_number: int) -> Dict:
        """
        Get specific instruction to click a meal card.

        This generates detailed instructions for clicking a specific meal,
        with multiple selector fallbacks.

        Args:
            meal_number: 1-indexed meal number

        Returns:
            Instruction dictionary for Playwright
        """
        return {
            "action": "click_meal",
            "description": f"Click to select meal #{meal_number}",
            "strategies": [
                {
                    "method": "nth_child",
                    "selector": f".meal-card:nth-child({meal_number}) .add-button, .meal-card:nth-child({meal_number}) button",
                    "description": "Select via nth-child",
                },
                {
                    "method": "data_attribute",
                    "selector": f"[data-meal-index='{meal_number - 1}'] button, [data-meal-number='{meal_number}'] button",
                    "description": "Select via data attribute",
                },
                {
                    "method": "text_content",
                    "instruction": f"Find the {meal_number}th meal card and click its add/select button",
                    "description": "Use AI to find and click",
                },
            ],
        }

    def parse_submission_result(self, html_content: str) -> SubmissionResult:
        """
        Parse the submission result from page HTML.

        Args:
            html_content: HTML after submission attempt

        Returns:
            SubmissionResult
        """
        import re

        success_indicators = [
            r"(?:selection|selections?)\s+(?:saved|confirmed|submitted)",
            r"thank\s+you",
            r"your\s+meals?\s+(?:have\s+been|are)\s+(?:selected|saved)",
            r"order\s+confirmed",
        ]

        error_indicators = [
            r"error",
            r"failed",
            r"unable\s+to",
            r"please\s+try\s+again",
            r"something\s+went\s+wrong",
        ]

        html_lower = html_content.lower()

        # Check for success
        for pattern in success_indicators:
            if re.search(pattern, html_lower):
                # Try to extract confirmation number
                conf_match = re.search(
                    r"(?:confirmation|order)\s*(?:#|number|:)\s*([A-Z0-9-]+)",
                    html_content,
                    re.IGNORECASE,
                )
                conf_number = conf_match.group(1) if conf_match else None

                return SubmissionResult(
                    success=True,
                    meals_submitted=[],  # Would need to parse from page
                    confirmation_number=conf_number,
                    submitted_at=datetime.now(),
                )

        # Check for errors
        for pattern in error_indicators:
            if re.search(pattern, html_lower):
                # Try to extract error message
                error_match = re.search(
                    r"(?:error|failed)[:\s]*([^<]+)",
                    html_content,
                    re.IGNORECASE,
                )
                error_msg = (
                    error_match.group(1).strip()
                    if error_match
                    else "Unknown error occurred"
                )

                return SubmissionResult(
                    success=False,
                    meals_submitted=[],
                    error_message=error_msg,
                )

        # Uncertain result
        return SubmissionResult(
            success=False,
            meals_submitted=[],
            error_message="Could not determine submission result from page",
            warnings=["The page content did not clearly indicate success or failure"],
        )

    def verify_selections(
        self,
        html_content: str,
        expected_meals: List[MealOption],
    ) -> Dict:
        """
        Verify that the correct meals are selected on the page.

        Args:
            html_content: Current page HTML
            expected_meals: Meals that should be selected

        Returns:
            Verification result dictionary
        """
        import re

        selected_on_page = []
        missing = []
        unexpected = []

        # Look for selected meal indicators in HTML
        selected_patterns = [
            r'class="[^"]*selected[^"]*"[^>]*>([^<]+)',
            r'data-selected="true"[^>]*>([^<]+)',
            r"<div[^>]*checked[^>]*>([^<]+)",
        ]

        page_selected_names = set()
        for pattern in selected_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            page_selected_names.update(m.strip().lower() for m in matches)

        expected_names = {m.name.lower() for m in expected_meals}

        # Check what's matching
        for meal in expected_meals:
            meal_lower = meal.name.lower()
            if any(
                meal_lower in selected or selected in meal_lower
                for selected in page_selected_names
            ):
                selected_on_page.append(meal.name)
            else:
                missing.append(meal.name)

        # Check for unexpected selections
        for selected in page_selected_names:
            if not any(selected in exp or exp in selected for exp in expected_names):
                unexpected.append(selected)

        return {
            "all_correct": len(missing) == 0 and len(unexpected) == 0,
            "selected_count": len(selected_on_page),
            "expected_count": len(expected_meals),
            "selected_on_page": selected_on_page,
            "missing": missing,
            "unexpected": unexpected,
        }


def create_submission_summary(
    result: SubmissionResult,
    selected_meals: List[MealOption],
) -> str:
    """
    Create a human-readable summary of the submission.

    Args:
        result: SubmissionResult from submission
        selected_meals: List of meals that were selected

    Returns:
        Formatted summary string
    """
    lines = []

    if result.success:
        lines.append("Meal Selection Successful!")
        lines.append("")
        lines.append(f"Submitted at: {result.submitted_at}")
        if result.confirmation_number:
            lines.append(f"Confirmation #: {result.confirmation_number}")
        lines.append("")
        lines.append(f"Meals selected ({len(selected_meals)}):")
        for i, meal in enumerate(selected_meals, 1):
            lines.append(f"  {i}. {meal.name}")
    else:
        lines.append("Meal Selection Failed")
        lines.append("")
        lines.append(f"Error: {result.error_message}")
        if result.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in result.warnings:
                lines.append(f"  - {warning}")

    return "\n".join(lines)

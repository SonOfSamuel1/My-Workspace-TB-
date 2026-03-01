#!/usr/bin/env python3
"""
Reply Parser

Parses email replies to extract meal selections.
Supports various input formats and validates selection count.
"""

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from factor75_scraper import MealOption

logger = logging.getLogger(__name__)


@dataclass
class SelectionResult:
    """Result of parsing a reply email."""

    meal_numbers: List[int]  # List of selected meal numbers (1-indexed)
    quantities: Dict[int, int]  # Map of meal number to quantity
    total_count: int  # Total meals selected (sum of quantities)
    is_valid: bool
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    raw_input: str = ""

    def get_meal_ids(self, meals: List[MealOption]) -> List[str]:
        """
        Convert meal numbers to meal IDs.

        Args:
            meals: List of MealOption objects (in order as presented)

        Returns:
            List of meal_id strings for selected meals
        """
        meal_ids = []
        for num, qty in self.quantities.items():
            if 1 <= num <= len(meals):
                meal_id = meals[num - 1].meal_id
                meal_ids.extend([meal_id] * qty)
        return meal_ids

    def get_selected_meals(self, meals: List[MealOption]) -> List[MealOption]:
        """
        Get the actual MealOption objects for selections.

        Args:
            meals: List of MealOption objects (in order as presented)

        Returns:
            List of selected MealOption objects (with duplicates)
        """
        selected = []
        for num, qty in self.quantities.items():
            if 1 <= num <= len(meals):
                selected.extend([meals[num - 1]] * qty)
        return selected


class ReplyParser:
    """
    Parses email replies to extract meal selections.

    Supports formats:
    - Comma-separated numbers: "1, 3, 5, 7, 9, 11, 13, 15, 17, 19"
    - Space-separated: "1 3 5 7 9 11 13 15 17 19"
    - Newline-separated: "1\n3\n5\n..."
    - With quantities: "1 x2, 3, 5 x2, 7, 9" or "1 (2), 3, 5 (2), 7, 9"
    - Meal names (fuzzy matched)
    """

    def __init__(self, expected_count: int = 10):
        """
        Initialize the parser.

        Args:
            expected_count: Expected number of meals to select
        """
        self.expected_count = expected_count

    def parse(
        self,
        reply_text: str,
        available_meals: Optional[List[MealOption]] = None,
    ) -> SelectionResult:
        """
        Parse reply text to extract meal selections.

        Args:
            reply_text: Raw text from email reply
            available_meals: Optional list of available meals for name matching

        Returns:
            SelectionResult with parsed selections and validation
        """
        # Clean up the input
        cleaned = self._clean_reply_text(reply_text)

        if not cleaned:
            return SelectionResult(
                meal_numbers=[],
                quantities={},
                total_count=0,
                is_valid=False,
                validation_errors=["Empty or unreadable reply"],
                raw_input=reply_text,
            )

        # Try different parsing strategies
        result = self._parse_numbers_with_quantities(cleaned)

        # If that didn't work well, try simple number extraction
        if not result.meal_numbers:
            result = self._parse_simple_numbers(cleaned)

        # If still no luck and we have meal names, try name matching
        if not result.meal_numbers and available_meals:
            result = self._parse_meal_names(cleaned, available_meals)

        # Validate the result
        result = self._validate_result(result, available_meals)
        result.raw_input = reply_text

        return result

    def _clean_reply_text(self, text: str) -> str:
        """
        Clean and extract relevant content from reply email.

        Args:
            text: Raw email text

        Returns:
            Cleaned text with just the user's reply
        """
        if not text:
            return ""

        # Remove common email reply prefixes/quoted text
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            # Skip quoted lines
            if line.strip().startswith(">"):
                continue
            # Skip "On ... wrote:" lines
            if re.match(r"^On .+ wrote:?$", line.strip()):
                continue
            # Skip signature separators
            if line.strip() in ["--", "---", "___"]:
                break
            # Skip common signature lines
            if re.match(r"^(Sent from|Get Outlook|Sent via)", line.strip()):
                break

            cleaned_lines.append(line)

        cleaned = "\n".join(cleaned_lines).strip()

        # Remove HTML tags if present
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)

        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    def _parse_numbers_with_quantities(self, text: str) -> SelectionResult:
        """
        Parse numbers with optional quantities.

        Formats: "1 x2", "1x2", "1 (2)", "1(2)", "1 *2"

        Args:
            text: Cleaned reply text

        Returns:
            SelectionResult with quantities
        """
        quantities: Dict[int, int] = {}
        meal_numbers: List[int] = []

        # Pattern for number with optional quantity
        # Matches: 1, 1x2, 1 x2, 1(2), 1 (2), 1*2, 1 *2
        pattern = r"(\d+)\s*(?:[x*×]\s*(\d+)|\((\d+)\))?"

        matches = re.findall(pattern, text)

        for match in matches:
            num_str, qty_x, qty_paren = match
            try:
                num = int(num_str)
                qty = 1
                if qty_x:
                    qty = int(qty_x)
                elif qty_paren:
                    qty = int(qty_paren)

                if num > 0:
                    meal_numbers.append(num)
                    quantities[num] = quantities.get(num, 0) + qty

            except ValueError:
                continue

        total_count = sum(quantities.values())

        return SelectionResult(
            meal_numbers=sorted(set(meal_numbers)),
            quantities=quantities,
            total_count=total_count,
            is_valid=False,  # Will be validated later
        )

    def _parse_simple_numbers(self, text: str) -> SelectionResult:
        """
        Simple extraction of all numbers from text.

        Args:
            text: Cleaned reply text

        Returns:
            SelectionResult
        """
        quantities: Dict[int, int] = {}
        meal_numbers: List[int] = []

        # Find all numbers
        numbers = re.findall(r"\d+", text)

        for num_str in numbers:
            try:
                num = int(num_str)
                # Filter out obviously invalid numbers (too large, years, etc.)
                if 1 <= num <= 100:  # Reasonable meal number range
                    meal_numbers.append(num)
                    quantities[num] = quantities.get(num, 0) + 1
            except ValueError:
                continue

        total_count = sum(quantities.values())

        return SelectionResult(
            meal_numbers=sorted(set(meal_numbers)),
            quantities=quantities,
            total_count=total_count,
            is_valid=False,
        )

    def _parse_meal_names(
        self,
        text: str,
        meals: List[MealOption],
    ) -> SelectionResult:
        """
        Parse meal selections by matching meal names.

        Args:
            text: Cleaned reply text
            meals: Available meal options

        Returns:
            SelectionResult
        """
        quantities: Dict[int, int] = {}
        meal_numbers: List[int] = []
        warnings: List[str] = []

        # Split text into potential meal names
        # Try comma, newline, semicolon separators
        potential_names = re.split(r"[,;\n]+", text)

        for name in potential_names:
            name = name.strip()
            if not name or len(name) < 3:
                continue

            # Try to match against meal names
            best_match, score, index = self._fuzzy_match_meal(name, meals)

            if score >= 0.6:  # 60% similarity threshold
                meal_num = index + 1  # Convert to 1-indexed
                meal_numbers.append(meal_num)
                quantities[meal_num] = quantities.get(meal_num, 0) + 1

                if score < 0.9:
                    warnings.append(f'Interpreted "{name}" as "{best_match}"')
            else:
                warnings.append(f'Could not match "{name}" to any meal')

        total_count = sum(quantities.values())

        return SelectionResult(
            meal_numbers=sorted(set(meal_numbers)),
            quantities=quantities,
            total_count=total_count,
            is_valid=False,
            warnings=warnings,
        )

    def _fuzzy_match_meal(
        self,
        text: str,
        meals: List[MealOption],
    ) -> Tuple[str, float, int]:
        """
        Find the best matching meal name.

        Args:
            text: Text to match
            meals: Available meals

        Returns:
            Tuple of (best_match_name, score, index)
        """
        best_match = ""
        best_score = 0.0
        best_index = -1

        text_lower = text.lower()

        for i, meal in enumerate(meals):
            name_lower = meal.name.lower()

            # Check for exact substring match first
            if text_lower in name_lower or name_lower in text_lower:
                score = 0.95
            else:
                # Use sequence matcher for fuzzy matching
                score = SequenceMatcher(None, text_lower, name_lower).ratio()

            if score > best_score:
                best_score = score
                best_match = meal.name
                best_index = i

        return best_match, best_score, best_index

    def _validate_result(
        self,
        result: SelectionResult,
        available_meals: Optional[List[MealOption]] = None,
    ) -> SelectionResult:
        """
        Validate the parsed result.

        Args:
            result: Parsed SelectionResult
            available_meals: Optional list of available meals

        Returns:
            Updated SelectionResult with validation
        """
        errors = list(result.validation_errors)
        warnings = list(result.warnings)

        # Check total count
        if result.total_count == 0:
            errors.append("No meal selections found in your reply")
        elif result.total_count < self.expected_count:
            errors.append(
                f"Not enough meals selected. You selected {result.total_count}, "
                f"but you need {self.expected_count}."
            )
        elif result.total_count > self.expected_count:
            errors.append(
                f"Too many meals selected. You selected {result.total_count}, "
                f"but you can only select {self.expected_count}."
            )

        # Validate meal numbers against available meals
        if available_meals:
            max_num = len(available_meals)
            invalid_nums = [n for n in result.meal_numbers if n > max_num]
            if invalid_nums:
                errors.append(
                    f"Invalid meal numbers: {invalid_nums}. "
                    f"Valid range is 1-{max_num}."
                )

        # Check for meal number 0 or negative
        invalid_zeros = [n for n in result.meal_numbers if n <= 0]
        if invalid_zeros:
            errors.append("Meal numbers must be positive (1 or greater)")

        is_valid = len(errors) == 0

        return SelectionResult(
            meal_numbers=result.meal_numbers,
            quantities=result.quantities,
            total_count=result.total_count,
            is_valid=is_valid,
            validation_errors=errors,
            warnings=warnings,
            raw_input=result.raw_input,
        )

    def format_clarification_message(
        self,
        result: SelectionResult,
        available_meals: Optional[List[MealOption]] = None,
    ) -> str:
        """
        Generate a clarification message when parsing fails.

        Args:
            result: Failed SelectionResult
            available_meals: Optional list of available meals

        Returns:
            Formatted message string
        """
        message_parts = ["There was an issue with your meal selection:\n"]

        for error in result.validation_errors:
            message_parts.append(f"- {error}")

        if result.warnings:
            message_parts.append("\nNotes:")
            for warning in result.warnings:
                message_parts.append(f"- {warning}")

        message_parts.append(
            f"\nPlease reply with exactly {self.expected_count} meal numbers."
        )
        message_parts.append("\nExample: 1, 3, 5, 7, 9, 11, 13, 15, 17, 19")

        if result.total_count > 0:
            message_parts.append(
                f"\nWe understood these selections: {result.meal_numbers}"
            )
            message_parts.append(f"Total count: {result.total_count}")

        return "\n".join(message_parts)

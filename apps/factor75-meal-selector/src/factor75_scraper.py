#!/usr/bin/env python3
"""
Factor 75 Web Scraper

Scrapes meal options from Factor 75 website using Playwright MCP.
This module is designed to be called from Claude Code with Playwright MCP tools.

For standalone/Lambda usage, this provides the interface and data structures,
but actual browser automation is performed by the caller using Playwright MCP.
"""

import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pytz
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


@dataclass
class MealOption:
    """Represents a single meal option from Factor 75."""

    meal_id: str
    name: str
    description: str
    image_url: str
    calories: int
    protein: int
    carbs: int
    fat: int
    tags: List[str]
    category: str
    price: Optional[float] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "MealOption":
        """Create from dictionary."""
        return cls(
            meal_id=data.get("meal_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            image_url=data.get("image_url", ""),
            calories=int(data.get("calories", 0)),
            protein=int(data.get("protein", 0)),
            carbs=int(data.get("carbs", 0)),
            fat=int(data.get("fat", 0)),
            tags=data.get("tags", []),
            category=data.get("category", ""),
            price=data.get("price"),
        )


@dataclass
class ScrapingResult:
    """Result of scraping Factor 75 menu."""

    meals: List[MealOption]
    deadline: Optional[datetime]
    current_selections: List[str]
    week_of: Optional[str]
    success: bool
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "meals": [m.to_dict() for m in self.meals],
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "current_selections": self.current_selections,
            "week_of": self.week_of,
            "success": self.success,
            "error_message": self.error_message,
        }


class Factor75Scraper:
    """
    Factor 75 website scraper using Playwright MCP.

    This class defines the scraping interface and data parsing logic.
    Actual browser automation is performed via Playwright MCP tools
    when called from Claude Code.

    Usage with Claude Code:
    1. Claude uses mcp__playwright__playwright_navigate to navigate
    2. Claude uses mcp__playwright__playwright_fill for form inputs
    3. Claude uses mcp__playwright__playwright_click for interactions
    4. Claude uses mcp__playwright__playwright_get_visible_html to extract content
    5. This class parses the extracted HTML into structured data
    """

    FACTOR75_BASE_URL = "https://www.factor75.com"
    LOGIN_URL = "https://www.factor75.com/login"
    MENU_URL = "https://www.factor75.com/menu"

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the scraper.

        Args:
            config: Configuration dictionary with optional settings
        """
        self.config = config or {}
        self.email = os.getenv("FACTOR75_EMAIL")
        self.password = os.getenv("FACTOR75_PASSWORD")
        self.timeout = self.config.get("scraping", {}).get("timeout_ms", 30000)
        self.timezone = pytz.timezone("America/New_York")

    def get_login_instructions(self) -> Dict:
        """
        Get instructions for Playwright MCP to perform login.

        Returns:
            Dictionary with step-by-step Playwright instructions
        """
        return {
            "steps": [
                {
                    "action": "navigate",
                    "url": self.LOGIN_URL,
                    "description": "Navigate to Factor 75 login page",
                },
                {
                    "action": "fill",
                    "selector": 'input[type="email"], input[name="email"], #email',
                    "value": self.email,
                    "description": "Enter email address",
                },
                {
                    "action": "fill",
                    "selector": 'input[type="password"], input[name="password"], #password',
                    "value": self.password,
                    "description": "Enter password",
                },
                {
                    "action": "click",
                    "selector": 'button[type="submit"], input[type="submit"], button:has-text("Log in"), button:has-text("Sign in")',  # noqa: E501
                    "description": "Click login button",
                },
                {
                    "action": "wait",
                    "timeout": 5000,
                    "description": "Wait for login to complete",
                },
            ]
        }

    def get_menu_scrape_instructions(self) -> Dict:
        """
        Get instructions for Playwright MCP to scrape the menu.

        Returns:
            Dictionary with step-by-step Playwright instructions
        """
        return {
            "steps": [
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
                {
                    "action": "get_html",
                    "description": "Extract page HTML for parsing",
                },
            ]
        }

    def parse_menu_html(self, html_content: str) -> ScrapingResult:
        """
        Parse meal options from Factor 75 menu HTML.

        Args:
            html_content: Raw HTML from the menu page

        Returns:
            ScrapingResult with parsed meals and metadata
        """
        try:
            meals = self._extract_meals_from_html(html_content)
            deadline = self._extract_deadline_from_html(html_content)
            current_selections = self._extract_current_selections(html_content)
            week_of = self._extract_week_of(html_content)

            logger.info(f"Parsed {len(meals)} meals from HTML")

            return ScrapingResult(
                meals=meals,
                deadline=deadline,
                current_selections=current_selections,
                week_of=week_of,
                success=True,
            )

        except Exception as e:
            logger.error(f"Failed to parse menu HTML: {e}")
            return ScrapingResult(
                meals=[],
                deadline=None,
                current_selections=[],
                week_of=None,
                success=False,
                error_message=str(e),
            )

    def _extract_meals_from_html(self, html: str) -> List[MealOption]:
        """
        Extract meal options from HTML content.

        This uses regex patterns to find meal data.
        Factor 75's menu typically renders meal cards with structured data.

        Args:
            html: Raw HTML content

        Returns:
            List of MealOption objects
        """
        meals = []

        # Try to find JSON data embedded in the page (common pattern)
        json_patterns = [
            r"window\.__INITIAL_STATE__\s*=\s*({.*?});",
            r"window\.__NEXT_DATA__\s*=\s*({.*?});",
            r'"meals"\s*:\s*(\[.*?\])',
            r'"menuItems"\s*:\s*(\[.*?\])',
        ]

        for pattern in json_patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    extracted = self._parse_meals_from_json(data)
                    if extracted:
                        return extracted
                except json.JSONDecodeError:
                    continue

        # Fallback: Parse HTML structure directly
        # Look for meal card patterns
        meal_card_pattern = (
            r'<div[^>]*class="[^"]*meal[^"]*card[^"]*"[^>]*>(.*?)</div>\s*</div>'
        )
        card_matches = re.findall(meal_card_pattern, html, re.DOTALL | re.IGNORECASE)

        for i, card_html in enumerate(card_matches):
            meal = self._parse_meal_card_html(card_html, i)
            if meal:
                meals.append(meal)

        return meals

    def _parse_meals_from_json(self, data: Dict) -> List[MealOption]:
        """
        Parse meals from JSON data structure.

        Args:
            data: JSON data that may contain meals

        Returns:
            List of MealOption objects
        """
        meals = []

        # Handle various JSON structures
        meal_list = None

        if isinstance(data, list):
            meal_list = data
        elif isinstance(data, dict):
            # Try common keys
            for key in ["meals", "menuItems", "items", "products", "menu"]:
                if key in data:
                    meal_list = data[key]
                    break

            # Try nested structures
            if not meal_list:
                for key in ["data", "props", "pageProps", "initialState"]:
                    if key in data and isinstance(data[key], dict):
                        return self._parse_meals_from_json(data[key])

        if not meal_list:
            return meals

        for item in meal_list:
            if not isinstance(item, dict):
                continue

            # Extract meal data from various field names
            meal_id = str(
                item.get("id")
                or item.get("mealId")
                or item.get("productId")
                or item.get("sku")
                or ""
            )

            name = item.get("name") or item.get("title") or item.get("mealName") or ""

            description = (
                item.get("description")
                or item.get("shortDescription")
                or item.get("summary")
                or ""
            )

            # Image URL
            image_url = ""
            if "image" in item:
                img = item["image"]
                image_url = img if isinstance(img, str) else img.get("url", "")
            elif "imageUrl" in item:
                image_url = item["imageUrl"]
            elif "images" in item and item["images"]:
                image_url = (
                    item["images"][0]
                    if isinstance(item["images"][0], str)
                    else item["images"][0].get("url", "")
                )

            # Nutrition
            nutrition = (
                item.get("nutrition", {}) or item.get("nutritionFacts", {}) or {}
            )
            calories = int(nutrition.get("calories", 0) or item.get("calories", 0) or 0)
            protein = int(nutrition.get("protein", 0) or item.get("protein", 0) or 0)
            carbs = int(
                nutrition.get("carbs", 0)
                or nutrition.get("carbohydrates", 0)
                or item.get("carbs", 0)
                or 0
            )
            fat = int(nutrition.get("fat", 0) or item.get("fat", 0) or 0)

            # Tags/categories
            tags = (
                item.get("tags", [])
                or item.get("labels", [])
                or item.get("dietaryInfo", [])
                or []
            )
            if isinstance(tags, str):
                tags = [tags]

            category = (
                item.get("category") or item.get("mealType") or item.get("type") or ""
            )

            if name:  # Only add if we have a name
                meals.append(
                    MealOption(
                        meal_id=meal_id,
                        name=name,
                        description=description,
                        image_url=image_url,
                        calories=calories,
                        protein=protein,
                        carbs=carbs,
                        fat=fat,
                        tags=tags,
                        category=category,
                    )
                )

        return meals

    def _parse_meal_card_html(self, card_html: str, index: int) -> Optional[MealOption]:
        """
        Parse a single meal card from HTML.

        Args:
            card_html: HTML content of a meal card
            index: Index for generating ID if not found

        Returns:
            MealOption or None if parsing fails
        """
        # Extract meal name
        name_match = re.search(r"<h[23][^>]*>(.*?)</h[23]>", card_html, re.IGNORECASE)
        name = name_match.group(1).strip() if name_match else ""
        name = re.sub(r"<[^>]+>", "", name)  # Remove any inner HTML

        if not name:
            return None

        # Extract description
        desc_match = re.search(
            r'<p[^>]*class="[^"]*desc[^"]*"[^>]*>(.*?)</p>',
            card_html,
            re.IGNORECASE | re.DOTALL,
        )
        description = desc_match.group(1).strip() if desc_match else ""
        description = re.sub(r"<[^>]+>", "", description)

        # Extract image URL
        img_match = re.search(r'<img[^>]*src="([^"]+)"', card_html, re.IGNORECASE)
        image_url = img_match.group(1) if img_match else ""

        # Extract nutrition (look for calorie patterns)
        cal_match = re.search(
            r"(\d+)\s*(?:cal|kcal|calories)", card_html, re.IGNORECASE
        )
        calories = int(cal_match.group(1)) if cal_match else 0

        protein_match = re.search(
            r"(\d+)\s*g?\s*(?:protein|prot)", card_html, re.IGNORECASE
        )
        protein = int(protein_match.group(1)) if protein_match else 0

        carb_match = re.search(r"(\d+)\s*g?\s*(?:carb|carbs)", card_html, re.IGNORECASE)
        carbs = int(carb_match.group(1)) if carb_match else 0

        fat_match = re.search(r"(\d+)\s*g?\s*(?:fat)", card_html, re.IGNORECASE)
        fat = int(fat_match.group(1)) if fat_match else 0

        # Extract meal ID from data attributes
        id_match = re.search(r'data-(?:meal-)?id="([^"]+)"', card_html, re.IGNORECASE)
        meal_id = id_match.group(1) if id_match else f"meal_{index}"

        # Extract tags
        tags = []
        tag_matches = re.findall(
            r'<span[^>]*class="[^"]*tag[^"]*"[^>]*>([^<]+)</span>',
            card_html,
            re.IGNORECASE,
        )
        tags = [t.strip() for t in tag_matches]

        return MealOption(
            meal_id=meal_id,
            name=name,
            description=description,
            image_url=image_url,
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
            tags=tags,
            category="",
        )

    def _extract_deadline_from_html(self, html: str) -> Optional[datetime]:
        """
        Extract selection deadline from HTML.

        Args:
            html: Raw HTML content

        Returns:
            Datetime of deadline or None
        """
        # Common deadline patterns
        patterns = [
            r"deadline[:\s]*([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?\s*(?:,\s*\d{4})?\s*(?:at\s+\d{1,2}:\d{2}\s*(?:AM|PM)?)?)",
            r"select\s+by[:\s]*([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?\s*(?:,\s*\d{4})?\s*(?:at\s+\d{1,2}:\d{2}\s*(?:AM|PM)?)?)",
            r"order\s+by[:\s]*([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?\s*(?:,\s*\d{4})?\s*(?:at\s+\d{1,2}:\d{2}\s*(?:AM|PM)?)?)",
            r"(\d{1,2}/\d{1,2}/\d{2,4}\s*\d{1,2}:\d{2}\s*(?:AM|PM)?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1).strip()
                    # Remove ordinal suffixes
                    date_str = re.sub(r"(\d)(st|nd|rd|th)", r"\1", date_str)
                    parsed = date_parser.parse(date_str, fuzzy=True)
                    # Ensure it's in the future
                    if parsed < datetime.now():
                        parsed = parsed.replace(year=datetime.now().year + 1)
                    return (
                        self.timezone.localize(parsed)
                        if parsed.tzinfo is None
                        else parsed
                    )
                except (ValueError, TypeError):
                    continue

        return None

    def _extract_current_selections(self, html: str) -> List[str]:
        """
        Extract any currently selected meals.

        Args:
            html: Raw HTML content

        Returns:
            List of selected meal IDs
        """
        selections = []

        # Look for selected/checked meal cards
        selected_patterns = [
            r'data-(?:meal-)?id="([^"]+)"[^>]*(?:selected|checked|active)',
            r'(?:selected|checked|active)[^>]*data-(?:meal-)?id="([^"]+)"',
            r'class="[^"]*selected[^"]*"[^>]*data-(?:meal-)?id="([^"]+)"',
        ]

        for pattern in selected_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            selections.extend(matches)

        return list(set(selections))  # Deduplicate

    def _extract_week_of(self, html: str) -> Optional[str]:
        """
        Extract the "week of" date string.

        Args:
            html: Raw HTML content

        Returns:
            Week of string or None
        """
        patterns = [
            r"week\s+of\s+([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?)",
            r"delivery\s+week[:\s]*([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?)",
            r"menu\s+for\s+([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def validate_login_state(self, html: str) -> Tuple[bool, str]:
        """
        Check if the user is logged in based on page HTML.

        Args:
            html: Raw HTML content

        Returns:
            Tuple of (is_logged_in, message)
        """
        # Signs of being logged in
        logged_in_indicators = [
            r"(?:log\s*out|sign\s*out)",
            r"my\s*account",
            r"welcome[,\s]+\w+",
            r"hello[,\s]+\w+",
        ]

        # Signs of NOT being logged in
        logged_out_indicators = [
            r"(?:log\s*in|sign\s*in)",
            r"create\s*account",
            r"forgot\s*password",
        ]

        for pattern in logged_in_indicators:
            if re.search(pattern, html, re.IGNORECASE):
                return True, "User appears to be logged in"

        for pattern in logged_out_indicators:
            if re.search(pattern, html, re.IGNORECASE):
                return False, "User appears to be logged out"

        return False, "Could not determine login state"


def create_mock_meals_for_testing() -> List[MealOption]:
    """
    Create mock meal data for testing without actual scraping.

    Returns:
        List of sample MealOption objects
    """
    return [
        MealOption(
            meal_id="1",
            name="Grilled Chicken with Roasted Vegetables",
            description="Tender grilled chicken breast served with a medley of roasted seasonal vegetables.",
            image_url="https://factor75.com/images/grilled-chicken.jpg",
            calories=450,
            protein=42,
            carbs=25,
            fat=18,
            tags=["High Protein", "Low Carb", "Gluten Free"],
            category="Chef's Choice",
        ),
        MealOption(
            meal_id="2",
            name="Beef Stir Fry with Brown Rice",
            description="Savory beef strips with crisp vegetables in a tangy sauce, served over brown rice.",
            image_url="https://factor75.com/images/beef-stirfry.jpg",
            calories=520,
            protein=38,
            carbs=45,
            fat=20,
            tags=["High Protein"],
            category="Signature",
        ),
        MealOption(
            meal_id="3",
            name="Salmon with Lemon Dill Sauce",
            description="Fresh Atlantic salmon fillet with a bright lemon dill sauce and asparagus.",
            image_url="https://factor75.com/images/salmon.jpg",
            calories=480,
            protein=35,
            carbs=15,
            fat=28,
            tags=["Keto", "Low Carb", "Gluten Free"],
            category="Premium",
        ),
        MealOption(
            meal_id="4",
            name="Turkey Meatballs with Marinara",
            description="Lean turkey meatballs in house-made marinara sauce with zucchini noodles.",
            image_url="https://factor75.com/images/turkey-meatballs.jpg",
            calories=380,
            protein=32,
            carbs=18,
            fat=16,
            tags=["Low Carb", "Gluten Free"],
            category="Chef's Choice",
        ),
        MealOption(
            meal_id="5",
            name="Pork Tenderloin with Apple Chutney",
            description="Juicy pork tenderloin topped with sweet apple chutney and roasted sweet potato.",
            image_url="https://factor75.com/images/pork-tenderloin.jpg",
            calories=490,
            protein=36,
            carbs=32,
            fat=22,
            tags=["Gluten Free"],
            category="Signature",
        ),
        MealOption(
            meal_id="6",
            name="Shrimp Scampi with Linguine",
            description="Garlic butter shrimp over linguine pasta with fresh herbs.",
            image_url="https://factor75.com/images/shrimp-scampi.jpg",
            calories=540,
            protein=30,
            carbs=48,
            fat=24,
            tags=["High Protein"],
            category="Premium",
        ),
        MealOption(
            meal_id="7",
            name="Chicken Tikka Masala",
            description="Aromatic chicken in creamy tomato curry sauce with basmati rice.",
            image_url="https://factor75.com/images/tikka-masala.jpg",
            calories=510,
            protein=38,
            carbs=42,
            fat=20,
            tags=["Gluten Free"],
            category="Global Flavors",
        ),
        MealOption(
            meal_id="8",
            name="Mediterranean Bowl",
            description="Grilled chicken, falafel, hummus, and fresh vegetables over quinoa.",
            image_url="https://factor75.com/images/mediterranean-bowl.jpg",
            calories=470,
            protein=34,
            carbs=38,
            fat=18,
            tags=["High Protein", "Vegetarian Option"],
            category="Chef's Choice",
        ),
        MealOption(
            meal_id="9",
            name="BBQ Pulled Pork",
            description="Slow-cooked pulled pork in smoky BBQ sauce with coleslaw and cornbread.",
            image_url="https://factor75.com/images/bbq-pork.jpg",
            calories=580,
            protein=40,
            carbs=45,
            fat=26,
            tags=["Gluten Free"],
            category="Comfort",
        ),
        MealOption(
            meal_id="10",
            name="Herb Crusted Cod",
            description="Flaky cod with herb panko crust, served with roasted broccoli and rice pilaf.",
            image_url="https://factor75.com/images/herb-cod.jpg",
            calories=420,
            protein=32,
            carbs=30,
            fat=16,
            tags=["Low Fat", "High Protein"],
            category="Signature",
        ),
        MealOption(
            meal_id="11",
            name="Steak Fajita Bowl",
            description="Sliced steak with peppers, onions, and Mexican rice topped with fresh pico.",
            image_url="https://factor75.com/images/fajita-bowl.jpg",
            calories=550,
            protein=42,
            carbs=40,
            fat=24,
            tags=["High Protein", "Gluten Free"],
            category="Global Flavors",
        ),
        MealOption(
            meal_id="12",
            name="Lemon Herb Chicken Breast",
            description="Simply seasoned chicken breast with lemon herbs, green beans, and mashed potatoes.",
            image_url="https://factor75.com/images/lemon-chicken.jpg",
            calories=440,
            protein=40,
            carbs=28,
            fat=16,
            tags=["High Protein", "Gluten Free"],
            category="Classic",
        ),
    ]

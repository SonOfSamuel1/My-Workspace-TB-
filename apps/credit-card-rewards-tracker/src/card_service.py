"""
Card Service for Credit Card Rewards Tracker

Manages credit card configuration, category multipliers, and best card recommendations.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from data_manager import DataManager

logger = logging.getLogger(__name__)


@dataclass
class CardRecommendation:
    """Recommendation for best card to use."""
    card_id: str
    card_name: str
    multiplier: float
    reward_program: str
    estimated_cpp: float  # cents per point value
    reason: str


@dataclass
class AnnualFeeAlert:
    """Alert for upcoming annual fee."""
    card_id: str
    card_name: str
    annual_fee: int  # in cents
    due_date: str
    days_until: int
    recommendation: str


class CardService:
    """Manages credit card data and provides recommendations."""

    def __init__(self, data_manager: DataManager = None, config: Dict[str, Any] = None):
        """
        Initialize card service.

        Args:
            data_manager: DataManager instance (creates one if not provided)
            config: Configuration dictionary
        """
        self.data_manager = data_manager or DataManager()
        self.config = config or {}
        self.point_valuations = self.config.get("rewards_tracker", {}).get("point_valuations", {})

    def get_all_cards(self) -> List[Dict[str, Any]]:
        """Get all credit cards."""
        return self.data_manager.get_all_cards()

    def get_active_cards(self) -> List[Dict[str, Any]]:
        """Get only active credit cards."""
        cards = self.get_all_cards()
        return [c for c in cards if c.get("is_active", True)]

    def get_card_by_id(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific card by ID."""
        return self.data_manager.get_card_by_id(card_id)

    def add_card(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new credit card.

        Args:
            card_data: Card configuration dictionary

        Returns:
            The added card with generated ID
        """
        # Validate required fields
        required_fields = ["issuer", "name", "reward_type"]
        for field in required_fields:
            if field not in card_data:
                raise ValueError(f"Missing required field: {field}")

        # Set defaults
        card_data.setdefault("is_active", True)
        card_data.setdefault("base_reward_rate", 1.0)
        card_data.setdefault("category_multipliers", [])
        card_data.setdefault("annual_fee", 0)
        card_data.setdefault("last_four", "0000")

        return self.data_manager.add_card(card_data)

    def update_card(self, card_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a card's configuration."""
        return self.data_manager.update_card(card_id, updates)

    def deactivate_card(self, card_id: str) -> bool:
        """Mark a card as inactive (closed/cancelled)."""
        result = self.data_manager.update_card(card_id, {"is_active": False})
        return result is not None

    def get_card_multiplier(self, card: Dict[str, Any], category: str) -> float:
        """
        Get the reward multiplier for a card in a specific category.

        Args:
            card: Card data dictionary
            category: Spending category

        Returns:
            Multiplier for that category (base rate if no special multiplier)
        """
        base_rate = card.get("base_reward_rate", 1.0)
        multipliers = card.get("category_multipliers", [])

        for mult in multipliers:
            if mult.get("category", "").lower() == category.lower():
                # Check if multiplier has expired
                expires = mult.get("expires")
                if expires and expires < datetime.now().strftime("%Y-%m-%d"):
                    continue

                # Check quarterly rotation (simplified - would need actual dates)
                if mult.get("quarterly"):
                    # For now, assume quarterly bonuses are active
                    pass

                # Check annual cap
                cap = mult.get("cap_annual")
                if cap:
                    # Would need to track spend against cap
                    pass

                return mult.get("multiplier", base_rate)

        return base_rate

    def get_best_card_for_category(self, category: str) -> Optional[CardRecommendation]:
        """
        Find the best card to use for a spending category.

        Args:
            category: Spending category (dining, groceries, gas, etc.)

        Returns:
            CardRecommendation with best card info, or None if no cards
        """
        active_cards = self.get_active_cards()
        if not active_cards:
            return None

        programs = self.data_manager.get_reward_programs()
        best_card = None
        best_value = 0.0

        for card in active_cards:
            multiplier = self.get_card_multiplier(card, category)
            program = card.get("reward_program", "cash_back")

            # Get point value (cents per point)
            cpp = self.point_valuations.get(
                program,
                programs.get(program, {}).get("point_value_cents", 1.0)
            )

            # Calculate effective value per dollar spent
            effective_value = multiplier * cpp

            if effective_value > best_value:
                best_value = effective_value
                best_card = card
                best_multiplier = multiplier
                best_cpp = cpp

        if best_card:
            return CardRecommendation(
                card_id=best_card["id"],
                card_name=best_card["name"],
                multiplier=best_multiplier,
                reward_program=best_card.get("reward_program", "cash_back"),
                estimated_cpp=best_cpp,
                reason=f"{best_multiplier}x at {best_cpp}cpp = {best_value:.1f}% effective return"
            )

        return None

    def get_all_category_recommendations(self) -> Dict[str, CardRecommendation]:
        """
        Get best card recommendations for all common categories.

        Returns:
            Dictionary mapping category to recommendation
        """
        categories = [
            "dining", "groceries", "gas", "travel", "streaming",
            "utilities", "online_shopping", "drugstores", "entertainment"
        ]

        recommendations = {}
        for category in categories:
            rec = self.get_best_card_for_category(category)
            if rec:
                recommendations[category] = rec

        return recommendations

    def get_upcoming_annual_fees(self, days: int = 60) -> List[AnnualFeeAlert]:
        """
        Get cards with annual fees coming due soon.

        Args:
            days: Number of days to look ahead

        Returns:
            List of AnnualFeeAlert for upcoming fees
        """
        alerts = []
        active_cards = self.get_active_cards()
        today = datetime.now().date()
        cutoff = today + timedelta(days=days)

        for card in active_cards:
            annual_fee = card.get("annual_fee", 0)
            due_date_str = card.get("annual_fee_due_date")

            if annual_fee > 0 and due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()

                    # Handle case where fee is in next year (annual)
                    if due_date < today:
                        due_date = due_date.replace(year=due_date.year + 1)

                    if today <= due_date <= cutoff:
                        days_until = (due_date - today).days

                        # Generate recommendation
                        if days_until <= 30:
                            rec = f"Call retention line before {due_date_str} for potential offer"
                        else:
                            rec = f"Evaluate card value before fee posts on {due_date_str}"

                        alerts.append(AnnualFeeAlert(
                            card_id=card["id"],
                            card_name=card["name"],
                            annual_fee=annual_fee,
                            due_date=due_date.strftime("%Y-%m-%d"),
                            days_until=days_until,
                            recommendation=rec
                        ))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid fee due date for card {card.get('id')}: {due_date_str}")

        # Sort by days until due
        alerts.sort(key=lambda a: a.days_until)
        return alerts

    def get_cards_by_program(self, program: str) -> List[Dict[str, Any]]:
        """Get all cards earning a specific reward program."""
        cards = self.get_active_cards()
        return [c for c in cards if c.get("reward_program") == program]

    def get_cards_by_issuer(self, issuer: str) -> List[Dict[str, Any]]:
        """Get all cards from a specific issuer."""
        cards = self.get_all_cards()
        return [c for c in cards if c.get("issuer", "").lower() == issuer.lower()]

    def calculate_card_annual_value(self, card_id: str, annual_spend: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Calculate the estimated annual value of a card based on spending.

        Args:
            card_id: Card ID
            annual_spend: Dictionary of category -> annual spend amount

        Returns:
            Dictionary with value breakdown
        """
        card = self.get_card_by_id(card_id)
        if not card:
            return {"error": "Card not found"}

        # Default spending if not provided
        if annual_spend is None:
            annual_spend = {
                "dining": 3000,
                "groceries": 6000,
                "gas": 2400,
                "travel": 2000,
                "other": 12000
            }

        program = card.get("reward_program", "cash_back")
        programs = self.data_manager.get_reward_programs()
        cpp = self.point_valuations.get(
            program,
            programs.get(program, {}).get("point_value_cents", 1.0)
        )

        total_points = 0
        breakdown = {}

        for category, amount in annual_spend.items():
            multiplier = self.get_card_multiplier(card, category)
            points = int(amount * multiplier)
            total_points += points
            breakdown[category] = {
                "spend": amount,
                "multiplier": multiplier,
                "points_earned": points,
                "value_cents": int(points * cpp)
            }

        annual_fee = card.get("annual_fee", 0)
        total_value_cents = int(total_points * cpp)
        net_value_cents = total_value_cents - annual_fee

        return {
            "card_id": card_id,
            "card_name": card["name"],
            "reward_program": program,
            "total_points_earned": total_points,
            "total_value_cents": total_value_cents,
            "annual_fee_cents": annual_fee,
            "net_value_cents": net_value_cents,
            "roi_percentage": round((total_value_cents / annual_fee * 100), 1) if annual_fee > 0 else None,
            "breakdown": breakdown
        }

    def get_card_summary(self, card_id: str) -> Dict[str, Any]:
        """
        Get a comprehensive summary of a card.

        Args:
            card_id: Card ID

        Returns:
            Dictionary with card details and summary
        """
        card = self.get_card_by_id(card_id)
        if not card:
            return {"error": "Card not found"}

        program = card.get("reward_program", "cash_back")
        programs = self.data_manager.get_reward_programs()
        program_info = programs.get(program, {})

        # Get current balance if tracked
        balance = self.data_manager.get_balance(program)

        # Get upcoming fee info
        fee_alerts = self.get_upcoming_annual_fees(365)
        card_fee_alert = next((a for a in fee_alerts if a.card_id == card_id), None)

        return {
            **card,
            "program_info": {
                "name": program_info.get("name", program),
                "point_value_cents": program_info.get("point_value_cents", 1.0),
                "transfer_partners": program_info.get("transfer_partners", [])
            },
            "current_balance": balance,
            "upcoming_fee": {
                "amount": card_fee_alert.annual_fee if card_fee_alert else None,
                "due_date": card_fee_alert.due_date if card_fee_alert else None,
                "days_until": card_fee_alert.days_until if card_fee_alert else None
            } if card_fee_alert else None
        }

    def validate_card_data(self, card_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate card data before adding.

        Args:
            card_data: Card data to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Required fields
        required = ["issuer", "name", "reward_type"]
        for field in required:
            if field not in card_data or not card_data[field]:
                errors.append(f"Missing required field: {field}")

        # Validate reward_type
        valid_reward_types = ["points", "cash_back", "miles"]
        if card_data.get("reward_type") not in valid_reward_types:
            errors.append(f"Invalid reward_type. Must be one of: {valid_reward_types}")

        # Validate annual_fee is non-negative
        if card_data.get("annual_fee", 0) < 0:
            errors.append("annual_fee cannot be negative")

        # Validate multipliers
        for mult in card_data.get("category_multipliers", []):
            if "category" not in mult:
                errors.append("Each multiplier must have a 'category'")
            if "multiplier" not in mult or mult["multiplier"] <= 0:
                errors.append(f"Invalid multiplier value for category: {mult.get('category')}")

        # Validate last_four if provided
        last_four = card_data.get("last_four", "")
        if last_four and (not last_four.isdigit() or len(last_four) != 4):
            errors.append("last_four must be exactly 4 digits")

        # Validate dates
        for date_field in ["opened_date", "annual_fee_due_date"]:
            date_str = card_data.get(date_field)
            if date_str:
                try:
                    datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    errors.append(f"Invalid date format for {date_field}. Use YYYY-MM-DD")

        return len(errors) == 0, errors

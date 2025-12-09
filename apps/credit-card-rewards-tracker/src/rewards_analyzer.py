"""
Rewards Analyzer for Credit Card Rewards Tracker

Provides analysis, optimization suggestions, and ROI calculations for credit card rewards.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from data_manager import DataManager
from card_service import CardService

logger = logging.getLogger(__name__)


@dataclass
class ROIAnalysis:
    """Return on Investment analysis for a card."""
    card_id: str
    card_name: str
    annual_fee_cents: int
    rewards_earned_cents: int
    net_value_cents: int
    roi_percentage: float
    is_worth_keeping: bool
    recommendation: str


@dataclass
class RedemptionSummary:
    """Summary of redemption activity."""
    total_redemptions: int
    total_points_redeemed: int
    total_value_received_cents: int
    average_cpp: float
    best_redemption_cpp: float
    worst_redemption_cpp: float
    by_program: Dict[str, Dict[str, Any]]
    by_type: Dict[str, Dict[str, Any]]


@dataclass
class TotalValueSummary:
    """Summary of total rewards value."""
    total_points_value_cents: int
    total_cash_back_cents: int
    combined_value_cents: int
    by_program: Dict[str, int]


@dataclass
class OptimizationTip:
    """Optimization suggestion for the user."""
    category: str
    priority: str  # high, medium, low
    title: str
    description: str
    potential_value_cents: Optional[int] = None


class RewardsAnalyzer:
    """Analyzes rewards data and provides optimization suggestions."""

    def __init__(
        self,
        data_manager: DataManager = None,
        card_service: CardService = None,
        config: Dict[str, Any] = None
    ):
        """
        Initialize rewards analyzer.

        Args:
            data_manager: DataManager instance
            card_service: CardService instance
            config: Configuration dictionary
        """
        self.data_manager = data_manager or DataManager()
        self.card_service = card_service or CardService(self.data_manager, config)
        self.config = config or {}

        # Get configuration values
        tracker_config = self.config.get("rewards_tracker", {})
        self.point_valuations = tracker_config.get("point_valuations", {})
        alerts_config = tracker_config.get("alerts", {})
        self.min_acceptable_roi = alerts_config.get("min_acceptable_roi", 100)
        self.low_redemption_cpp = alerts_config.get("low_redemption_cpp", 1.0)
        self.expiring_points_days = alerts_config.get("expiring_points_days", 90)

    def calculate_total_value(self) -> TotalValueSummary:
        """
        Calculate the total value of all rewards.

        Returns:
            TotalValueSummary with breakdown
        """
        all_balances = self.data_manager.get_all_balances()
        programs = self.data_manager.get_reward_programs()

        total_points_value = 0
        by_program = {}

        # Calculate points value
        for program, balance in all_balances.get("points", {}).items():
            points = balance.get("points", 0)
            cpp = self.point_valuations.get(
                program,
                programs.get(program, {}).get("point_value_cents", 1.0)
            )
            value_cents = int(points * cpp)
            total_points_value += value_cents
            by_program[program] = value_cents

        # Calculate cash back value
        total_cash_back = 0
        for card_id, balance in all_balances.get("cash_back", {}).items():
            amount = balance.get("amount_cents", 0)
            total_cash_back += amount
            by_program[f"cash_back_{card_id}"] = amount

        return TotalValueSummary(
            total_points_value_cents=total_points_value,
            total_cash_back_cents=total_cash_back,
            combined_value_cents=total_points_value + total_cash_back,
            by_program=by_program
        )

    def calculate_card_roi(self, card_id: str, period_days: int = 365) -> Optional[ROIAnalysis]:
        """
        Calculate ROI for a specific card.

        Args:
            card_id: Card ID
            period_days: Number of days to analyze

        Returns:
            ROIAnalysis or None if card not found
        """
        card = self.card_service.get_card_by_id(card_id)
        if not card:
            return None

        annual_fee = card.get("annual_fee", 0)

        # Get rewards earned on this card's program
        program = card.get("reward_program", "cash_back")

        # Calculate rewards earned (simplified - based on balance changes)
        start_date = (datetime.now() - timedelta(days=period_days)).strftime("%Y-%m-%d")
        history = self.data_manager.get_balance_history(program)

        # Filter history to period and sum positive changes
        period_earnings = sum(
            h.get("change", 0) for h in history
            if h.get("change", 0) > 0 and h.get("date", "") >= start_date
        )

        # Convert points to cents
        programs = self.data_manager.get_reward_programs()
        cpp = self.point_valuations.get(
            program,
            programs.get(program, {}).get("point_value_cents", 1.0)
        )
        rewards_value_cents = int(period_earnings * cpp)

        # Calculate net value and ROI
        net_value = rewards_value_cents - annual_fee
        roi_percentage = (rewards_value_cents / annual_fee * 100) if annual_fee > 0 else float('inf')

        # Determine if worth keeping
        is_worth_keeping = annual_fee == 0 or roi_percentage >= self.min_acceptable_roi

        # Generate recommendation
        if annual_fee == 0:
            recommendation = "No annual fee - keep for credit history and backup"
        elif roi_percentage >= 200:
            recommendation = "Excellent value - definitely worth keeping"
        elif roi_percentage >= self.min_acceptable_roi:
            recommendation = "Good value - worth keeping"
        elif roi_percentage >= 50:
            recommendation = "Marginal value - consider downgrading to no-AF version"
        else:
            recommendation = "Poor value - consider cancelling or product changing"

        return ROIAnalysis(
            card_id=card_id,
            card_name=card["name"],
            annual_fee_cents=annual_fee,
            rewards_earned_cents=rewards_value_cents,
            net_value_cents=net_value,
            roi_percentage=round(roi_percentage, 1) if roi_percentage != float('inf') else 0,
            is_worth_keeping=is_worth_keeping,
            recommendation=recommendation
        )

    def calculate_all_cards_roi(self) -> List[ROIAnalysis]:
        """Calculate ROI for all active cards with annual fees."""
        cards = self.card_service.get_active_cards()
        analyses = []

        for card in cards:
            if card.get("annual_fee", 0) > 0:
                analysis = self.calculate_card_roi(card["id"])
                if analysis:
                    analyses.append(analysis)

        # Sort by ROI descending
        analyses.sort(key=lambda a: a.roi_percentage, reverse=True)
        return analyses

    def get_redemption_stats(self, start_date: str = None, end_date: str = None) -> RedemptionSummary:
        """
        Get statistics about redemption history.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            RedemptionSummary with statistics
        """
        redemptions = self.data_manager.get_redemptions(
            start_date=start_date,
            end_date=end_date
        )

        if not redemptions:
            return RedemptionSummary(
                total_redemptions=0,
                total_points_redeemed=0,
                total_value_received_cents=0,
                average_cpp=0.0,
                best_redemption_cpp=0.0,
                worst_redemption_cpp=0.0,
                by_program={},
                by_type={}
            )

        total_points = 0
        total_value = 0
        cpps = []
        by_program = {}
        by_type = {}

        for red in redemptions:
            points = red.get("points_redeemed", 0)
            value = red.get("value_received_cents", 0)
            cpp = red.get("cents_per_point", 0)
            program = red.get("program", "unknown")
            red_type = red.get("redemption_type", "unknown")

            total_points += points
            total_value += value
            if cpp > 0:
                cpps.append(cpp)

            # Aggregate by program
            if program not in by_program:
                by_program[program] = {"count": 0, "points": 0, "value": 0}
            by_program[program]["count"] += 1
            by_program[program]["points"] += points
            by_program[program]["value"] += value

            # Aggregate by type
            if red_type not in by_type:
                by_type[red_type] = {"count": 0, "points": 0, "value": 0}
            by_type[red_type]["count"] += 1
            by_type[red_type]["points"] += points
            by_type[red_type]["value"] += value

        avg_cpp = sum(cpps) / len(cpps) if cpps else 0.0

        return RedemptionSummary(
            total_redemptions=len(redemptions),
            total_points_redeemed=total_points,
            total_value_received_cents=total_value,
            average_cpp=round(avg_cpp, 2),
            best_redemption_cpp=max(cpps) if cpps else 0.0,
            worst_redemption_cpp=min(cpps) if cpps else 0.0,
            by_program=by_program,
            by_type=by_type
        )

    def get_category_recommendations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get best card recommendations for each spending category.

        Returns:
            Dictionary of category -> recommendation details
        """
        recommendations = self.card_service.get_all_category_recommendations()
        result = {}

        for category, rec in recommendations.items():
            result[category] = {
                "card_id": rec.card_id,
                "card_name": rec.card_name,
                "multiplier": rec.multiplier,
                "program": rec.reward_program,
                "cpp": rec.estimated_cpp,
                "effective_return": f"{rec.multiplier * rec.estimated_cpp:.1f}%",
                "reason": rec.reason
            }

        return result

    def get_optimization_tips(self) -> List[OptimizationTip]:
        """
        Generate optimization suggestions based on current data.

        Returns:
            List of OptimizationTip suggestions
        """
        tips = []

        # Analyze redemption patterns
        redemption_stats = self.get_redemption_stats()

        # Tip: Low average redemption value
        if 0 < redemption_stats.average_cpp < self.low_redemption_cpp:
            tips.append(OptimizationTip(
                category="redemption",
                priority="high",
                title="Improve Redemption Value",
                description=f"Your average redemption is {redemption_stats.average_cpp:.2f} cpp. "
                           f"Consider transfer partners for 1.5-2.0+ cpp value.",
                potential_value_cents=int(
                    (1.5 - redemption_stats.average_cpp) *
                    redemption_stats.total_points_redeemed
                ) if redemption_stats.total_points_redeemed > 0 else None
            ))

        # Analyze card ROI
        roi_analyses = self.calculate_all_cards_roi()
        for analysis in roi_analyses:
            if not analysis.is_worth_keeping:
                tips.append(OptimizationTip(
                    category="annual_fee",
                    priority="high",
                    title=f"Review {analysis.card_name}",
                    description=f"ROI is only {analysis.roi_percentage:.0f}%. "
                               f"Consider downgrading or cancelling.",
                    potential_value_cents=analysis.annual_fee_cents
                ))

        # Check for upcoming annual fees
        upcoming_fees = self.card_service.get_upcoming_annual_fees(days=60)
        for fee in upcoming_fees:
            tips.append(OptimizationTip(
                category="annual_fee",
                priority="medium",
                title=f"Annual Fee Due: {fee.card_name}",
                description=f"${fee.annual_fee/100:.0f} due in {fee.days_until} days. "
                           f"{fee.recommendation}",
                potential_value_cents=fee.annual_fee
            ))

        # Check balance concentration
        total_value = self.calculate_total_value()
        if total_value.by_program:
            max_program = max(total_value.by_program.items(), key=lambda x: x[1])
            max_percentage = max_program[1] / total_value.combined_value_cents * 100 if total_value.combined_value_cents > 0 else 0

            if max_percentage > 80 and total_value.combined_value_cents > 10000:
                tips.append(OptimizationTip(
                    category="diversification",
                    priority="low",
                    title="High Balance Concentration",
                    description=f"{max_percentage:.0f}% of value is in {max_program[0]}. "
                               f"Consider redeeming some to reduce devaluation risk."
                ))

        # Check for unused category bonuses
        cards = self.card_service.get_active_cards()
        for card in cards:
            multipliers = card.get("category_multipliers", [])
            for mult in multipliers:
                if mult.get("multiplier", 1) >= 3:
                    category = mult.get("category")
                    tips.append(OptimizationTip(
                        category="spending",
                        priority="low",
                        title=f"Use {card['name']} for {category}",
                        description=f"Earning {mult['multiplier']}x on {category}. "
                                   f"Make sure you're using this card for all {category} purchases."
                    ))

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        tips.sort(key=lambda t: priority_order.get(t.priority, 3))

        return tips

    def get_earning_rate(self, period_days: int = 30) -> Dict[str, Any]:
        """
        Calculate rewards earning rate over a period.

        Args:
            period_days: Number of days to analyze

        Returns:
            Dictionary with earning statistics
        """
        start_date = (datetime.now() - timedelta(days=period_days)).strftime("%Y-%m-%d")

        # Get transactions in period
        transactions = self.data_manager.get_transactions(start_date=start_date)

        total_spend = 0
        total_rewards_value = 0
        by_card = {}
        by_category = {}

        programs = self.data_manager.get_reward_programs()

        for txn in transactions:
            amount = txn.get("amount_cents", 0)
            card_id = txn.get("card_id", "unknown")
            category = txn.get("category", "other")
            rewards = txn.get("rewards_earned", {})

            total_spend += amount

            points = rewards.get("points", 0)

            # Get card's program for valuation
            card = self.card_service.get_card_by_id(card_id)
            if card:
                program = card.get("reward_program", "cash_back")
                cpp = self.point_valuations.get(
                    program,
                    programs.get(program, {}).get("point_value_cents", 1.0)
                )
                reward_value = int(points * cpp)
            else:
                reward_value = points  # Assume 1cpp if no card info

            total_rewards_value += reward_value

            # Aggregate by card
            if card_id not in by_card:
                by_card[card_id] = {"spend": 0, "rewards_value": 0}
            by_card[card_id]["spend"] += amount
            by_card[card_id]["rewards_value"] += reward_value

            # Aggregate by category
            if category not in by_category:
                by_category[category] = {"spend": 0, "rewards_value": 0}
            by_category[category]["spend"] += amount
            by_category[category]["rewards_value"] += reward_value

        # Calculate effective return percentage
        effective_return = (total_rewards_value / total_spend * 100) if total_spend > 0 else 0

        return {
            "period_days": period_days,
            "total_spend_cents": total_spend,
            "total_rewards_value_cents": total_rewards_value,
            "effective_return_percentage": round(effective_return, 2),
            "average_daily_spend": total_spend / period_days if period_days > 0 else 0,
            "average_daily_rewards": total_rewards_value / period_days if period_days > 0 else 0,
            "by_card": by_card,
            "by_category": by_category,
            "transaction_count": len(transactions)
        }

    def project_future_balance(self, program: str, months: int = 6) -> Dict[str, Any]:
        """
        Project future balance based on earning trends.

        Args:
            program: Reward program ID
            months: Number of months to project

        Returns:
            Dictionary with projection data
        """
        # Get current balance
        balance = self.data_manager.get_balance(program)
        current_points = balance.get("points", 0) if balance else 0

        # Get earning history
        history = self.data_manager.get_balance_history(program)

        # Calculate average monthly earning (simplified)
        positive_changes = [h.get("change", 0) for h in history[-12:] if h.get("change", 0) > 0]
        avg_monthly_earning = sum(positive_changes) / max(len(positive_changes), 1) if positive_changes else 0

        # Project future balances
        projections = []
        projected_balance = current_points
        for month in range(1, months + 1):
            projected_balance += int(avg_monthly_earning)
            projections.append({
                "month": month,
                "projected_balance": projected_balance
            })

        # Get point value
        programs = self.data_manager.get_reward_programs()
        cpp = self.point_valuations.get(
            program,
            programs.get(program, {}).get("point_value_cents", 1.0)
        )

        return {
            "program": program,
            "current_balance": current_points,
            "current_value_cents": int(current_points * cpp),
            "avg_monthly_earning": int(avg_monthly_earning),
            "projections": projections,
            "projected_balance_final": projections[-1]["projected_balance"] if projections else current_points,
            "projected_value_cents": int(projections[-1]["projected_balance"] * cpp) if projections else int(current_points * cpp)
        }

    def generate_weekly_summary(self) -> Dict[str, Any]:
        """
        Generate a comprehensive weekly summary for reports.

        Returns:
            Dictionary with all summary data
        """
        # Get total value
        total_value = self.calculate_total_value()

        # Get all balances
        all_balances = self.data_manager.get_all_balances()

        # Get recent redemptions
        recent_redemptions = self.data_manager.get_recent_redemptions(5)

        # Get redemption stats for this year
        year_start = f"{datetime.now().year}-01-01"
        redemption_stats = self.get_redemption_stats(start_date=year_start)

        # Get category recommendations
        recommendations = self.get_category_recommendations()

        # Get optimization tips
        tips = self.get_optimization_tips()

        # Get upcoming fees
        upcoming_fees = self.card_service.get_upcoming_annual_fees(90)

        # Get annual summary
        annual_summary = self.data_manager.load_annual_summary()

        # Get cards with high value multipliers
        cards = self.card_service.get_active_cards()
        highlighted_cards = []
        for card in cards:
            for mult in card.get("category_multipliers", []):
                if mult.get("multiplier", 1) >= 4:
                    highlighted_cards.append({
                        "card_name": card["name"],
                        "category": mult["category"],
                        "multiplier": mult["multiplier"]
                    })

        return {
            "generated_at": datetime.now().isoformat(),
            "total_value": {
                "points_value_cents": total_value.total_points_value_cents,
                "cash_back_cents": total_value.total_cash_back_cents,
                "combined_cents": total_value.combined_value_cents,
                "by_program": total_value.by_program
            },
            "balances": {
                "points": all_balances.get("points", {}),
                "cash_back": all_balances.get("cash_back", {})
            },
            "recent_redemptions": recent_redemptions,
            "ytd_redemption_stats": {
                "total_redemptions": redemption_stats.total_redemptions,
                "total_points_redeemed": redemption_stats.total_points_redeemed,
                "total_value_received_cents": redemption_stats.total_value_received_cents,
                "average_cpp": redemption_stats.average_cpp,
                "best_cpp": redemption_stats.best_redemption_cpp
            },
            "category_recommendations": recommendations,
            "optimization_tips": [
                {
                    "priority": tip.priority,
                    "title": tip.title,
                    "description": tip.description
                } for tip in tips[:5]  # Top 5 tips
            ],
            "upcoming_fees": [
                {
                    "card_name": fee.card_name,
                    "amount": fee.annual_fee,
                    "due_date": fee.due_date,
                    "days_until": fee.days_until
                } for fee in upcoming_fees
            ],
            "annual_summary": {
                "fees_paid_cents": annual_summary.get("total_fees_paid_cents", 0),
                "rewards_value_cents": annual_summary.get("total_rewards_value_cents", 0),
                "net_value_cents": annual_summary.get("net_value_cents", 0),
                "roi_percentage": annual_summary.get("roi_percentage", 0)
            },
            "highlighted_cards": highlighted_cards
        }

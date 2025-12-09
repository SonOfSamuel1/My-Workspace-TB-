"""
Data Manager for Credit Card Rewards Tracker

Handles JSON file persistence for cards, balances, transactions, and redemptions.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataManager:
    """Manages JSON file persistence for rewards tracking data."""

    # Default data structures
    DEFAULT_CARDS = {
        "cards": [],
        "reward_programs": {
            "chase_ultimate_rewards": {
                "name": "Chase Ultimate Rewards",
                "point_value_cents": 1.5,
                "transfer_partners": ["hyatt", "united", "southwest", "marriott", "ihg"]
            },
            "amex_membership_rewards": {
                "name": "Amex Membership Rewards",
                "point_value_cents": 1.0,
                "transfer_partners": ["delta", "hilton", "marriott", "ana", "british_airways"]
            },
            "capital_one_miles": {
                "name": "Capital One Miles",
                "point_value_cents": 1.0,
                "transfer_partners": ["avianca", "wyndham", "accor"]
            },
            "citi_thank_you": {
                "name": "Citi ThankYou Points",
                "point_value_cents": 1.0,
                "transfer_partners": ["turkish", "singapore", "virgin_atlantic"]
            },
            "cash_back": {
                "name": "Cash Back",
                "point_value_cents": 1.0,
                "transfer_partners": []
            }
        }
    }

    DEFAULT_BALANCES = {
        "balances": {},
        "cash_back_balances": {},
        "history": []
    }

    DEFAULT_TRANSACTIONS = {
        "transactions": [],
        "last_sync": None
    }

    DEFAULT_REDEMPTIONS = {
        "redemptions": []
    }

    DEFAULT_ANNUAL_SUMMARY = {
        "year": datetime.now().year,
        "annual_fees_paid": [],
        "total_fees_paid_cents": 0,
        "total_rewards_value_cents": 0,
        "net_value_cents": 0,
        "roi_percentage": 0.0
    }

    def __init__(self, data_dir: str = "data"):
        """
        Initialize the data manager.

        Args:
            data_dir: Directory path for JSON data files
        """
        self.data_dir = Path(data_dir)
        self._ensure_data_directory()
        self._initialize_data_files()

    def _ensure_data_directory(self):
        """Create data directory if it doesn't exist."""
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created data directory: {self.data_dir}")

    def _initialize_data_files(self):
        """Initialize data files with defaults if they don't exist."""
        file_defaults = {
            "cards.json": self.DEFAULT_CARDS,
            "rewards_balances.json": self.DEFAULT_BALANCES,
            "transactions.json": self.DEFAULT_TRANSACTIONS,
            "redemptions.json": self.DEFAULT_REDEMPTIONS,
            "annual_summary.json": self.DEFAULT_ANNUAL_SUMMARY
        }

        for filename, default_data in file_defaults.items():
            filepath = self.data_dir / filename
            if not filepath.exists():
                self._save_json(filename, default_data)
                logger.info(f"Created default data file: {filename}")

    def _load_json(self, filename: str) -> Dict[str, Any]:
        """
        Load JSON data from file.

        Args:
            filename: Name of the JSON file

        Returns:
            Dictionary of loaded data
        """
        filepath = self.data_dir / filename
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"File not found: {filename}, returning empty dict")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON in {filename}: {e}")
            return {}

    def _save_json(self, filename: str, data: Dict[str, Any]):
        """
        Save data to JSON file.

        Args:
            filename: Name of the JSON file
            data: Dictionary to save
        """
        filepath = self.data_dir / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        logger.debug(f"Saved data to: {filename}")

    # Cards methods
    def load_cards(self) -> Dict[str, Any]:
        """Load cards configuration."""
        return self._load_json("cards.json")

    def save_cards(self, data: Dict[str, Any]):
        """Save cards configuration."""
        self._save_json("cards.json", data)

    def get_all_cards(self) -> List[Dict[str, Any]]:
        """Get list of all cards."""
        data = self.load_cards()
        return data.get("cards", [])

    def get_card_by_id(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific card by ID."""
        cards = self.get_all_cards()
        for card in cards:
            if card.get("id") == card_id:
                return card
        return None

    def add_card(self, card: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new card.

        Args:
            card: Card data dictionary

        Returns:
            The added card with generated ID
        """
        data = self.load_cards()

        # Generate ID if not provided
        if "id" not in card:
            issuer = card.get("issuer", "unknown").lower().replace(" ", "-")
            name = card.get("name", "card").lower().replace(" ", "-")
            last_four = card.get("last_four", "0000")
            card["id"] = f"{issuer}-{name}-{last_four}"

        data["cards"].append(card)
        self.save_cards(data)
        logger.info(f"Added card: {card['id']}")
        return card

    def update_card(self, card_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a card's data."""
        data = self.load_cards()
        for i, card in enumerate(data["cards"]):
            if card.get("id") == card_id:
                data["cards"][i].update(updates)
                self.save_cards(data)
                logger.info(f"Updated card: {card_id}")
                return data["cards"][i]
        return None

    def delete_card(self, card_id: str) -> bool:
        """Delete a card."""
        data = self.load_cards()
        original_count = len(data["cards"])
        data["cards"] = [c for c in data["cards"] if c.get("id") != card_id]
        if len(data["cards"]) < original_count:
            self.save_cards(data)
            logger.info(f"Deleted card: {card_id}")
            return True
        return False

    def get_reward_programs(self) -> Dict[str, Any]:
        """Get all reward programs."""
        data = self.load_cards()
        return data.get("reward_programs", {})

    def add_reward_program(self, program_id: str, program_data: Dict[str, Any]):
        """Add a new reward program."""
        data = self.load_cards()
        if "reward_programs" not in data:
            data["reward_programs"] = {}
        data["reward_programs"][program_id] = program_data
        self.save_cards(data)
        logger.info(f"Added reward program: {program_id}")

    # Balances methods
    def load_balances(self) -> Dict[str, Any]:
        """Load rewards balances."""
        return self._load_json("rewards_balances.json")

    def save_balances(self, data: Dict[str, Any]):
        """Save rewards balances."""
        self._save_json("rewards_balances.json", data)

    def get_balance(self, program: str) -> Optional[Dict[str, Any]]:
        """Get balance for a specific program."""
        data = self.load_balances()
        return data.get("balances", {}).get(program)

    def update_balance(self, program: str, points: int, source: str = "manual"):
        """
        Update balance for a reward program.

        Args:
            program: Reward program ID
            points: New point balance
            source: Source of update (manual, plaid, etc.)
        """
        data = self.load_balances()
        if "balances" not in data:
            data["balances"] = {}

        # Get point value for calculating cents value
        programs = self.get_reward_programs()
        point_value_cents = programs.get(program, {}).get("point_value_cents", 1.0)

        # Calculate change from previous balance
        old_balance = data["balances"].get(program, {}).get("points", 0)
        change = points - old_balance

        # Update balance
        now = datetime.now().isoformat()
        data["balances"][program] = {
            "points": points,
            "value_cents": int(points * point_value_cents),
            "last_updated": now,
            "source": source
        }

        # Add to history
        if "history" not in data:
            data["history"] = []

        if change != 0:
            data["history"].append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "program": program,
                "points": points,
                "change": change,
                "reason": "balance_update"
            })

        self.save_balances(data)
        logger.info(f"Updated {program} balance: {points} pts (change: {change:+d})")

    def update_cash_back_balance(self, card_id: str, amount_cents: int, source: str = "manual"):
        """Update cash back balance for a card."""
        data = self.load_balances()
        if "cash_back_balances" not in data:
            data["cash_back_balances"] = {}

        now = datetime.now().isoformat()
        data["cash_back_balances"][card_id] = {
            "amount_cents": amount_cents,
            "last_updated": now,
            "source": source
        }
        self.save_balances(data)
        logger.info(f"Updated cash back for {card_id}: ${amount_cents/100:.2f}")

    def get_all_balances(self) -> Dict[str, Any]:
        """Get all balances (points and cash back)."""
        data = self.load_balances()
        return {
            "points": data.get("balances", {}),
            "cash_back": data.get("cash_back_balances", {})
        }

    def get_balance_history(self, program: str = None, days: int = 30) -> List[Dict[str, Any]]:
        """Get balance history, optionally filtered by program."""
        data = self.load_balances()
        history = data.get("history", [])

        if program:
            history = [h for h in history if h.get("program") == program]

        # Filter by date if needed (simplified)
        return history[-100:]  # Return last 100 entries

    # Transactions methods
    def load_transactions(self) -> Dict[str, Any]:
        """Load transactions."""
        return self._load_json("transactions.json")

    def save_transactions(self, data: Dict[str, Any]):
        """Save transactions."""
        self._save_json("transactions.json", data)

    def add_transaction(self, transaction: Dict[str, Any]):
        """Add a new transaction."""
        data = self.load_transactions()
        if "transactions" not in data:
            data["transactions"] = []

        # Generate ID if not provided
        if "id" not in transaction:
            transaction["id"] = f"txn_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(data['transactions'])}"

        data["transactions"].append(transaction)
        self.save_transactions(data)
        logger.info(f"Added transaction: {transaction['id']}")

    def get_transactions(self, card_id: str = None, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Get transactions with optional filters."""
        data = self.load_transactions()
        transactions = data.get("transactions", [])

        if card_id:
            transactions = [t for t in transactions if t.get("card_id") == card_id]

        if start_date:
            transactions = [t for t in transactions if t.get("date", "") >= start_date]

        if end_date:
            transactions = [t for t in transactions if t.get("date", "") <= end_date]

        return transactions

    # Redemptions methods
    def load_redemptions(self) -> Dict[str, Any]:
        """Load redemptions."""
        return self._load_json("redemptions.json")

    def save_redemptions(self, data: Dict[str, Any]):
        """Save redemptions."""
        self._save_json("redemptions.json", data)

    def add_redemption(self, redemption: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new redemption.

        Args:
            redemption: Redemption data

        Returns:
            The added redemption with generated ID
        """
        data = self.load_redemptions()
        if "redemptions" not in data:
            data["redemptions"] = []

        # Generate ID if not provided
        if "id" not in redemption:
            redemption["id"] = f"red_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Calculate cents per point if not provided
        if "cents_per_point" not in redemption and redemption.get("points_redeemed"):
            points = redemption["points_redeemed"]
            value = redemption.get("value_received_cents", 0)
            if points > 0:
                redemption["cents_per_point"] = round(value / points, 2)

        # Set date if not provided
        if "date" not in redemption:
            redemption["date"] = datetime.now().strftime("%Y-%m-%d")

        data["redemptions"].append(redemption)
        self.save_redemptions(data)
        logger.info(f"Added redemption: {redemption['id']} - {redemption.get('program')} "
                   f"({redemption.get('points_redeemed', 0)} pts)")
        return redemption

    def get_redemptions(self, program: str = None, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Get redemptions with optional filters."""
        data = self.load_redemptions()
        redemptions = data.get("redemptions", [])

        if program:
            redemptions = [r for r in redemptions if r.get("program") == program]

        if start_date:
            redemptions = [r for r in redemptions if r.get("date", "") >= start_date]

        if end_date:
            redemptions = [r for r in redemptions if r.get("date", "") <= end_date]

        return redemptions

    def get_recent_redemptions(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get most recent redemptions."""
        data = self.load_redemptions()
        redemptions = data.get("redemptions", [])
        # Sort by date descending and return top N
        sorted_redemptions = sorted(redemptions, key=lambda r: r.get("date", ""), reverse=True)
        return sorted_redemptions[:count]

    # Annual summary methods
    def load_annual_summary(self, year: int = None) -> Dict[str, Any]:
        """Load annual summary for a given year."""
        if year is None:
            year = datetime.now().year

        data = self._load_json("annual_summary.json")

        # Check if this is for the current year
        if data.get("year") != year:
            # Return default for different year
            return {
                "year": year,
                "annual_fees_paid": [],
                "total_fees_paid_cents": 0,
                "total_rewards_value_cents": 0,
                "net_value_cents": 0,
                "roi_percentage": 0.0
            }

        return data

    def save_annual_summary(self, data: Dict[str, Any]):
        """Save annual summary."""
        self._save_json("annual_summary.json", data)

    def add_annual_fee(self, card_id: str, amount_cents: int, date: str = None, retention_offer: str = None):
        """Record an annual fee payment."""
        data = self.load_annual_summary()

        fee_record = {
            "card_id": card_id,
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "amount_cents": amount_cents,
            "retention_offer": retention_offer
        }

        data["annual_fees_paid"].append(fee_record)
        data["total_fees_paid_cents"] = sum(f["amount_cents"] for f in data["annual_fees_paid"])

        # Recalculate net value and ROI
        data["net_value_cents"] = data["total_rewards_value_cents"] - data["total_fees_paid_cents"]
        if data["total_fees_paid_cents"] > 0:
            data["roi_percentage"] = round(
                (data["total_rewards_value_cents"] / data["total_fees_paid_cents"]) * 100, 1
            )

        self.save_annual_summary(data)
        logger.info(f"Added annual fee for {card_id}: ${amount_cents/100:.2f}")

    def update_annual_rewards_value(self, total_value_cents: int):
        """Update the total rewards value for the year."""
        data = self.load_annual_summary()
        data["total_rewards_value_cents"] = total_value_cents
        data["net_value_cents"] = total_value_cents - data["total_fees_paid_cents"]

        if data["total_fees_paid_cents"] > 0:
            data["roi_percentage"] = round(
                (total_value_cents / data["total_fees_paid_cents"]) * 100, 1
            )

        self.save_annual_summary(data)

    # Backup methods
    def backup_all(self, backup_dir: str = None):
        """
        Create backup of all data files.

        Args:
            backup_dir: Optional backup directory path
        """
        if backup_dir is None:
            backup_dir = self.data_dir / "backups"

        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        files_to_backup = [
            "cards.json",
            "rewards_balances.json",
            "transactions.json",
            "redemptions.json",
            "annual_summary.json"
        ]

        for filename in files_to_backup:
            src = self.data_dir / filename
            if src.exists():
                dst = backup_path / f"{timestamp}_{filename}"
                shutil.copy2(src, dst)
                logger.debug(f"Backed up: {filename}")

        logger.info(f"Backup created at: {backup_path}")

    def get_state(self) -> Dict[str, Any]:
        """
        Load all data files and return complete state.

        Returns:
            Dictionary containing all data
        """
        return {
            "cards": self.load_cards(),
            "balances": self.load_balances(),
            "transactions": self.load_transactions(),
            "redemptions": self.load_redemptions(),
            "annual_summary": self.load_annual_summary()
        }

    def validate_data_integrity(self) -> List[str]:
        """
        Validate data integrity across files.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check cards reference valid programs
        cards_data = self.load_cards()
        programs = cards_data.get("reward_programs", {})

        for card in cards_data.get("cards", []):
            program = card.get("reward_program")
            if program and program not in programs and program != "cash_back":
                errors.append(f"Card {card.get('id')} references unknown program: {program}")

        # Check balances reference valid programs
        balances_data = self.load_balances()
        for program in balances_data.get("balances", {}).keys():
            if program not in programs and program != "cash_back":
                errors.append(f"Balance exists for unknown program: {program}")

        # Check redemptions reference valid programs
        redemptions_data = self.load_redemptions()
        for redemption in redemptions_data.get("redemptions", []):
            program = redemption.get("program")
            if program and program not in programs and program != "cash_back":
                errors.append(f"Redemption {redemption.get('id')} references unknown program: {program}")

        return errors

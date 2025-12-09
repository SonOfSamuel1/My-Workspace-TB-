"""
CLI Dashboard for Credit Card Rewards Tracker

Rich terminal dashboard for viewing rewards data and recommendations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.style import Style

from data_manager import DataManager
from card_service import CardService
from rewards_analyzer import RewardsAnalyzer

logger = logging.getLogger(__name__)


class CLIDashboard:
    """Rich terminal dashboard for rewards tracking."""

    def __init__(
        self,
        data_manager: DataManager = None,
        card_service: CardService = None,
        analyzer: RewardsAnalyzer = None,
        config: Dict[str, Any] = None
    ):
        """
        Initialize CLI dashboard.

        Args:
            data_manager: DataManager instance
            card_service: CardService instance
            analyzer: RewardsAnalyzer instance
            config: Configuration dictionary
        """
        self.data_manager = data_manager or DataManager()
        self.card_service = card_service or CardService(self.data_manager, config)
        self.analyzer = analyzer or RewardsAnalyzer(self.data_manager, self.card_service, config)
        self.config = config or {}
        self.console = Console()

    def _format_dollars(self, cents: int) -> str:
        """Format cents as dollars."""
        return f"${cents / 100:,.2f}"

    def _format_points(self, points: int) -> str:
        """Format points with commas."""
        return f"{points:,}"

    def display_header(self):
        """Display dashboard header."""
        now = datetime.now().strftime("%B %d, %Y %I:%M %p")
        self.console.print()
        self.console.print(Panel(
            f"[bold cyan]Credit Card Rewards Tracker[/bold cyan]\n"
            f"[dim]{now}[/dim]",
            style="cyan"
        ))
        self.console.print()

    def display_balances(self):
        """Display current rewards balances."""
        total_value = self.analyzer.calculate_total_value()
        all_balances = self.data_manager.get_all_balances()
        programs = self.data_manager.get_reward_programs()

        # Create balances table
        table = Table(title="Current Rewards Balances", show_header=True, header_style="bold magenta")
        table.add_column("Program", style="cyan")
        table.add_column("Balance", justify="right", style="green")
        table.add_column("Value", justify="right", style="yellow")
        table.add_column("Last Updated", style="dim")

        # Points balances
        for program_id, balance in all_balances.get("points", {}).items():
            program_name = programs.get(program_id, {}).get("name", program_id)
            points = balance.get("points", 0)
            value_cents = balance.get("value_cents", 0)
            updated = balance.get("last_updated", "")[:10]

            table.add_row(
                program_name,
                self._format_points(points) + " pts",
                self._format_dollars(value_cents),
                updated
            )

        # Cash back balances
        for card_id, balance in all_balances.get("cash_back", {}).items():
            amount = balance.get("amount_cents", 0)
            updated = balance.get("last_updated", "")[:10]
            card = self.card_service.get_card_by_id(card_id)
            card_name = card.get("name", card_id) if card else card_id

            table.add_row(
                f"{card_name} (Cash Back)",
                self._format_dollars(amount),
                self._format_dollars(amount),
                updated
            )

        # Total row
        table.add_section()
        table.add_row(
            "[bold]TOTAL[/bold]",
            "",
            f"[bold]{self._format_dollars(total_value.combined_value_cents)}[/bold]",
            ""
        )

        self.console.print(table)
        self.console.print()

    def display_cards(self):
        """Display credit cards overview."""
        cards = self.card_service.get_all_cards()

        table = Table(title="Credit Cards", show_header=True, header_style="bold blue")
        table.add_column("Card", style="cyan")
        table.add_column("Issuer", style="dim")
        table.add_column("Type", style="green")
        table.add_column("Annual Fee", justify="right")
        table.add_column("Top Categories", style="yellow")
        table.add_column("Status")

        for card in cards:
            # Get top multipliers
            multipliers = card.get("category_multipliers", [])
            top_mults = sorted(multipliers, key=lambda m: m.get("multiplier", 0), reverse=True)[:2]
            mult_str = ", ".join(
                f"{m.get('category')}: {m.get('multiplier')}x"
                for m in top_mults
            ) if top_mults else "1x base"

            # Status
            status = "[green]Active[/green]" if card.get("is_active", True) else "[red]Closed[/red]"

            # Annual fee
            fee = card.get("annual_fee", 0)
            fee_str = self._format_dollars(fee) if fee > 0 else "[dim]$0[/dim]"

            table.add_row(
                card.get("name", "Unknown"),
                card.get("issuer", "").title(),
                card.get("reward_type", "").title(),
                fee_str,
                mult_str,
                status
            )

        self.console.print(table)
        self.console.print()

    def display_recommendations(self):
        """Display category spending recommendations."""
        recommendations = self.analyzer.get_category_recommendations()

        table = Table(title="Best Card by Category", show_header=True, header_style="bold green")
        table.add_column("Category", style="cyan")
        table.add_column("Best Card", style="yellow")
        table.add_column("Multiplier", justify="right", style="green")
        table.add_column("Effective Return", justify="right", style="magenta")

        for category, rec in recommendations.items():
            effective_return = rec["multiplier"] * rec["cpp"]
            table.add_row(
                category.replace("_", " ").title(),
                rec["card_name"],
                f"{rec['multiplier']}x",
                f"{effective_return:.1f}%"
            )

        self.console.print(table)
        self.console.print()

    def display_fees(self):
        """Display annual fee analysis and upcoming fees."""
        # Upcoming fees
        upcoming = self.card_service.get_upcoming_annual_fees(90)

        if upcoming:
            table = Table(title="Upcoming Annual Fees", show_header=True, header_style="bold red")
            table.add_column("Card", style="cyan")
            table.add_column("Fee", justify="right", style="red")
            table.add_column("Due Date")
            table.add_column("Days", justify="right")
            table.add_column("Recommendation", style="yellow")

            for fee in upcoming:
                days_style = "red" if fee.days_until <= 30 else "yellow"
                table.add_row(
                    fee.card_name,
                    self._format_dollars(fee.annual_fee),
                    fee.due_date,
                    f"[{days_style}]{fee.days_until}[/{days_style}]",
                    fee.recommendation[:50] + "..." if len(fee.recommendation) > 50 else fee.recommendation
                )

            self.console.print(table)
        else:
            self.console.print("[dim]No upcoming annual fees in the next 90 days[/dim]")

        self.console.print()

        # ROI analysis for cards with fees
        roi_analyses = self.analyzer.calculate_all_cards_roi()

        if roi_analyses:
            table = Table(title="Annual Fee ROI Analysis", show_header=True, header_style="bold magenta")
            table.add_column("Card", style="cyan")
            table.add_column("Annual Fee", justify="right")
            table.add_column("Rewards Earned", justify="right", style="green")
            table.add_column("Net Value", justify="right")
            table.add_column("ROI", justify="right")
            table.add_column("Verdict")

            for analysis in roi_analyses:
                net_style = "green" if analysis.net_value_cents >= 0 else "red"
                roi_style = "green" if analysis.roi_percentage >= 100 else "red"
                verdict = "[green]Keep[/green]" if analysis.is_worth_keeping else "[red]Review[/red]"

                table.add_row(
                    analysis.card_name,
                    self._format_dollars(analysis.annual_fee_cents),
                    self._format_dollars(analysis.rewards_earned_cents),
                    f"[{net_style}]{self._format_dollars(analysis.net_value_cents)}[/{net_style}]",
                    f"[{roi_style}]{analysis.roi_percentage:.0f}%[/{roi_style}]",
                    verdict
                )

            self.console.print(table)
        else:
            self.console.print("[dim]No cards with annual fees to analyze[/dim]")

        self.console.print()

    def display_recent_redemptions(self, count: int = 10):
        """Display recent redemptions."""
        redemptions = self.data_manager.get_recent_redemptions(count)

        if not redemptions:
            self.console.print("[dim]No redemptions recorded yet[/dim]")
            self.console.print()
            return

        table = Table(title="Recent Redemptions", show_header=True, header_style="bold yellow")
        table.add_column("Date", style="dim")
        table.add_column("Program", style="cyan")
        table.add_column("Points", justify="right")
        table.add_column("Type")
        table.add_column("Value", justify="right", style="green")
        table.add_column("CPP", justify="right")

        for red in redemptions:
            cpp = red.get("cents_per_point", 0)
            cpp_style = "green" if cpp >= 1.5 else "yellow" if cpp >= 1.0 else "red"

            table.add_row(
                red.get("date", "")[:10],
                red.get("program", "").replace("_", " ").title(),
                self._format_points(red.get("points_redeemed", 0)),
                red.get("redemption_type", "").replace("_", " ").title(),
                self._format_dollars(red.get("value_received_cents", 0)),
                f"[{cpp_style}]{cpp:.2f}[/{cpp_style}]"
            )

        self.console.print(table)
        self.console.print()

    def display_optimization_tips(self):
        """Display optimization suggestions."""
        tips = self.analyzer.get_optimization_tips()

        if not tips:
            self.console.print("[green]No optimization tips at this time - you're doing great![/green]")
            self.console.print()
            return

        self.console.print("[bold]Optimization Tips[/bold]")
        self.console.print()

        for tip in tips[:5]:  # Show top 5
            priority_style = {
                "high": "red bold",
                "medium": "yellow",
                "low": "dim"
            }.get(tip.priority, "")

            priority_icon = {
                "high": "[!]",
                "medium": "[*]",
                "low": "[-]"
            }.get(tip.priority, "")

            panel = Panel(
                f"[bold]{tip.title}[/bold]\n\n{tip.description}",
                title=f"[{priority_style}]{priority_icon} {tip.priority.upper()}[/{priority_style}]",
                border_style=priority_style.split()[0] if priority_style else "dim"
            )
            self.console.print(panel)

        self.console.print()

    def display_quick_lookup(self, category: str):
        """Display best card for a specific category."""
        rec = self.card_service.get_best_card_for_category(category)

        if rec:
            effective_return = rec.multiplier * rec.estimated_cpp

            self.console.print()
            self.console.print(Panel(
                f"[bold cyan]Best Card for {category.title()}[/bold cyan]\n\n"
                f"[bold]{rec.card_name}[/bold]\n"
                f"Multiplier: [green]{rec.multiplier}x[/green]\n"
                f"Program: {rec.reward_program.replace('_', ' ').title()}\n"
                f"Point Value: {rec.estimated_cpp:.2f} cpp\n"
                f"Effective Return: [bold green]{effective_return:.1f}%[/bold green]",
                title="Recommendation"
            ))
        else:
            self.console.print(f"[red]No card recommendation found for category: {category}[/red]")

        self.console.print()

    def display_full_dashboard(self):
        """Display the complete dashboard view."""
        self.display_header()
        self.display_balances()
        self.display_recommendations()
        self.display_recent_redemptions(5)
        self.display_optimization_tips()

    def run_interactive(self):
        """Run interactive dashboard session."""
        self.display_header()

        while True:
            self.console.print("\n[bold]Dashboard Options:[/bold]")
            self.console.print("  [cyan]1[/cyan] - View Balances")
            self.console.print("  [cyan]2[/cyan] - View Cards")
            self.console.print("  [cyan]3[/cyan] - Category Recommendations")
            self.console.print("  [cyan]4[/cyan] - Annual Fee Analysis")
            self.console.print("  [cyan]5[/cyan] - Recent Redemptions")
            self.console.print("  [cyan]6[/cyan] - Optimization Tips")
            self.console.print("  [cyan]7[/cyan] - Full Dashboard")
            self.console.print("  [cyan]q[/cyan] - Quit")

            try:
                choice = self.console.input("\n[bold]Select option: [/bold]").strip().lower()
            except (KeyboardInterrupt, EOFError):
                break

            self.console.print()

            if choice == "1":
                self.display_balances()
            elif choice == "2":
                self.display_cards()
            elif choice == "3":
                self.display_recommendations()
            elif choice == "4":
                self.display_fees()
            elif choice == "5":
                self.display_recent_redemptions(10)
            elif choice == "6":
                self.display_optimization_tips()
            elif choice == "7":
                self.display_full_dashboard()
            elif choice == "q":
                self.console.print("[dim]Goodbye![/dim]")
                break
            else:
                self.console.print("[red]Invalid option. Please try again.[/red]")


def main():
    """Main entry point for testing dashboard."""
    import yaml

    # Load config
    try:
        with open("config.yaml") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        config = {}

    dashboard = CLIDashboard(config=config)
    dashboard.run_interactive()


if __name__ == "__main__":
    main()

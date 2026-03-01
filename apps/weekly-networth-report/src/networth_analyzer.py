import logging
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

ASSET_TYPES = {"checking", "savings", "otherAsset", "cash"}
LIABILITY_TYPES = {"creditCard", "otherLiability", "mortgage", "lineOfCredit"}

MILLIUNIT_FACTOR = 1000.0


class NetWorthAnalyzer:

    def __init__(self, config: dict):
        self.config = config

    def calculate_net_worth(self, accounts: list) -> dict:
        """
        Calculate net worth from a list of YNAB accounts.

        Filters out closed and deleted accounts, then categorizes remaining
        accounts into assets and liabilities. YNAB balances are in milliunits.

        Returns a dict with total_assets, total_liabilities, net_worth,
        accounts_by_type, asset_accounts, and liability_accounts.
        """
        active_accounts = [
            a
            for a in accounts
            if not a.get("closed", False) and not a.get("deleted", False)
        ]

        accounts_by_type = defaultdict(list)
        asset_accounts = []
        liability_accounts = []

        for account in active_accounts:
            account_type = account.get("type", "")
            name = account.get("name", "")
            balance_milliunits = account.get("balance", 0)
            balance = balance_milliunits / MILLIUNIT_FACTOR

            entry = {"name": name, "balance": balance, "type": account_type}

            accounts_by_type[account_type].append(entry)

            if account_type in ASSET_TYPES:
                asset_accounts.append(entry)
            elif account_type in LIABILITY_TYPES:
                liability_accounts.append(
                    {"name": name, "balance": abs(balance), "type": account_type}
                )

        total_assets = sum(a["balance"] for a in asset_accounts)
        total_liabilities = sum(a["balance"] for a in liability_accounts)
        net_worth = total_assets - total_liabilities

        logger.info(
            "Net worth calculated: assets=%.2f liabilities=%.2f net=%.2f",
            total_assets,
            total_liabilities,
            net_worth,
        )

        return {
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": net_worth,
            "accounts_by_type": dict(accounts_by_type),
            "asset_accounts": asset_accounts,
            "liability_accounts": liability_accounts,
        }

    def calculate_run_rate(self, transactions: list, months: int = 3) -> dict:
        """
        Calculate income/expense run rate over the last `months` months.

        Skips internal transfers (where transfer_account_id is not None).
        Inflows are transactions with a positive amount; outflows are negative.
        Averages per-month totals to produce run-rate figures.

        Returns avg_monthly_income, avg_monthly_expenses, avg_monthly_net,
        annual_run_rate, monthly_breakdown, and months_analyzed.
        """
        cutoff_date = datetime.now() - timedelta(days=months * 30)

        filtered = []
        for txn in transactions:
            if txn.get("transfer_account_id") is not None:
                continue
            date_str = txn.get("date", "")
            try:
                txn_date = datetime.strptime(date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                logger.warning(
                    "Skipping transaction with unparseable date: %s", date_str
                )
                continue
            if txn_date >= cutoff_date:
                filtered.append((txn_date, txn))

        monthly_income = defaultdict(float)
        monthly_expenses = defaultdict(float)

        for txn_date, txn in filtered:
            month_key = txn_date.strftime("%Y-%m")
            amount = txn.get("amount", 0) / MILLIUNIT_FACTOR
            if amount >= 0:
                monthly_income[month_key] += amount
            else:
                monthly_expenses[month_key] += abs(amount)

        all_months = set(monthly_income.keys()) | set(monthly_expenses.keys())

        monthly_breakdown = []
        for month in sorted(all_months):
            income = monthly_income.get(month, 0.0)
            expenses = monthly_expenses.get(month, 0.0)
            monthly_breakdown.append(
                {
                    "month": month,
                    "income": income,
                    "expenses": expenses,
                    "net": income - expenses,
                }
            )

        months_analyzed = len(all_months) if all_months else 1

        avg_monthly_income = sum(monthly_income.values()) / months_analyzed
        avg_monthly_expenses = sum(monthly_expenses.values()) / months_analyzed
        avg_monthly_net = avg_monthly_income - avg_monthly_expenses
        annual_run_rate = avg_monthly_net * 12

        logger.info(
            "Run rate calculated over %d months: avg_income=%.2f avg_expenses=%.2f annual_run_rate=%.2f",
            months_analyzed,
            avg_monthly_income,
            avg_monthly_expenses,
            annual_run_rate,
        )

        return {
            "avg_monthly_income": avg_monthly_income,
            "avg_monthly_expenses": avg_monthly_expenses,
            "avg_monthly_net": avg_monthly_net,
            "annual_run_rate": annual_run_rate,
            "monthly_breakdown": monthly_breakdown,
            "months_analyzed": months_analyzed,
        }

    def calculate_changes(self, current_net_worth: float, accounts: list) -> dict:
        return {
            "net_worth": current_net_worth,
        }

    def compile_report_data(self, accounts: list, transactions: list) -> dict:
        """
        Orchestrate a full report by calculating net worth and run rate,
        then returning all data combined with a generation timestamp.
        """
        logger.info("Compiling report data...")

        net_worth_data = self.calculate_net_worth(accounts)
        run_rate_data = self.calculate_run_rate(transactions)
        changes_data = self.calculate_changes(net_worth_data["net_worth"], accounts)

        report = {
            **net_worth_data,
            **run_rate_data,
            "changes": changes_data,
            "generated_at": datetime.now().isoformat(),
        }

        logger.info("Report data compiled successfully.")
        return report

#!/usr/bin/env python3
"""
Trending Analyzer for GitHub Trending Report

Scores repos by growth velocity (stars per day) rather than
absolute popularity. Tracks previously seen repos to ensure
fresh content each week.
"""
import json
import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pytz
from github_fetcher import TrendingRepo

logger = logging.getLogger(__name__)


@dataclass
class ProcessedTrending:
    """Container for processed trending data."""

    trending_repos: List[TrendingRepo]
    total_fetched: int
    language_breakdown: Dict[str, int]
    period_start: datetime
    period_end: datetime


class TrendingAnalyzer:
    """
    Analyzes and ranks trending GitHub repositories by growth velocity.

    Scores repos by stars-per-day since creation (favoring fast risers
    over established mega-repos). Tracks previously reported repos in
    seen_repos.json to enforce a cooldown period so the report stays fresh.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        report_config = config.get("report", {})
        self.max_repos = report_config.get("max_repos", 15)
        self.lookback_days = report_config.get("lookback_days", 7)
        self.timezone = pytz.timezone(config.get("timezone", "America/New_York"))

        rotation_config = config.get("rotation", {})
        self.cooldown_weeks = rotation_config.get("cooldown_weeks", 3)
        self.seen_repos_file = rotation_config.get("seen_repos_file", "seen_repos.json")

        # Will be set by caller via load_seen_repos / set_seen_repos_path
        self._seen_repos_path: Optional[Path] = None
        self._seen_repos: Dict[str, str] = {}  # full_name -> ISO date last seen

    def set_seen_repos_path(self, path: Path):
        """Set the path for the seen-repos persistence file and load it."""
        self._seen_repos_path = path
        self._seen_repos = self._load_seen_repos(path)

    def _load_seen_repos(self, path: Path) -> Dict[str, str]:
        """Load seen repos from JSON file."""
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                logger.info(f"Loaded {len(data)} seen repos from {path}")
                return data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load seen repos: {e}")
        return {}

    def save_seen_repos(self, selected_repos: List[TrendingRepo]):
        """
        Save the selected repos to the seen-repos file.

        Adds new repos with today's date, prunes entries older
        than the cooldown window.
        """
        if not self._seen_repos_path:
            return

        today = datetime.now(self.timezone).strftime("%Y-%m-%d")
        cutoff = (
            datetime.now(self.timezone) - timedelta(weeks=self.cooldown_weeks)
        ).strftime("%Y-%m-%d")

        # Add newly selected repos
        for repo in selected_repos:
            self._seen_repos[repo.full_name] = today

        # Prune entries older than cooldown window
        pruned = {
            name: date for name, date in self._seen_repos.items() if date >= cutoff
        }

        try:
            with open(self._seen_repos_path, "w") as f:
                json.dump(pruned, f, indent=2)
            logger.info(
                f"Saved {len(selected_repos)} new repos to seen list "
                f"({len(pruned)} total, pruned {len(self._seen_repos) - len(pruned)})"
            )
        except IOError as e:
            logger.error(f"Could not save seen repos: {e}")

        self._seen_repos = pruned

    def _get_cooled_down_repos(self) -> Set[str]:
        """Get set of repo full_names that are still in cooldown."""
        cutoff = (
            datetime.now(self.timezone) - timedelta(weeks=self.cooldown_weeks)
        ).strftime("%Y-%m-%d")

        return {name for name, date in self._seen_repos.items() if date >= cutoff}

    def process_repos(self, repos: List[TrendingRepo]) -> ProcessedTrending:
        """
        Score by growth velocity, filter out recently-seen repos,
        and select the top N.
        """
        logger.info(f"Processing {len(repos)} fetched repos...")

        now = datetime.now(self.timezone)
        period_end = now
        period_start = now - timedelta(days=self.lookback_days)

        cooled_down = self._get_cooled_down_repos()
        if cooled_down:
            logger.info(f"Suppressing {len(cooled_down)} recently-seen repos")

        # Score and sort
        scored = []
        for repo in repos:
            in_cooldown = repo.full_name in cooled_down
            score = self._score_repo(repo, now, in_cooldown)
            scored.append((score, repo))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Take top N (skip any that still scored negative from cooldown)
        top_repos = []
        for score, repo in scored:
            if len(top_repos) >= self.max_repos:
                break
            if score > 0:
                top_repos.append(repo)

        # Compute language breakdown
        language_breakdown = defaultdict(int)
        for repo in top_repos:
            lang = repo.language or "Unknown"
            language_breakdown[lang] += 1

        language_breakdown = dict(
            sorted(language_breakdown.items(), key=lambda x: x[1], reverse=True)
        )

        logger.info(f"Selected top {len(top_repos)} repos from {len(repos)} total")

        return ProcessedTrending(
            trending_repos=top_repos,
            total_fetched=len(repos),
            language_breakdown=language_breakdown,
            period_start=period_start,
            period_end=period_end,
        )

    def _score_repo(
        self, repo: TrendingRepo, now: datetime, in_cooldown: bool
    ) -> float:
        """
        Score a repo by growth velocity.

        Primary signal: stars per day since creation (capped).
        Bonuses for recency, description, topics.
        Heavy penalty if the repo was in a recent report.
        """
        score = 0.0

        # --- Growth velocity (0-80 points) ---
        created = repo.created_at
        if created.tzinfo is None:
            created = self.timezone.localize(created)
        else:
            created = created.astimezone(self.timezone)

        age_days = max(1, (now - created).total_seconds() / 86400)
        stars_per_day = repo.stars / age_days

        # Log-scale the velocity to prevent extreme outliers from dominating
        # A repo getting 100 stars/day scores ~80, 10/day ~40, 1/day ~0
        if stars_per_day > 0:
            score += min(80, math.log10(stars_per_day + 1) * 40)

        # --- Recency bonus (0-30 points) ---
        updated = repo.updated_at
        if updated.tzinfo is None:
            updated = self.timezone.localize(updated)
        else:
            updated = updated.astimezone(self.timezone)

        hours_since_update = max(0, (now - updated).total_seconds() / 3600)
        score += max(0, 30 - (hours_since_update / 6))

        # --- Newness bonus (0-20 points) ---
        # Younger repos get a bonus (favors discoveries over fixtures)
        if age_days <= 7:
            score += 20
        elif age_days <= 30:
            score += 10

        # --- Quality bonuses (0-10 points) ---
        if repo.description and len(repo.description) > 20:
            score += 5
        if repo.topics and len(repo.topics) >= 2:
            score += 5

        # --- Rotation penalty ---
        if in_cooldown:
            score -= 200  # Effectively excludes from selection

        return score

    def get_statistics(self, processed: ProcessedTrending) -> Dict[str, Any]:
        """Generate summary statistics for CLI output."""
        top_repos = processed.trending_repos

        avg_stars = (
            sum(r.stars for r in top_repos) // len(top_repos) if top_repos else 0
        )
        avg_forks = (
            sum(r.forks for r in top_repos) // len(top_repos) if top_repos else 0
        )

        # Compute avg growth rate
        now = datetime.now(self.timezone)
        growth_rates = []
        for r in top_repos:
            created = r.created_at
            if created.tzinfo is None:
                created = self.timezone.localize(created)
            else:
                created = created.astimezone(self.timezone)
            age_days = max(1, (now - created).total_seconds() / 86400)
            growth_rates.append(r.stars / age_days)

        avg_growth = int(sum(growth_rates) / len(growth_rates)) if growth_rates else 0

        return {
            "total_fetched": processed.total_fetched,
            "top_repos": len(top_repos),
            "languages": processed.language_breakdown,
            "avg_stars": avg_stars,
            "avg_forks": avg_forks,
            "avg_growth_rate": avg_growth,
            "period": {
                "start": processed.period_start.strftime("%Y-%m-%d"),
                "end": processed.period_end.strftime("%Y-%m-%d"),
                "days": self.lookback_days,
            },
        }

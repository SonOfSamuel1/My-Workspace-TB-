#!/usr/bin/env python3
"""
GitHub Trending Fetcher

Fetches trending repositories from the GitHub Search API.
Uses two query strategies to find both new breakout repos
and actively maintained established repos.
"""
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytz
import requests
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


@dataclass
class TrendingRepo:
    """Represents a trending GitHub repository."""

    full_name: str
    name: str
    owner: str
    description: str
    html_url: str
    stars: int
    forks: int
    language: Optional[str]
    topics: List[str]
    open_issues: int
    created_at: datetime
    updated_at: datetime
    license_name: Optional[str]

    @property
    def owner_url(self) -> str:
        return f"https://github.com/{self.owner}"


class GitHubFetcher:
    """
    Fetches trending repositories from the GitHub Search API.

    Uses two query strategies:
    - Recently created repos with >50 stars (new breakout repos)
    - Recently pushed repos with >500 stars (active established repos)
    """

    SEARCH_URL = "https://api.github.com/search/repositories"

    def __init__(
        self,
        queries_config: List[Dict[str, Any]],
        timeout: int = 30,
        timezone: str = "America/New_York",
    ):
        self.queries_config = queries_config
        self.timeout = timeout
        self.timezone = pytz.timezone(timezone)
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with GitHub API headers."""
        session = requests.Session()
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "weekly-github-trending-report",
        }

        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token}"
            logger.info("Using authenticated GitHub API requests")
        else:
            logger.info(
                "No GITHUB_TOKEN set - using unauthenticated requests "
                "(10 req/min limit)"
            )

        session.headers.update(headers)
        return session

    def fetch_trending_repos(self, lookback_days: int = 7) -> List[TrendingRepo]:
        """
        Fetch trending repos using all configured queries.

        Runs each query, deduplicates results by full_name,
        and returns the combined list.

        Args:
            lookback_days: Number of days to look back

        Returns:
            Deduplicated list of TrendingRepo objects
        """
        now = datetime.now(self.timezone)
        cutoff_date = (now - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        cutoff_30d = (now - timedelta(days=30)).strftime("%Y-%m-%d")

        all_repos: Dict[str, TrendingRepo] = {}

        for query_config in self.queries_config:
            query_name = query_config["name"]
            query_template = query_config["query_template"]
            sort = query_config.get("sort", "stars")
            per_page = query_config.get("per_page", 30)

            query = query_template.format(date=cutoff_date, date_30d=cutoff_30d)
            logger.info(f"Running query '{query_name}': {query}")

            try:
                repos = self._search_repos(query, sort=sort, per_page=per_page)
                new_count = 0
                for repo in repos:
                    if repo.full_name not in all_repos:
                        all_repos[repo.full_name] = repo
                        new_count += 1

                logger.info(
                    f"Query '{query_name}': {len(repos)} results, "
                    f"{new_count} new (after dedup)"
                )
            except Exception as e:
                logger.error(f"Query '{query_name}' failed: {e}")

        logger.info(f"Total unique repos fetched: {len(all_repos)}")
        return list(all_repos.values())

    def _search_repos(
        self, query: str, sort: str = "stars", per_page: int = 30
    ) -> List[TrendingRepo]:
        """
        Execute a single GitHub search query.

        Args:
            query: GitHub search query string
            sort: Sort field (stars, forks, updated)
            per_page: Number of results per page

        Returns:
            List of TrendingRepo objects
        """
        params = {
            "q": query,
            "sort": sort,
            "order": "desc",
            "per_page": per_page,
        }

        response = self.session.get(
            self.SEARCH_URL, params=params, timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        repos = []
        for item in items:
            try:
                repo = self._parse_repo(item)
                repos.append(repo)
            except Exception as e:
                logger.debug(f"Error parsing repo {item.get('full_name', '?')}: {e}")

        return repos

    def _parse_repo(self, item: Dict[str, Any]) -> TrendingRepo:
        """Parse a GitHub API repo item into a TrendingRepo."""
        license_info = item.get("license") or {}

        created_at = date_parser.parse(item["created_at"])
        updated_at = date_parser.parse(item["updated_at"])

        return TrendingRepo(
            full_name=item["full_name"],
            name=item["name"],
            owner=item["owner"]["login"],
            description=item.get("description") or "",
            html_url=item["html_url"],
            stars=item["stargazers_count"],
            forks=item["forks_count"],
            language=item.get("language"),
            topics=item.get("topics", []),
            open_issues=item.get("open_issues_count", 0),
            created_at=created_at,
            updated_at=updated_at,
            license_name=license_info.get("spdx_id"),
        )

    def test_api(self) -> Dict[str, Any]:
        """
        Test GitHub API connectivity and show rate limit status.

        Returns:
            Dictionary with status and rate limit info
        """
        try:
            response = self.session.get(
                "https://api.github.com/rate_limit", timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            search_limits = data.get("resources", {}).get("search", {})

            result = {
                "status": "ok",
                "authenticated": "Authorization" in self.session.headers,
                "search_limit": search_limits.get("limit", 0),
                "search_remaining": search_limits.get("remaining", 0),
                "search_reset": search_limits.get("reset", 0),
            }

            logger.info(
                f"GitHub API OK - Search rate limit: "
                f"{result['search_remaining']}/{result['search_limit']}"
            )
            return result

        except requests.RequestException as e:
            logger.error(f"GitHub API test failed: {e}")
            return {"status": "error", "error": str(e)}

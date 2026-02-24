"""Perplexity/OpenRouter source — wraps existing PerplexityService as a BaseEventSource."""

import logging
import os
from typing import List

from event_parser import Event, EventParser
from event_sources.base import BaseEventSource

logger = logging.getLogger(__name__)


class PerplexitySource(BaseEventSource):
    """Optional AI-powered event search via OpenRouter + Perplexity models."""

    def __init__(
        self,
        api_key: str = None,
        primary_model: str = "perplexity/sonar-pro",
        fallback_model: str = "perplexity/sonar-reasoning-pro",
        timezone: str = "America/New_York",
        area: str = "Gwinnett County, Georgia",
        categories: list = None,
        known_sources: list = None,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.timezone = timezone
        self.area = area
        self.categories = categories
        self.known_sources = known_sources

    @property
    def name(self) -> str:
        return "Perplexity AI"

    def fetch_events(self, lookahead_days: int = 30) -> List[Event]:
        """Search for events via Perplexity, parse, and return."""
        if not self.api_key:
            logger.info("Perplexity source skipped: no OPENROUTER_API_KEY")
            return []

        try:
            from perplexity_service import PerplexityService

            service = PerplexityService(
                api_key=self.api_key,
                primary_model=self.primary_model,
                fallback_model=self.fallback_model,
                timezone=self.timezone,
            )

            result = service.search_events(
                area=self.area,
                lookahead_days=lookahead_days,
                categories=self.categories,
                known_sources=self.known_sources,
            )

            parser = EventParser()
            events = parser.parse_response(result["content"])
            logger.info(f"Perplexity: found {len(events)} events")
            return events

        except Exception as e:
            logger.error(f"Perplexity source failed: {e}", exc_info=True)
            return []

    def validate(self) -> bool:
        """Check that the API key is set and valid."""
        if not self.api_key:
            return False
        try:
            from perplexity_service import PerplexityService

            service = PerplexityService(api_key=self.api_key)
            return service.validate_api_key()
        except Exception:
            return False

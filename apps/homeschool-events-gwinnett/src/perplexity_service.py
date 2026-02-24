#!/usr/bin/env python3
"""
Event Search Service

Searches for homeschooling events in Gwinnett County using OpenRouter API
with Perplexity sonar-pro model for web-grounded search.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import pytz
import requests

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class PerplexityService:
    """Client for event search via OpenRouter (Perplexity models)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        primary_model: str = "perplexity/sonar-pro",
        fallback_model: str = "perplexity/sonar-reasoning-pro",
        timezone: str = "America/New_York",
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is required. Set it in .env or pass directly."
            )

        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.timezone = timezone
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/anthropics/claude-code",
        }

    def search_events(
        self,
        area: str = "Gwinnett County, Georgia",
        lookahead_days: int = 30,
        categories: list = None,
        known_sources: list = None,
    ) -> dict:
        """
        Search for homeschooling events using OpenRouter + Perplexity models.

        Returns:
            dict with 'content' (response text) and 'citations' (source URLs)
        """
        tz = pytz.timezone(self.timezone)
        now = datetime.now(tz)
        end_date = now + timedelta(days=lookahead_days)

        date_range = f"{now.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"

        categories_str = ""
        if categories:
            categories_str = "\n\nEvent categories to look for:\n- " + "\n- ".join(
                categories
            )

        sources_str = ""
        if known_sources:
            sources_str = "\n\nSpecific sources to check:\n- " + "\n- ".join(
                known_sources
            )

        prompt = f"""Find all upcoming homeschool events, activities, and programs for homeschool families in and around {area} from {date_range}. Include the broader metro area and surrounding counties if relevant.

Search for events from:
- Public libraries (story times, STEM programs, homeschool-specific sessions)
- Parks & Recreation departments (homeschool classes, sports leagues, nature programs)
- State parks with homeschool programs
- Homeschool co-ops, resource fairs, and expos
- Museums and cultural centers (homeschool days, workshops)
- Community organizations (classes, clubs, competitions)
- Churches and faith-based groups offering homeschool programs
- Science centers, nature centers, and educational venues{categories_str}{sources_str}

For each event, provide:
- **Title** of the event
- **Date** (use YYYY-MM-DD format)
- **Start time** and **end time** if available
- **Location** (venue name and address)
- **Description** (brief summary)
- **URL** for more information
- **Category** (field trips, co-ops, workshops, classes, meetups, sports, arts, science fairs, support groups, library programs, or parks & rec)
- **Source** (organization or website name)

List as many verifiable events as you can find. Format each event clearly with the fields above."""

        # Try primary model first
        result = self._call_api(prompt, self.primary_model)
        if result:
            return result

        # Fallback to secondary model
        logger.warning(
            f"Primary model {self.primary_model} failed, trying {self.fallback_model}"
        )
        result = self._call_api(prompt, self.fallback_model)
        if result:
            return result

        raise RuntimeError("Both models failed to return results")

    def _call_api(self, prompt: str, model: str) -> Optional[dict]:
        """Make a single API call via OpenRouter."""
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful research assistant that finds "
                        "homeschooling events and activities. Return results "
                        "as structured JSON. Only include verifiable events "
                        "with real dates and sources."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }

        try:
            logger.info(f"Calling OpenRouter API with model: {model}")
            response = requests.post(
                OPENROUTER_API_URL,
                headers=self.headers,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            citations = data.get("citations", [])

            logger.info(
                f"API response received: {len(content)} chars, "
                f"{len(citations)} citations"
            )

            return {"content": content, "citations": citations}

        except requests.exceptions.Timeout:
            logger.error(f"OpenRouter API timeout with model {model}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"OpenRouter API HTTP error: {e.response.status_code} - {e.response.text}"
            )
            return None
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            return None

    def validate_api_key(self) -> bool:
        """Validate the API key with a minimal request."""
        payload = {
            "model": self.primary_model,
            "messages": [{"role": "user", "content": "Hello"}],
        }

        try:
            response = requests.post(
                OPENROUTER_API_URL,
                headers=self.headers,
                json=payload,
                timeout=15,
            )
            if response.status_code == 200:
                logger.info("OpenRouter API key validated successfully")
                return True
            elif response.status_code == 401:
                logger.error("OpenRouter API key is invalid")
                return False
            else:
                logger.warning(f"OpenRouter API returned status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error validating OpenRouter API key: {e}")
            return False

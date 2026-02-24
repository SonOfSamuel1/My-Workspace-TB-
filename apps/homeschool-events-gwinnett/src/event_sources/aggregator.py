"""Aggregator that collects events from multiple sources and deduplicates."""

import logging
import math
from typing import Dict, List, Optional, Set

from event_parser import Event, EventParser
from event_sources.base import BaseEventSource

logger = logging.getLogger(__name__)


class EventSourceAggregator:
    """Runs multiple event sources sequentially, merges and deduplicates results."""

    def __init__(
        self,
        sources: List[BaseEventSource],
        location_filter: Optional[Dict] = None,
        relevance_filter: Optional[Dict] = None,
    ):
        self.sources = sources
        self.location_filter = location_filter or {}
        self.relevance_filter = relevance_filter or {}

    def _filter_by_relevance(self, events: List[Event]) -> tuple:
        """Filter events to only those relevant to homeschooling/kids education."""
        if not self.relevance_filter.get("enabled", False):
            return events, len(events), len(events)

        required_keywords = [
            k.lower() for k in self.relevance_filter.get("required_keywords", [])
        ]
        exclude_keywords = [
            k.lower() for k in self.relevance_filter.get("exclude_keywords", [])
        ]

        before_count = len(events)
        filtered = []

        for event in events:
            text = (event.title + " " + (event.description or "")).lower()

            # Reject if any exclude keyword matches
            excluded = False
            for kw in exclude_keywords:
                if kw in text:
                    logger.debug(f"Relevance rejected (exclude '{kw}'): {event.title}")
                    excluded = True
                    break
            if excluded:
                continue

            # Keep if any required keyword matches
            if any(kw in text for kw in required_keywords):
                filtered.append(event)
                logger.debug(f"Relevance kept: {event.title}")
            else:
                logger.debug(f"Relevance rejected (no keyword match): {event.title}")

        after_count = len(filtered)
        removed = before_count - after_count
        if removed > 0:
            logger.info(
                f"Relevance filter: {before_count} -> {after_count} "
                f"({removed} non-homeschool events removed)"
            )

        return filtered, before_count, after_count

    @staticmethod
    def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Return straight-line distance in miles between two lat/lon points."""
        R = 3958.8  # Earth radius in miles
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _filter_by_location(self, events: List[Event]) -> tuple:
        """
        Filter events by haversine distance from origin coordinates.
        Falls back to city-name matching for events without lat/lon.

        Returns:
            (filtered_events, before_count, after_count)
        """
        if not self.location_filter.get("enabled", False):
            return events, len(events), len(events)

        origin_lat = self.location_filter.get("origin_lat")
        origin_lon = self.location_filter.get("origin_lon")
        max_radius = self.location_filter.get("max_radius_miles", 45)

        # Fallback city/keyword lists for events without coordinates
        fallback_cities: Set[str] = {
            c.lower() for c in self.location_filter.get("fallback_cities", [])
        }
        fallback_keywords: Set[str] = {
            k.lower() for k in self.location_filter.get("fallback_keywords", [])
        }

        before_count = len(events)
        filtered = []

        for event in events:
            # --- Distance-based check (preferred) ---
            if (
                origin_lat is not None
                and origin_lon is not None
                and event.latitude is not None
                and event.longitude is not None
            ):
                dist = self._haversine_miles(
                    origin_lat, origin_lon, event.latitude, event.longitude
                )
                if dist <= max_radius:
                    filtered.append(event)
                    logger.debug(
                        f"Kept ({dist:.1f} mi): {event.title} — {event.location}"
                    )
                else:
                    logger.debug(
                        f"Filtered out ({dist:.1f} mi): {event.title} — {event.location}"
                    )
                continue

            # --- Fallback: city / keyword name matching ---
            if not event.location:
                logger.debug(f"Filtered out (no location/coords): {event.title}")
                continue

            loc_lower = event.location.lower()

            if any(city in loc_lower for city in fallback_cities):
                filtered.append(event)
                logger.debug(f"Kept (city fallback): {event.title} — {event.location}")
                continue

            if any(kw in loc_lower for kw in fallback_keywords):
                filtered.append(event)
                logger.debug(
                    f"Kept (keyword fallback): {event.title} — {event.location}"
                )
                continue

            logger.debug(f"Filtered out (no match): {event.title} — {event.location}")

        after_count = len(filtered)
        removed = before_count - after_count

        if removed > 0:
            logger.info(
                f"Location filter: {before_count} -> {after_count} "
                f"({removed} events outside {max_radius}-mi radius removed)"
            )

        return filtered, before_count, after_count

    def fetch_all(self, lookahead_days: int = 30) -> Dict:
        """
        Fetch events from all sources, merge, deduplicate, and filter by location.

        Returns:
            {
                "events": List[Event],
                "source_counts": {"Eventbrite": 46, ...},
                "errors": ["source_name: error message", ...],
                "filter_stats": {"before": int, "after": int} | None,
            }
        """
        all_events: List[Event] = []
        source_counts: Dict[str, int] = {}
        errors: List[str] = []

        for source in self.sources:
            logger.info(f"Fetching from {source.name}...")
            try:
                events = source.fetch_events(lookahead_days)
                count = len(events)
                source_counts[source.name] = count
                all_events.extend(events)
                logger.info(f"  {source.name}: {count} events")
            except Exception as e:
                # Should not happen (sources catch internally), but be safe
                msg = f"{source.name}: {e}"
                logger.error(msg)
                errors.append(msg)
                source_counts[source.name] = 0

        # Deduplicate across all sources
        parser = EventParser()
        unique_events = parser.deduplicate_events(all_events)

        total_before = len(all_events)
        total_after = len(unique_events)
        if total_before != total_after:
            logger.info(
                f"Deduplication: {total_before} -> {total_after} "
                f"({total_before - total_after} duplicates removed)"
            )

        # Filter by relevance (homeschool keywords)
        relevant_events, rel_before, rel_after = self._filter_by_relevance(
            unique_events
        )

        relevance_stats = None
        if self.relevance_filter.get("enabled", False):
            relevance_stats = {"before": rel_before, "after": rel_after}

        # Filter by location (Gwinnett County cities only)
        filtered_events, filter_before, filter_after = self._filter_by_location(
            relevant_events
        )

        filter_stats = None
        if self.location_filter.get("enabled", False):
            filter_stats = {"before": filter_before, "after": filter_after}

        logger.info(
            f"Aggregator total: {len(filtered_events)} events from "
            f"{len(self.sources)} sources"
        )

        return {
            "events": filtered_events,
            "source_counts": source_counts,
            "errors": errors,
            "relevance_stats": relevance_stats,
            "filter_stats": filter_stats,
        }

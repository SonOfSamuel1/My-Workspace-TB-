"""Event sources package for multi-source web scraping."""

from event_sources.aggregator import EventSourceAggregator
from event_sources.base import BaseEventSource
from event_sources.eventbrite_source import EventbriteSource
from event_sources.ga_state_parks_source import GAStateParksSource
from event_sources.gwinnett_library_source import GwinnettLibrarySource
from event_sources.perplexity_source import PerplexitySource

__all__ = [
    "BaseEventSource",
    "EventbriteSource",
    "GAStateParksSource",
    "GwinnettLibrarySource",
    "PerplexitySource",
    "EventSourceAggregator",
]

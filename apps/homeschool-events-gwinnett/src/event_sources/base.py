"""Abstract base class for event sources."""

import abc
import logging
from typing import List

from event_parser import Event

logger = logging.getLogger(__name__)


class BaseEventSource(abc.ABC):
    """Base class that all event sources must implement."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable name of this source."""

    @abc.abstractmethod
    def fetch_events(self, lookahead_days: int = 30) -> List[Event]:
        """
        Fetch events from this source.

        IMPORTANT: This method must never raise. Catch all exceptions internally
        and return an empty list on failure.

        Args:
            lookahead_days: How many days ahead to look for events.

        Returns:
            List of Event objects. Empty list on any failure.
        """

    def validate(self) -> bool:
        """
        Check whether this source is reachable / properly configured.

        Returns:
            True if the source is available, False otherwise.
        """
        return True

"""Base class for all bookmaker scrapers.

Bakes in the data-freshness circuit breaker from the hardening addendum:
a scraper that starts returning stale data should stop feeding the engine
rather than let it generate false-positive arbs.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone


class StaleDataError(Exception):
    """Raised when scraped data is older than the freshness threshold."""


class BaseScraper(ABC):
    bookmaker_id: str
    max_staleness: timedelta = timedelta(seconds=5)

    @abstractmethod
    async def fetch_raw_odds(self) -> dict:
        """Fetch the raw odds payload from the bookmaker. Implemented per-adapter."""

    @abstractmethod
    def to_odds_event(self, raw: dict) -> dict:
        """Map the bookmaker's raw payload onto the universal OddsEvent schema
        (see scanner-schemas). Implemented per-adapter."""

    def check_freshness(self, scraped_at: datetime) -> None:
        age = datetime.now(timezone.utc) - scraped_at
        if age > self.max_staleness:
            raise StaleDataError(
                f"{self.bookmaker_id}: odds are {age.total_seconds():.1f}s old, "
                f"exceeds max_staleness of {self.max_staleness.total_seconds()}s"
            )

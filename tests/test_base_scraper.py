from datetime import datetime, timedelta, timezone

import pytest

from ingestion.base_scraper import BaseScraper, StaleDataError


class _FakeScraper(BaseScraper):
    bookmaker_id = "fake_bookie"

    async def fetch_raw_odds(self) -> dict:
        return {}

    def to_odds_event(self, raw: dict) -> dict:
        return {}


def test_check_freshness_passes_for_recent_data():
    scraper = _FakeScraper()
    scraper.check_freshness(datetime.now(timezone.utc))  # should not raise


def test_check_freshness_raises_for_stale_data():
    scraper = _FakeScraper()
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=30)

    with pytest.raises(StaleDataError):
        scraper.check_freshness(stale_time)


def test_check_freshness_respects_custom_threshold():
    scraper = _FakeScraper()
    scraper.max_staleness = timedelta(seconds=60)
    borderline_time = datetime.now(timezone.utc) - timedelta(seconds=30)

    scraper.check_freshness(borderline_time)  # should not raise, within custom threshold

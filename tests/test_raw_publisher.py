from datetime import datetime, timezone

import pytest
from fakeredis import aioredis as fakeredis_aioredis
from schemas import MarketOdds, OddsEvent

from ingestion.base_scraper import BaseScraper
from ingestion.raw_publisher import RAW_ODDS_CHANNEL, publish_odds_events, run_scraper_loop


def _sample_event(bookmaker: str) -> OddsEvent:
    return OddsEvent(
        sport="soccer",
        league="Test League",
        home_team="Team A",
        away_team="Team B",
        start_time=datetime.now(timezone.utc),
        bookmaker=bookmaker,
        markets={"moneyline": MarketOdds(home_odds=2.0, away_odds=2.0)},
        scraped_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_publish_odds_events_sends_one_message_per_event():
    redis = fakeredis_aioredis.FakeRedis(decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(RAW_ODDS_CHANNEL)
    await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)  # drain subscribe confirmation

    events = [_sample_event("book_a"), _sample_event("book_b")]
    await publish_odds_events(redis, events)

    received = []
    for _ in range(2):
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
        assert msg is not None
        received.append(msg["data"])

    assert len(received) == 2
    assert '"bookmaker":"book_a"' in received[0]
    assert '"bookmaker":"book_b"' in received[1]


class _FakeScraper(BaseScraper):
    bookmaker_id = "fake_bookie"

    def __init__(self, batches: list[list[OddsEvent]]):
        self._batches = batches

    async def fetch_raw_odds(self) -> dict:
        return {}

    def to_odds_events(self, raw: dict) -> list:
        return []

    async def poll(self, interval_seconds: float = 0):
        for batch in self._batches:
            yield batch


@pytest.mark.asyncio
async def test_run_scraper_loop_publishes_each_batch_and_skips_empty_ones():
    redis = fakeredis_aioredis.FakeRedis(decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(RAW_ODDS_CHANNEL)
    await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)

    scraper = _FakeScraper(batches=[[_sample_event("book_a")], [], [_sample_event("book_b")]])

    await run_scraper_loop(scraper, redis)

    received = []
    for _ in range(2):
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
        assert msg is not None
        received.append(msg["data"])

    # The empty batch published nothing, so only 2 messages total for 2 non-empty batches
    third = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
    assert third is None
    assert len(received) == 2

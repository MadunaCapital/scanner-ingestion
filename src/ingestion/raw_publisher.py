"""Generic publishing helper every bookmaker repo uses to send its
normalized (but not yet entity-resolved) odds to Redis, for scanner-engine
to aggregate across bookmakers and detect arbitrage.

Lives in the shared toolkit rather than being duplicated per-bookmaker --
the publishing mechanics are identical regardless of which bookmaker or
scraping method produced the OddsEvents.
"""

import logging

from redis.asyncio import Redis
from schemas import OddsEvent

from ingestion.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

RAW_ODDS_CHANNEL = "raw_odds_events"


async def publish_odds_events(redis: Redis, events: list[OddsEvent]) -> None:
    for event in events:
        await redis.publish(RAW_ODDS_CHANNEL, event.model_dump_json())


async def run_scraper_loop(scraper: BaseScraper, redis: Redis, **poll_kwargs) -> None:
    """Drives scraper.poll() forever and publishes each batch of events to
    Redis. Intended as the entrypoint each bookmaker repo's __main__.py
    calls -- keeps that file to a handful of lines.
    """
    async for events in scraper.poll(**poll_kwargs):
        if events:
            await publish_odds_events(redis, events)
            logger.info("published %d odds events from %s", len(events), scraper.bookmaker_id)

"""Generic publishing helper every bookmaker repo uses to send its
normalized (but not yet entity-resolved) odds to Redis, for scanner-engine
to aggregate across bookmakers and detect arbitrage.

Lives in the shared toolkit rather than being duplicated per-bookmaker --
the publishing mechanics are identical regardless of which bookmaker or
scraping method produced the OddsEvents.
"""

import logging
from datetime import datetime, timezone

from redis.asyncio import Redis
from schemas import RAW_ODDS_CHANNEL, OddsEvent, ScraperHeartbeat, heartbeat_key

from ingestion.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# Every bookmaker repo's own scraper.py independently defaults its poll()
# to a 45s interval_seconds (see each repo's DEFAULT_POLL_INTERVAL_SECONDS).
# Used only to size the heartbeat TTL when the caller doesn't tell us the
# actual interval via poll_kwargs["interval_seconds"] -- none of the six
# __main__.py entrypoints pass it explicitly today, so this is what's
# actually in effect for all of them right now.
DEFAULT_POLL_INTERVAL_SECONDS = 45.0

# The elegant part of this design: if a scraper process dies entirely (or
# gets stuck failing every cycle without ever reaching the yield below), it
# simply stops refreshing its key and the key expires on its own -- a
# missing/expired key IS the "down" signal for scanner-api's health
# endpoints, no separate liveness detection needed. 3x the poll interval is
# generous enough to absorb one or two slow/failed cycles without flapping.
HEARTBEAT_TTL_MULTIPLIER = 3


async def publish_odds_events(redis: Redis, events: list[OddsEvent]) -> None:
    for event in events:
        await redis.publish(RAW_ODDS_CHANNEL, event.model_dump_json())


async def _write_heartbeat(
    redis: Redis,
    bookmaker_id: str,
    ttl_seconds: float,
    *,
    status: str,
    events_published: int,
    error_message: str | None = None,
) -> None:
    heartbeat = ScraperHeartbeat(
        bookmaker_id=bookmaker_id,
        status=status,
        timestamp=datetime.now(timezone.utc),
        events_published_this_cycle=events_published,
        error_message=error_message,
    )
    try:
        await redis.set(heartbeat_key(bookmaker_id), heartbeat.model_dump_json(), ex=max(1, int(ttl_seconds)))
    except Exception:
        # Best-effort: if Redis is unreachable, the publish above almost
        # certainly failed too (or will next cycle) and the previous
        # heartbeat key will simply expire on its own -- that's the correct
        # "down" signal, so there's nothing more to do here than log it.
        logger.exception("%s: failed to write heartbeat", bookmaker_id)


async def run_scraper_loop(scraper: BaseScraper, redis: Redis, **poll_kwargs) -> None:
    """Drives scraper.poll() forever, publishes each batch of events to
    Redis, and writes a `heartbeat:{bookmaker_id}` key (see scanner-schemas'
    heartbeat.py) after every cycle so scanner-api's health endpoints can
    tell this scraper is alive and how much data it's actually moving.
    Intended as the entrypoint each bookmaker repo's __main__.py calls --
    keeps that file to a handful of lines.

    A failure while publishing (e.g. a transient Redis blip) is logged and
    reported as an "error" heartbeat rather than crashing the loop --
    matching the same "never let one bad cycle kill the long-running
    process" philosophy each bookmaker's own poll() already applies to
    fetch failures.
    """
    interval_seconds = poll_kwargs.get("interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS)
    ttl_seconds = interval_seconds * HEARTBEAT_TTL_MULTIPLIER

    async for events in scraper.poll(**poll_kwargs):
        try:
            if events:
                await publish_odds_events(redis, events)
                logger.info("published %d odds events from %s", len(events), scraper.bookmaker_id)
            await _write_heartbeat(redis, scraper.bookmaker_id, ttl_seconds, status="ok", events_published=len(events))
        except Exception as exc:
            logger.exception("%s: failed to publish this cycle's events", scraper.bookmaker_id)
            await _write_heartbeat(
                redis, scraper.bookmaker_id, ttl_seconds, status="error", events_published=0, error_message=str(exc)
            )

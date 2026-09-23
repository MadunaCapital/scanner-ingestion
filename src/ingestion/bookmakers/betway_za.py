"""Betway ZA adapter.

STATUS: STRUCTURAL STUB. The pieces marked TODO below require inspecting a
real, logged-in browser session against Betway ZA's actual site (Network
tab -> find the internal XHR/WebSocket endpoint serving live odds JSON, per
the plan). That has to happen on a real machine with a real browser and
can't be done from here — this file wires up everything around that one
missing piece so it's a single, clearly-marked gap rather than a rewrite.

Before enabling this scraper for real use, see scanner-ingestion/README.md
for the outstanding legal-review note on anti-bot evasion.
"""

from datetime import datetime, timezone

from ingestion.base_scraper import BaseScraper
from ingestion.cloudflare_session import CloudflareSession, acquire_session
from ingestion.http_client import BookmakerHttpClient
from ingestion.proxy import ProxyConfig
from schemas import MarketOdds, OddsEvent

# TODO: replace with the actual internal odds API discovered via the
# browser's Network tab (Betway ZA's frontend loads odds dynamically via
# XHR/WebSocket after the page shell loads — see the plan's "Target
# Internal APIs" section for how to find it).
BETWAY_ZA_BASE_URL = "https://www.betway.co.za"
BETWAY_ZA_ODDS_ENDPOINT = "https://www.betway.co.za/api/v1/markets"  # PLACEHOLDER


class BetwayZAScraper(BaseScraper):
    bookmaker_id = "betway_za"

    def __init__(self, proxy: ProxyConfig | None = None):
        self.proxy = proxy or ProxyConfig.from_env()
        self._session: CloudflareSession | None = None
        self._client: BookmakerHttpClient | None = None

    async def _ensure_session(self) -> None:
        """Acquire (or refresh) the Cloudflare-cleared session.

        Call this before fetch_raw_odds, and again whenever the HTTP client
        raises a ScrapeError with status 403/1020 — that's the signal the
        cf_clearance cookie has expired.
        """
        self._session = await acquire_session(BETWAY_ZA_BASE_URL, proxy=self.proxy)
        self._client = BookmakerHttpClient(
            cookies=self._session.cookies,
            user_agent=self._session.user_agent,
            proxy=self.proxy,
            referer=BETWAY_ZA_BASE_URL,
        )

    async def fetch_raw_odds(self) -> dict:
        if self._client is None:
            await self._ensure_session()

        return await self._client.fetch_json(BETWAY_ZA_ODDS_ENDPOINT)

    def to_odds_event(self, raw: dict) -> OddsEvent:
        """Map Betway ZA's raw payload onto the universal OddsEvent schema.

        TODO: field names below (home_team, away_team, market, etc.) are
        placeholders — replace them once the real payload shape is known
        from the actual API response.

        Note event_id is deliberately left unset: entity resolution (turning
        Betway's scraped team name into the universal team id) happens
        downstream in scanner-engine, not here — see the note on
        OddsEvent.event_id in scanner-schemas.
        """
        return OddsEvent(
            sport=raw["sport"],
            league=raw["league"],
            home_team=raw["home_team"],
            away_team=raw["away_team"],
            start_time=datetime.fromisoformat(raw["start_time"]),
            bookmaker=self.bookmaker_id,
            markets={
                "moneyline": MarketOdds(
                    home_odds=raw["odds"]["home"],
                    away_odds=raw["odds"]["away"],
                    draw_odds=raw["odds"].get("draw"),
                )
            },
            scraped_at=datetime.now(timezone.utc),
        )

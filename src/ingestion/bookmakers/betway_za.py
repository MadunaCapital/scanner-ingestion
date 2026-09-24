"""Betway ZA adapter.

Reads Betway ZA's public, unauthenticated odds feed — the same JSON
endpoint their own website calls to render the page for any visitor. This
is a plain HTTP GET with no TLS impersonation, no stealth browser, and no
Cloudflare bypass: none of that is needed here because the endpoint isn't
behind any bot-detection layer. Deliberately not using http_client.py's
impersonated session or cloudflare_session.py for that reason.

Endpoint discovered by ordinary browsing (Playwright, no stealth plugins)
of the public site and inspecting the requests the page itself made.
"""

from datetime import datetime, timezone

import httpx

from ingestion.base_scraper import BaseScraper
from schemas import MarketOdds, OddsEvent

BETWAY_ZA_HIGHLIGHTS_URL = "https://www.betway.co.za/sportsapi/br/v1/BetBook/Highlights/"

# marketTypeCName -> universal market key, per the plan's market-mapping
# approach (scanner-engine/formatting.py does the same for other bookmakers).
MARKET_TYPE_MAP = {
    "win-draw-win": "moneyline",
}


class BetwayZAScraper(BaseScraper):
    bookmaker_id = "betway_za"

    def __init__(self, sport_id: str = "soccer", take: int = 50):
        self.sport_id = sport_id
        self.take = take
        self._client = httpx.AsyncClient(timeout=10)

    async def fetch_raw_odds(self) -> dict:
        response = await self._client.get(
            BETWAY_ZA_HIGHLIGHTS_URL,
            params={
                "countryCode": "ZA",
                "sportId": self.sport_id,
                "Skip": 0,
                "Take": self.take,
                "cultureCode": "en-US",
                "isEsport": "false",
                "boostedOnly": "false",
                "marketTypes": "[Win/Draw/Win]",
            },
        )
        response.raise_for_status()
        return response.json()

    def to_odds_events(self, raw: dict) -> list[OddsEvent]:
        """Joins the bulk payload's events/markets/outcomes/prices arrays
        (related only by shared eventId/marketId/outcomeId) into one
        OddsEvent per match, moneyline market only for now.

        Note event_id (the OddsEvent field) is left unset here — that's the
        engine's job downstream (see the note on OddsEvent.event_id in
        scanner-schemas). Betway's own numeric eventId is preserved nowhere
        in OddsEvent by design, since it's bookmaker-specific and the whole
        point of downstream entity resolution is to not depend on it.
        """
        scraped_at = datetime.now(timezone.utc)

        markets_by_event: dict[int, list[dict]] = {}
        for market in raw.get("markets", []):
            if MARKET_TYPE_MAP.get(market.get("marketTypeCName")) is None:
                continue
            markets_by_event.setdefault(market["eventId"], []).append(market)

        outcomes_by_market: dict[str, list[dict]] = {}
        for outcome in raw.get("outcomes", []):
            outcomes_by_market.setdefault(outcome["marketId"], []).append(outcome)

        price_by_outcome: dict[str, dict] = {p["outcomeId"]: p for p in raw.get("prices", [])}

        events_by_id = {e["eventId"]: e for e in raw.get("events", [])}

        odds_events: list[OddsEvent] = []

        for event_id, markets in markets_by_event.items():
            event = events_by_id.get(event_id)
            if event is None or not event.get("isActive") or event.get("isFinished"):
                continue

            for market in markets:
                if market.get("isSuspended"):
                    continue

                universal_market = MARKET_TYPE_MAP[market["marketTypeCName"]]
                outcomes = outcomes_by_market.get(market["marketId"], [])

                home_odds = away_odds = draw_odds = None
                for outcome in outcomes:
                    price = price_by_outcome.get(outcome["outcomeId"])
                    if price is None:
                        continue
                    decimal_odds = price["priceDecimal"]

                    if outcome["name"] == event["homeTeam"]:
                        home_odds = decimal_odds
                    elif outcome["name"] == event["awayTeam"]:
                        away_odds = decimal_odds
                    elif outcome["name"].lower() == "draw":
                        draw_odds = decimal_odds

                if home_odds is None or away_odds is None:
                    continue  # incomplete market, don't publish a partial price

                odds_events.append(
                    OddsEvent(
                        sport=event["sportId"],
                        league=event.get("league", "unknown"),
                        home_team=event["homeTeam"],
                        away_team=event["awayTeam"],
                        start_time=datetime.fromtimestamp(event["expectedStartEpoch"], tz=timezone.utc),
                        bookmaker=self.bookmaker_id,
                        markets={universal_market: MarketOdds(home_odds=home_odds, away_odds=away_odds, draw_odds=draw_odds)},
                        scraped_at=scraped_at,
                    )
                )

        return odds_events

    async def close(self) -> None:
        await self._client.aclose()

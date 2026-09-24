from ingestion.bookmakers.betway_za import BetwayZAScraper

# Shape captured from a real, plain GET to Betway ZA's public
# BetBook/Highlights endpoint (see betway_za.py's docstring). Trimmed to
# one match's worth of records, field names unchanged from the real response.
SAMPLE_RAW_PAYLOAD = {
    "events": [
        {
            "eventId": 68932806,
            "isActive": True,
            "isFinished": False,
            "sportId": "soccer",
            "league": "UEFA Nations League",
            "homeTeam": "Andorra",
            "awayTeam": "Malta",
            "expectedStartEpoch": 1790265600,
        }
    ],
    "markets": [
        {
            "marketId": "689328061",
            "eventId": 68932806,
            "isSuspended": False,
            "marketTypeCName": "win-draw-win",
        }
    ],
    "outcomes": [
        {"outcomeId": "6893280611", "marketId": "689328061", "eventId": 68932806, "name": "Andorra"},
        {"outcomeId": "6893280612", "marketId": "689328061", "eventId": 68932806, "name": "Draw"},
        {"outcomeId": "6893280613", "marketId": "689328061", "eventId": 68932806, "name": "Malta"},
    ],
    "prices": [
        {"outcomeId": "6893280611", "priceDecimal": 3.75},
        {"outcomeId": "6893280612", "priceDecimal": 3.30},
        {"outcomeId": "6893280613", "priceDecimal": 2.05},
    ],
}


def test_to_odds_events_joins_events_markets_outcomes_and_prices():
    scraper = BetwayZAScraper()

    events = scraper.to_odds_events(SAMPLE_RAW_PAYLOAD)

    assert len(events) == 1
    event = events[0]
    assert event.sport == "soccer"
    assert event.league == "UEFA Nations League"
    assert event.home_team == "Andorra"
    assert event.away_team == "Malta"
    assert event.bookmaker == "betway_za"
    assert event.event_id is None  # left for the engine to compute
    assert event.markets["moneyline"].home_odds == 3.75
    assert event.markets["moneyline"].away_odds == 2.05
    assert event.markets["moneyline"].draw_odds == 3.30


def test_to_odds_events_skips_suspended_markets():
    payload = {
        **SAMPLE_RAW_PAYLOAD,
        "markets": [{**SAMPLE_RAW_PAYLOAD["markets"][0], "isSuspended": True}],
    }
    scraper = BetwayZAScraper()

    events = scraper.to_odds_events(payload)

    assert events == []


def test_to_odds_events_skips_inactive_or_finished_events():
    payload = {
        **SAMPLE_RAW_PAYLOAD,
        "events": [{**SAMPLE_RAW_PAYLOAD["events"][0], "isActive": False}],
    }
    scraper = BetwayZAScraper()

    assert scraper.to_odds_events(payload) == []


def test_to_odds_events_skips_unmapped_market_types():
    payload = {
        **SAMPLE_RAW_PAYLOAD,
        "markets": [{**SAMPLE_RAW_PAYLOAD["markets"][0], "marketTypeCName": "some-future-market-type"}],
    }
    scraper = BetwayZAScraper()

    assert scraper.to_odds_events(payload) == []


def test_to_odds_events_skips_incomplete_price_data():
    """If a price is missing for home or away, don't publish a partial/misleading market."""
    payload = {
        **SAMPLE_RAW_PAYLOAD,
        "prices": [{"outcomeId": "6893280611", "priceDecimal": 3.75}],  # only home team has a price
    }
    scraper = BetwayZAScraper()

    assert scraper.to_odds_events(payload) == []


def test_to_odds_events_handles_multiple_events_independently():
    payload = {
        "events": [
            SAMPLE_RAW_PAYLOAD["events"][0],
            {
                "eventId": 99999999,
                "isActive": True,
                "isFinished": False,
                "sportId": "soccer",
                "league": "Premier League",
                "homeTeam": "TeamA",
                "awayTeam": "TeamB",
                "expectedStartEpoch": 1790269200,
            },
        ],
        "markets": [
            SAMPLE_RAW_PAYLOAD["markets"][0],
            {"marketId": "999990001", "eventId": 99999999, "isSuspended": False, "marketTypeCName": "win-draw-win"},
        ],
        "outcomes": [
            *SAMPLE_RAW_PAYLOAD["outcomes"],
            {"outcomeId": "999990011", "marketId": "999990001", "eventId": 99999999, "name": "TeamA"},
            {"outcomeId": "999990012", "marketId": "999990001", "eventId": 99999999, "name": "Draw"},
            {"outcomeId": "999990013", "marketId": "999990001", "eventId": 99999999, "name": "TeamB"},
        ],
        "prices": [
            *SAMPLE_RAW_PAYLOAD["prices"],
            {"outcomeId": "999990011", "priceDecimal": 2.10},
            {"outcomeId": "999990012", "priceDecimal": 3.20},
            {"outcomeId": "999990013", "priceDecimal": 3.40},
        ],
    }
    scraper = BetwayZAScraper()

    events = scraper.to_odds_events(payload)

    assert len(events) == 2
    assert {e.home_team for e in events} == {"Andorra", "TeamA"}

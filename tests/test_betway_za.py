from ingestion.bookmakers.betway_za import BetwayZAScraper

SAMPLE_RAW_PAYLOAD = {
    "sport": "soccer",
    "league": "south_africa_premier_league",
    "home_team": "Kaizer Chiefs",
    "away_team": "Orlando Pirates",
    "start_time": "2026-10-24T15:00:00+00:00",
    "odds": {"home": 2.60, "away": 3.50, "draw": 3.30},
}


def test_to_odds_event_maps_placeholder_payload_shape():
    """Validates the mapping logic against the placeholder field names.

    Once the real Betway ZA payload shape is known (see the TODOs in
    betway_za.py), this test's SAMPLE_RAW_PAYLOAD should be replaced with
    an actual captured response and the field names in to_odds_event
    updated to match.
    """
    scraper = BetwayZAScraper()

    event = scraper.to_odds_event(SAMPLE_RAW_PAYLOAD)

    assert event.sport == "soccer"
    assert event.league == "south_africa_premier_league"
    assert event.home_team == "Kaizer Chiefs"
    assert event.away_team == "Orlando Pirates"
    assert event.bookmaker == "betway_za"
    assert event.event_id is None  # left for the engine to compute
    assert event.markets["moneyline"].home_odds == 2.60
    assert event.markets["moneyline"].away_odds == 3.50
    assert event.markets["moneyline"].draw_odds == 3.30

# scanner-ingestion

Scrapers for the MadunaCapital arbitrage scanner. One adapter module per South African bookmaker under `src/ingestion/bookmakers/`.

## Contents

- `src/ingestion/base_scraper.py` — abstract base class every bookmaker adapter implements, including the data-freshness circuit breaker from the hardening addendum
- `src/ingestion/bookmakers/betway_za.py` — **working, live**. Reads Betway ZA's public, unauthenticated `BetBook/Highlights` odds feed — the same JSON endpoint their own site calls to render the page. Plain `httpx` GET request, no TLS impersonation, no stealth browser, no Cloudflare bypass: none of that is needed since the endpoint isn't behind bot detection.
- `src/ingestion/proxy.py`, `src/ingestion/http_client.py`, `src/ingestion/cloudflare_session.py` — impersonated-client and Cloudflare-challenge-solving infrastructure, built but **not currently used by any adapter**. Kept for a bookmaker that turns out to actually gate its odds behind Cloudflare/WAF, which Betway ZA's public feed does not.

## Status

Betway ZA adapter is real and verified live: `fetch_raw_odds()` + `to_odds_events()` against the actual endpoint returns real current matches and odds (e.g. `Portugal vs Wales -- home=1.16 draw=7.2 away=12.0`, spot-checked and odds shape is sane). 17 passing tests, including joins across the endpoint's events/markets/outcomes/prices arrays and edge cases (suspended markets, inactive events, incomplete prices).

Not yet done: polling loop / scheduling (currently a one-shot fetch), wiring into `scanner-engine`'s normalization + arb detection, and a second bookmaker for there to be anything to arbitrage against.

## Scope note

This adapter intentionally only reads what Betway ZA's own frontend already fetches publicly, at a reasonable polling interval — no authentication bypass, no anti-bot evasion. Terms of Service exposure for scraping public data is a real but different (lower-severity, contractual rather than computer-misuse) question than the Cybercrimes Act question that applies to defeating security measures — worth keeping distinct if/when getting an actual legal read on this.

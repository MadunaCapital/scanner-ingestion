# scanner-ingestion

Scrapers for the MadunaCapital arbitrage scanner. One adapter module per South African bookmaker under `src/ingestion/bookmakers/`.

## Contents

- `src/ingestion/base_scraper.py` — abstract base class every bookmaker adapter implements, including the data-freshness circuit breaker from the hardening addendum
- `src/ingestion/proxy.py` — proxy config loaded from env (`PROXY_URL`), injected via AWS SSM in production, never hardcoded
- `src/ingestion/http_client.py` — TLS-impersonated HTTP client (wraps `curl_cffi`) for high-speed odds fetching once a session is established
- `src/ingestion/cloudflare_session.py` — solves a Cloudflare JS challenge once via Playwright and hands the resulting `cf_clearance` cookie to the fast HTTP client (the hybrid architecture from the plan)
- `src/ingestion/bookmakers/betway_za.py` — first adapter. **Structural stub**: everything is wired up except the actual odds API endpoint, which requires inspecting a real logged-in browser session against betway.co.za (see the TODOs in that file)

## Status

Infrastructure built and tested (proxy config, impersonated HTTP client, Cloudflare session handling, freshness circuit breaker — 12 passing tests). The Betway ZA adapter is structurally complete but not live: it needs the real internal odds endpoint, which only comes from inspecting the site's Network tab yourself in a real browser session — not something achievable without live browser access to the target.

**Next action for this repo:** open Betway ZA in a browser with dev tools open, find the XHR/WebSocket request that returns live odds as JSON, and fill in `BETWAY_ZA_ODDS_ENDPOINT` and the real field names in `to_odds_event` in `betway_za.py`.

## A note on legal risk

This repo will eventually contain anti-bot evasion logic (TLS impersonation, stealth browser automation) needed to reach bookmaker odds data. Per the plan's addendum, get a South African legal opinion (Cybercrimes Act, gambling regulation) before this moves beyond personal/private use.

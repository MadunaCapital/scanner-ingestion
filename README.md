# scanner-ingestion

Scrapers for the MadunaCapital arbitrage scanner. One adapter module per South African bookmaker under `src/ingestion/bookmakers/`.

## Contents

- `src/ingestion/base_scraper.py` — abstract base class every bookmaker adapter implements, including the data-freshness circuit breaker from the hardening addendum
- `src/ingestion/bookmakers/` — one module per bookmaker (empty until the first adapter is built)

## Status

Scaffolding only. No live scraper is implemented yet — see the build order in `scanner-schemas/docs/arbitrage-scanner-plan.md` (addendum): arb math and normalization come before any live scraping.

## A note on legal risk

This repo will eventually contain anti-bot evasion logic (TLS impersonation, stealth browser automation) needed to reach bookmaker odds data. Per the plan's addendum, get a South African legal opinion (Cybercrimes Act, gambling regulation) before this moves beyond personal/private use.

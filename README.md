# scanner-ingestion

Shared scraper toolkit for the MadunaCapital arbitrage scanner. This repo has no bookmaker-specific code — each bookmaker gets its own repo (e.g. [scanner-ingestion-betway-za](https://github.com/MadunaCapital/scanner-ingestion-betway-za)) that installs this one as a dependency, for maximum decoupling: a bug or a release in one bookmaker's scraper never touches another's.

## Contents

- `src/ingestion/base_scraper.py` — abstract base class every bookmaker adapter implements: `fetch_raw_odds()`, `to_odds_events()`, and the data-freshness circuit breaker from the hardening addendum
- `src/ingestion/raw_publisher.py` — generic helper (`run_scraper_loop`, `publish_odds_events`) that drives a scraper's `poll()` loop and publishes each batch to Redis; both bookmaker repos' `__main__.py` are just a few lines calling this

## Installing this as a dependency

```
maduna-scanner-ingestion @ git+https://github.com/MadunaCapital/scanner-ingestion.git
```

## Status

Toolkit built and tested (13 passing tests: freshness circuit breaker, generic Redis publisher). No bookmaker adapters live here — see `scanner-ingestion-betway-za` and `scanner-ingestion-wsb`.

## History

This repo previously carried a `stealth` extra (TLS-impersonated HTTP client + Cloudflare-challenge-solving infrastructure), built on the original plan's assumption that bookmakers would need anti-bot evasion. Stripped out once real experience across 5 bookmakers showed it wasn't earning its place: the 2 working scrapers (Betway ZA, WSB) both use plain, unauthenticated public endpoints, and the 3 harder ones (Hollywoodbets, Sportingbet ZA, Bet.co.za) need different things entirely (undocumented API params, WebSocket/SignalR push, or a Kambi-style session widget) — not TLS fingerprinting. If a genuinely WAF-protected bookmaker ever turns up, that's a real legal/technical decision to make fresh, not something worth pre-building speculatively.

# scanner-ingestion

Shared scraper toolkit for the MadunaCapital arbitrage scanner. This repo has no bookmaker-specific code — each bookmaker gets its own repo (e.g. [scanner-ingestion-betway-za](https://github.com/MadunaCapital/scanner-ingestion-betway-za)) that installs this one as a dependency, for maximum decoupling: a bug or a release in one bookmaker's scraper never touches another's.

## Contents

- `src/ingestion/base_scraper.py` — abstract base class every bookmaker adapter implements: `fetch_raw_odds()`, `to_odds_events()`, and the data-freshness circuit breaker from the hardening addendum. **Zero dependencies.**
- `src/ingestion/proxy.py` — proxy config loaded from env (`PROXY_URL`), injected via AWS SSM in production, never hardcoded. Zero dependencies.
- `src/ingestion/http_client.py`, `src/ingestion/cloudflare_session.py` — TLS-impersonated HTTP client and Cloudflare-challenge-solving infrastructure, behind the `stealth` extra (`pip install maduna-scanner-ingestion[stealth]`). **Not currently used by any bookmaker** — Betway ZA's public feed doesn't need it. Kept for a bookmaker that turns out to actually gate its odds behind a WAF.

## Installing this as a dependency

A bookmaker repo that only needs `BaseScraper` (like Betway ZA) installs the base package:

```
maduna-scanner-ingestion @ git+https://github.com/MadunaCapital/scanner-ingestion.git
```

A bookmaker repo that actually needs the Cloudflare/stealth toolkit installs the extra:

```
maduna-scanner-ingestion[stealth] @ git+https://github.com/MadunaCapital/scanner-ingestion.git
```

## Status

Toolkit built and tested (12 passing tests: proxy config, freshness circuit breaker, Cloudflare cookie extraction). No bookmaker adapters live here anymore — see `scanner-ingestion-betway-za` for the first one.

## Scope note

The `stealth` extra exists for a bookmaker that actually needs it. Read that bookmaker's own repo README for its scope note before assuming this toolkit's presence implies evasion is in use — Betway ZA's adapter deliberately doesn't use it.

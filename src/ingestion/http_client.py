"""High-speed HTTP client with TLS/browser fingerprint impersonation.

Standard HTTP clients (requests, aiohttp) send a TLS ClientHello that is
instantly recognizable as a bot (the JA3/JA4 fingerprint) and get a 1020
Access Denied before headers are even read. curl_cffi's `impersonate`
parameter matches a real browser's TLS/HTTP2 stack, per the plan.

This wraps curl_cffi rather than using it directly so the impersonate
version, proxy, and cookie/session-transfer logic (from a Cloudflare
challenge solved by Playwright — see cloudflare_session.py) live in one
place instead of being repeated in every bookmaker adapter.
"""

from dataclasses import dataclass, field

import orjson
from curl_cffi.requests import AsyncSession

from ingestion.proxy import ProxyConfig

# Keep this aligned with whatever Chromium version Playwright downloads —
# a mismatch between the impersonated TLS fingerprint and the browser that
# solved the Cloudflare challenge will get the session invalidated.
DEFAULT_IMPERSONATE = "chrome124"


class ScrapeError(Exception):
    """Raised when a bookmaker responds with a non-success status.

    Callers should treat 403/1020 specifically as a signal that the
    cf_clearance cookie has expired and a Cloudflare re-solve (via
    cloudflare_session.py) is needed before retrying.
    """

    def __init__(self, status_code: int, url: str):
        self.status_code = status_code
        self.url = url
        super().__init__(f"Request to {url} failed with status {status_code}")


@dataclass
class BookmakerHttpClient:
    cookies: dict[str, str]
    user_agent: str
    proxy: ProxyConfig | None = None
    impersonate: str = DEFAULT_IMPERSONATE
    timeout: int = 10
    referer: str | None = None
    _session: AsyncSession = field(init=False, repr=False)

    def __post_init__(self):
        self._session = AsyncSession(impersonate=self.impersonate)
        if self.proxy:
            self._session.proxies = self.proxy.as_dict()

    async def fetch_json(self, url: str) -> dict:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
        }
        if self.referer:
            headers["Referer"] = self.referer

        response = await self._session.get(
            url,
            headers=headers,
            cookies=self.cookies,
            timeout=self.timeout,
        )

        if response.status_code != 200:
            raise ScrapeError(response.status_code, url)

        return orjson.loads(response.content)

    async def close(self) -> None:
        await self._session.close()

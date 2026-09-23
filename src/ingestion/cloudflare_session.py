"""Solve a Cloudflare JS challenge once via stealth Playwright, then hand
the resulting session (cf_clearance cookie + user agent) to the fast
curl_cffi client for all subsequent requests.

This is the hybrid architecture from the plan: running headless Playwright
for every request is too slow for a time-sensitive arbitrage scanner, so
it's used only to acquire the clearance cookie, which is then reused until
it expires (typically 30-120 minutes).
"""

import asyncio
from dataclasses import dataclass

from playwright.async_api import async_playwright

from ingestion.proxy import ProxyConfig

CF_CLEARANCE_COOKIE_NAME = "cf_clearance"
CF_CLEARANCE_POLL_INTERVAL_SECONDS = 1
CF_CLEARANCE_POLL_MAX_ATTEMPTS = 30


class CloudflareChallengeTimeout(Exception):
    """Raised when the cf_clearance cookie isn't issued within the poll window."""


@dataclass
class CloudflareSession:
    cookies: dict[str, str]
    user_agent: str


def extract_cf_clearance(cookies: list[dict]) -> dict | None:
    """Pure logic split out from the Playwright polling loop so it's testable
    without a real browser: find the cf_clearance cookie among a raw cookie
    list, if present."""
    return next((c for c in cookies if c["name"] == CF_CLEARANCE_COOKIE_NAME), None)


async def acquire_session(target_url: str, proxy: ProxyConfig | None = None) -> CloudflareSession:
    """Launch a stealth Playwright browser, navigate to the target, and poll
    for the cf_clearance cookie Cloudflare issues once its challenge is
    satisfied.

    Requires the puppeteer-extra-plugin-stealth equivalent for Python
    (playwright-stealth) to be applied by the caller's browser context —
    left to the caller so this function stays a pure session-acquisition
    step rather than also owning stealth configuration.
    """
    launch_args = ["--disable-blink-features=AutomationControlled"]
    launch_options: dict = {"headless": False, "args": launch_args}
    if proxy:
        launch_options["proxy"] = proxy.as_playwright_proxy()

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_options)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        await page.goto(target_url, wait_until="domcontentloaded")

        cf_cookie = None
        for _ in range(CF_CLEARANCE_POLL_MAX_ATTEMPTS):
            cookies = await context.cookies()
            cf_cookie = extract_cf_clearance(cookies)
            if cf_cookie:
                break
            await asyncio.sleep(CF_CLEARANCE_POLL_INTERVAL_SECONDS)

        if not cf_cookie:
            await browser.close()
            raise CloudflareChallengeTimeout(
                f"Failed to acquire cf_clearance for {target_url} within "
                f"{CF_CLEARANCE_POLL_MAX_ATTEMPTS * CF_CLEARANCE_POLL_INTERVAL_SECONDS}s"
            )

        cookie_dict = {c["name"]: c["value"] for c in cookies}
        user_agent = await page.evaluate("navigator.userAgent")

        await browser.close()

        return CloudflareSession(cookies=cookie_dict, user_agent=user_agent)

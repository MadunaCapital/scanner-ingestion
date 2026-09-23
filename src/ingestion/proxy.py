"""Proxy configuration, loaded from environment variables.

Per the plan and its infra addendum: datacenter IPs (including AWS) get
instantly flagged by bookmaker WAFs, so all scraper egress must route
through a residential/mobile proxy. The connection string itself is never
hardcoded — in production it's injected via AWS SSM Parameter Store as an
ECS task environment variable (see scanner-infra).
"""

import os
from dataclasses import dataclass


@dataclass
class ProxyConfig:
    url: str

    @classmethod
    def from_env(cls, var_name: str = "PROXY_URL") -> "ProxyConfig | None":
        url = os.getenv(var_name)
        if not url:
            return None
        return cls(url=url)

    def as_dict(self) -> dict[str, str]:
        """Format for curl_cffi's `proxies=` kwarg."""
        return {"http": self.url, "https": self.url}

    def as_playwright_proxy(self) -> dict[str, str]:
        """Format for Playwright's `launch(proxy=...)` kwarg."""
        return {"server": self.url}

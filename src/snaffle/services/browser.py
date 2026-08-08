"""Shared headless-browser facility (Selenium; no Node.js runtime involved).

Central place for launching a browser that presents itself as a plausible
human-driven browser (real user agent, correct viewport, no automation flags).
Plugins must use this rather than launching their own driver.
"""

from __future__ import annotations

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def build_stealth_arguments() -> list[str]:
    """Chromium command-line arguments that suppress automation fingerprints."""
    return [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        f"--user-agent={DEFAULT_USER_AGENT}",
    ]


def build_stealth_capabilities() -> dict:
    """User agent, viewport, locale and related context options for the driver."""
    return {
        "user_agent": DEFAULT_USER_AGENT,
        "viewport": {"width": 1366, "height": 768},
        "locale": "en-GB",
        "timezone": "Europe/London",
    }


class BrowserService:
    """Lazily-started shared Selenium WebDriver."""

    def __init__(self, proxy_url: str | None = None) -> None:
        self.proxy_url = proxy_url
        self._driver = None

    def new_driver(self):
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

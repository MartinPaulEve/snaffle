"""Shared browser facility (Selenium + Chrome; no Node.js runtime involved).

Used for sources that fingerprint and block plain HTTP clients and for
institutional login, where a visible browser lets the user complete SSO and
approve an Okta push once, after which the session is reused to harvest PDFs.
"""

from __future__ import annotations

import time

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
CHROME_BINARY = "/usr/bin/google-chrome"


def build_stealth_arguments(headless: bool = False) -> list[str]:
    """Chrome arguments that suppress automation fingerprints."""
    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-infobars",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-agent={DEFAULT_USER_AGENT}",
    ]
    if headless:
        args.append("--headless=new")
    return args


def build_stealth_capabilities() -> dict:
    return {
        "user_agent": DEFAULT_USER_AGENT,
        "viewport": {"width": 1366, "height": 768},
        "locale": "en-GB",
        "timezone": "Europe/London",
    }


class BrowserSession:
    """Thin, testable wrapper over a Selenium WebDriver."""

    def __init__(self, driver) -> None:
        self.driver = driver

    def get(self, url: str) -> None:
        self.driver.get(url)

    @property
    def current_url(self) -> str:
        return self.driver.current_url

    @property
    def page_source(self) -> str:
        return self.driver.page_source

    def cookies(self) -> dict:
        return {c["name"]: c["value"] for c in self.driver.get_cookies()}

    def wait_until_authenticated(
        self, login_host: str, timeout: float = 300.0, poll: float = 2.0, sleep=time.sleep
    ) -> bool:
        """Block until the browser leaves the identity-provider host.

        Used for manual login: the user signs in and approves any push in the
        visible window; this returns once the browser has navigated away from
        the login/IdP domain (or the timeout elapses).
        """
        waited = 0.0
        while waited < timeout:
            if login_host not in self.current_url:
                return True
            sleep(poll)
            waited += poll
        return False

    def wait_for_cookie(
        self, name_contains: str, timeout: float = 300.0, poll: float = 2.0, sleep=time.sleep
    ) -> bool:
        """Block until a cookie whose name contains ``name_contains`` appears.

        EZProxy sets a session cookie once the institutional login completes, so
        this is a reliable "the user has finished logging in" signal.
        """
        needle = name_contains.lower()
        waited = 0.0
        while waited < timeout:
            if any(needle in name.lower() for name in self.cookies()):
                return True
            sleep(poll)
            waited += poll
        return False


class BrowserService:
    """Lazily-started shared Chrome browser."""

    def __init__(self, headless: bool = False, proxy_url: str | None = None) -> None:
        self.headless = headless
        self.proxy_url = proxy_url
        self._driver = None

    def _start(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        options = Options()
        options.binary_location = CHROME_BINARY
        for arg in build_stealth_arguments(self.headless):
            options.add_argument(arg)
        if self.proxy_url:
            options.add_argument(f"--proxy-server={self.proxy_url}")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        driver = webdriver.Chrome(options=options)
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
        )
        return driver

    def session(self) -> BrowserSession:
        if self._driver is None:
            self._driver = self._start()
        return BrowserSession(self._driver)

    def close(self) -> None:
        if self._driver is not None:
            self._driver.quit()
            self._driver = None

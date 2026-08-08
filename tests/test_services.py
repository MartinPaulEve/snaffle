import httpx

from snaffle.models import Credential
from snaffle.services.browser import (
    BrowserSession,
    build_stealth_arguments,
    build_stealth_capabilities,
)
from snaffle.services.captcha import TwoCaptchaClient
from snaffle.services.ezproxy import build_proxied_url
from snaffle.services.tor import TorService


def test_build_proxied_url_rewrites_host():
    url = build_proxied_url("https://www.jstor.org/stable/123", "https://ezproxy.bbk.ac.uk")
    assert "ezproxy.bbk.ac.uk" in url
    assert "jstor.org" in url


def test_tor_proxy_url_points_at_socks():
    tor = TorService(host="127.0.0.1", port=9050)
    assert tor.proxy_url() == "socks5://127.0.0.1:9050"


def test_stealth_arguments_disable_automation_flags():
    args = build_stealth_arguments()
    joined = " ".join(args)
    assert "--disable-blink-features=AutomationControlled" in joined


def test_stealth_capabilities_have_user_agent():
    caps = build_stealth_capabilities()
    assert "user_agent" in caps
    assert "Mozilla" in caps["user_agent"]


class _FakeDriver:
    def __init__(self, urls):
        self._urls = list(urls)

    @property
    def current_url(self):
        # Advance through the sequence, holding on the last value.
        return self._urls.pop(0) if len(self._urls) > 1 else self._urls[0]

    def get_cookies(self):
        return [{"name": "s", "value": "1"}]


def test_wait_until_authenticated_returns_when_leaving_idp():
    # Stays on the IdP for two polls, then lands on the proxied publisher.
    driver = _FakeDriver(
        [
            "https://idp.okta.com/login",
            "https://idp.okta.com/challenge",
            "https://tandfonline-com.ezproxy/article",
        ]
    )
    session = BrowserSession(driver)
    assert session.wait_until_authenticated("okta.com", timeout=10, poll=0, sleep=lambda s: None)


def test_wait_until_authenticated_times_out():
    driver = _FakeDriver(["https://idp.okta.com/login"])
    session = BrowserSession(driver)
    assert (
        session.wait_until_authenticated("okta.com", timeout=1, poll=1, sleep=lambda s: None)
        is False
    )


def test_browser_session_cookies_flatten():
    session = BrowserSession(_FakeDriver(["https://x"]))
    assert session.cookies() == {"s": "1"}


class _CookieDriver:
    def __init__(self, cookie_after):
        self._n = 0
        self._after = cookie_after

    @property
    def current_url(self):
        return "https://x"

    def get_cookies(self):
        self._n += 1
        return [{"name": "ezproxyl", "value": "1"}] if self._n > self._after else []


def test_wait_for_cookie_returns_once_present():
    session = BrowserSession(_CookieDriver(cookie_after=2))
    assert session.wait_for_cookie("ezproxy", timeout=10, poll=0, sleep=lambda s: None)


def test_wait_for_cookie_times_out():
    session = BrowserSession(_CookieDriver(cookie_after=999))
    assert session.wait_for_cookie("ezproxy", timeout=1, poll=1, sleep=lambda s: None) is False


def test_twocaptcha_solves_recaptcha_via_polling():
    responses = iter(
        [
            httpx.Response(200, json={"status": 1, "request": "OK|captchaid"}),  # submit
            httpx.Response(200, json={"status": 0, "request": "CAPCHA_NOT_READY"}),  # poll 1
            httpx.Response(200, json={"status": 1, "request": "SOLVED-TOKEN"}),  # poll 2
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    client = TwoCaptchaClient("apikey", http=httpx.Client(transport=httpx.MockTransport(handler)))
    token = client.solve_recaptcha_v2("site-key", "https://example.com")
    assert token == "SOLVED-TOKEN"


def test_credential_dataclass_defaults():
    c = Credential(institution="MSU", username="grace", password_ref="op://v/i/p")
    assert c.otp_ref is None
    assert c.ezproxy_base is None

import httpx

from snaffle.models import Credential
from snaffle.services.browser import build_stealth_arguments, build_stealth_capabilities
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

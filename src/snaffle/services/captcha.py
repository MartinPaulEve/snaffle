"""CAPTCHA solving via the 2Captcha API (paid service; key supplied via secrets)."""

from __future__ import annotations

import time

_BASE = "https://2captcha.com"


class TwoCaptchaClient:
    def __init__(self, api_key: str, http=None, poll_interval: float = 0.0) -> None:
        self.api_key = api_key
        self.http = http
        self.poll_interval = poll_interval

    def _solve(self, method: str, site_key: str, page_url: str, extra_key: str) -> str:
        submit = self.http.get(
            f"{_BASE}/in.php",
            params={
                "key": self.api_key,
                "method": method,
                extra_key: site_key,
                "pageurl": page_url,
                "json": 1,
            },
        ).json()
        if submit.get("status") != 1:
            raise RuntimeError(f"2Captcha submit failed: {submit.get('request')}")
        captcha_id = submit["request"]

        while True:
            result = self.http.get(
                f"{_BASE}/res.php",
                params={"key": self.api_key, "action": "get", "id": captcha_id, "json": 1},
            ).json()
            if result.get("status") == 1:
                return result["request"]
            if result.get("request") != "CAPCHA_NOT_READY":
                raise RuntimeError(f"2Captcha error: {result.get('request')}")
            if self.poll_interval:
                time.sleep(self.poll_interval)

    def solve_recaptcha_v2(self, site_key: str, page_url: str) -> str:
        """Return the g-recaptcha-response token for the given site."""
        return self._solve("userrecaptcha", site_key, page_url, "googlekey")

    def solve_turnstile(self, site_key: str, page_url: str) -> str:
        return self._solve("turnstile", site_key, page_url, "sitekey")

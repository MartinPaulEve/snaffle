"""Okta authentication with push-to-device MFA.

For institutions (e.g. MSU) whose SSO is Okta and whose second factor is an
Okta Verify push, this runs the ``/api/v1/authn`` state machine: primary auth,
then trigger the push factor and poll until the user approves on their phone,
returning a one-time Okta session token that the caller can exchange for a
session cookie at the institution's login endpoint.
"""

from __future__ import annotations

import time


class OktaError(RuntimeError):
    """Raised when Okta authentication cannot complete (rejected, timeout, etc.)."""


class OktaAuthenticator:
    def __init__(self, org_url: str, http, poll_interval: float = 3.0, max_polls: int = 60) -> None:
        self.org_url = org_url.rstrip("/")
        self.http = http
        self.poll_interval = poll_interval
        self.max_polls = max_polls

    def authenticate(self, username: str, password: str) -> str:
        """Return an Okta session token, prompting a device push if required."""
        primary = self.http.post(
            f"{self.org_url}/api/v1/authn",
            json={"username": username, "password": password},
        ).json()

        status = primary.get("status")
        if status == "SUCCESS":
            return primary["sessionToken"]
        if status != "MFA_REQUIRED":
            raise OktaError(f"unexpected Okta status: {status}")

        state_token = primary.get("stateToken")
        verify_url = self._push_verify_url(primary)
        return self._poll_push(verify_url, state_token)

    def _push_verify_url(self, primary: dict) -> str:
        factors = (primary.get("_embedded") or {}).get("factors") or []
        for factor in factors:
            if factor.get("factorType") == "push":
                href = (((factor.get("_links") or {}).get("verify")) or {}).get("href")
                if href:
                    return href
        raise OktaError("no Okta push factor is enrolled for this account")

    def _poll_push(self, verify_url: str, state_token: str) -> str:
        for _ in range(self.max_polls):
            result = self.http.post(verify_url, json={"stateToken": state_token}).json()
            status = result.get("status")
            if status == "SUCCESS":
                return result["sessionToken"]
            factor_result = result.get("factorResult")
            if factor_result and factor_result != "WAITING":
                raise OktaError(f"Okta push not approved: {factor_result}")
            if self.poll_interval:
                time.sleep(self.poll_interval)
        raise OktaError("timed out waiting for Okta push approval")

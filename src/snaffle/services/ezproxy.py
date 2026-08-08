"""Institutional access via EZproxy-style URL rewriting and login."""

from __future__ import annotations

from snaffle.models import Credential


def build_proxied_url(target_url: str, ezproxy_base: str) -> str:
    """Rewrite ``target_url`` so it is fetched through the institution's EZproxy.

    EZproxy's URL form is ``<base>/login?url=<target>``; once authenticated the
    proxy rewrites subsequent links, but this entry URL is what we request.
    """
    from urllib.parse import quote

    base = ezproxy_base.rstrip("/")
    return f"{base}/login?url={quote(target_url, safe='')}"


class EZProxySession:
    """Authenticates against an institution and fetches pages through EZproxy.

    Two second-factor methods are supported per credential: ``totp`` (a code
    generated from a 1Password item) and ``push`` (approve an Okta Verify push
    on your phone — used by e.g. MSU on Okta).
    """

    def __init__(self, credential: Credential, ctx) -> None:
        self.credential = credential
        self.ctx = ctx

    def _password(self) -> str:
        return self.ctx.secrets.resolve(self.credential.password_ref)

    def current_otp(self) -> str:
        """The current TOTP code for a ``totp`` credential."""
        if not self.credential.otp_ref:
            raise ValueError(f"no OTP configured for {self.credential.institution}")
        return self.ctx.secrets.totp(self.credential.otp_ref)

    def obtain_session_token(self) -> str:
        """Authenticate and return a session token, prompting a push if needed.

        For ``push`` credentials this drives the Okta push flow (the phone will
        buzz); the caller exchanges the returned token for a session at the
        institution's login endpoint.
        """
        if self.credential.mfa_method == "push":
            from snaffle.services.okta import OktaAuthenticator

            if not self.credential.okta_org:
                raise ValueError(
                    f"{self.credential.institution} uses push MFA but no Okta org is set"
                )
            authenticator = OktaAuthenticator(self.credential.okta_org, self.ctx.http)
            return authenticator.authenticate(self.credential.username, self._password())
        raise NotImplementedError(
            "non-push session-token exchange is institution-specific; use current_otp()"
        )

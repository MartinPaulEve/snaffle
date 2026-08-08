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
    """Logs into an institution's EZproxy (handling TOTP) and fetches pages."""

    def __init__(self, credential: Credential, ctx) -> None:
        self.credential = credential
        self.ctx = ctx

    def login(self) -> bool:
        raise NotImplementedError

    def get(self, url: str):
        raise NotImplementedError

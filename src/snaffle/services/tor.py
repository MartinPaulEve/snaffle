"""Tor network access for plugins that need it."""

from __future__ import annotations


class TorService:
    """Provides proxy settings pointing at a local Tor SOCKS listener."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9050) -> None:
        self.host = host
        self.port = port

    def proxy_url(self) -> str:
        return f"socks5://{self.host}:{self.port}"

    def httpx_proxy(self) -> str:
        # httpx uses the same URL scheme for SOCKS proxies.
        return self.proxy_url()

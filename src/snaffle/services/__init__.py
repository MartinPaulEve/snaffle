"""Shared services made available to every plugin via ServiceContext."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class ServiceContext:
    """Bundle of shared facilities passed to every plugin.

    Plugins must reach the network through ``http`` (or the browser service)
    so that tests can inject mock transports and so shared behaviour such as
    rate limiting and user-agent handling stays in one place.
    """

    http: httpx.Client
    secrets: Any = None  # snaffle.secrets.SecretStore
    browser: Any = None  # snaffle.services.browser.BrowserService
    tor: Any = None  # snaffle.services.tor.TorService
    captcha: Any = None  # snaffle.services.captcha.TwoCaptchaClient
    kagi: Any = None  # snaffle.services.kagi.KagiClient
    credentials: list = field(default_factory=list)  # list[Credential]
    config: dict = field(default_factory=dict)
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("snaffle"))

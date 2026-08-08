"""ANSI-art 'snaffle' banner, painted to stderr."""

from __future__ import annotations

import sys

_ART = r"""
 ___  ___    __    ____  ____  __    ____
/ __)(  _ \  /__\  ( ___)( ___)(  )  ( ___)
\__ \ )   / /(__)\  )__)  )__)  )(__  )__)
(___/(_)\_)(__)(__)(__)  (__)  (____)(____)
"""

_CYAN = "\x1b[36m"
_BOLD = "\x1b[1m"
_RESET = "\x1b[0m"


_TAGLINE = "snaffle · gather an academic's complete works"


def render_banner(color: bool = True) -> str:
    """Return the multi-line coloured ASCII banner as a string."""
    art = _ART.strip("\n")
    if color:
        return f"{_BOLD}{_CYAN}{art}{_RESET}\n{_CYAN}{_TAGLINE}{_RESET}\n"
    return f"{art}\n{_TAGLINE}\n"


def print_banner(stream=sys.stderr, color: bool | None = None) -> None:
    """Paint the banner to the given stream (stderr by default)."""
    if color is None:
        color = hasattr(stream, "isatty") and stream.isatty()
    stream.write(render_banner(color=color))
    stream.flush()

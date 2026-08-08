"""Shared document fetching used by download plugins.

Handles a quirk of InvenioRDM/KCWorks file storage: the ``/content`` endpoint
may return a presigned S3 URL *as the response body* instead of streaming the
file, so one extra hop is needed to reach the actual bytes.
"""

from __future__ import annotations

from urllib.parse import quote

# Characters that are already meaningful in a URL and must be left as-is; ``%``
# is included so existing percent-escapes are not double-encoded.
_URL_SAFE = ":/?#[]@!$&'()*+,;=%~"


def encode_url(url: str) -> str:
    """Percent-encode unsafe characters (spaces, etc.) without double-encoding."""
    return quote(url, safe=_URL_SAFE)


def looks_like_pdf(data: bytes) -> bool:
    return data[:5].startswith(b"%PDF")


def _is_bare_url(data: bytes) -> bool:
    if not data or len(data) > 4096:
        return False
    try:
        text = data.decode("ascii").strip()
    except UnicodeDecodeError:
        return False
    return (
        text.startswith(("http://", "https://"))
        and "\n" not in text
        and " " not in text
    )


def fetch_document(http, url: str, _redirected: bool = False) -> bytes | None:
    """Return the bytes at ``url``, following a presigned-URL body one hop.

    Returns ``None`` on any error or non-200 response.
    """
    try:
        response = http.get(encode_url(url))
    except Exception:  # noqa: BLE001 - a dead link must not sink the run
        return None
    if response.status_code != 200 or not response.content:
        return None
    data = response.content
    if not _redirected and _is_bare_url(data):
        return fetch_document(http, data.decode("ascii").strip(), _redirected=True)
    return data

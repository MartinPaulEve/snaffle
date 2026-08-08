"""Kagi Search API client, used for full-text and repository discovery.

Authentication is a ``Authorization: Bot <token>`` header. Result rows have
``t == 0``; ``t == 1`` rows are related-search suggestions and are ignored.
"""

from __future__ import annotations

_ENDPOINT = "https://kagi.com/api/v0/search"


class KagiClient:
    def __init__(self, api_key: str, http=None) -> None:
        self.api_key = api_key
        self.http = http

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Return web results as ``[{"url", "title", "snippet"}, ...]``."""
        try:
            response = self.http.get(
                _ENDPOINT,
                params={"q": query, "limit": limit},
                headers={"Authorization": f"Bot {self.api_key}"},
            )
        except Exception:  # noqa: BLE001 - discovery must never sink a run
            return []
        if response.status_code != 200:
            return []
        rows = response.json().get("data", [])
        results = []
        for row in rows:
            if row.get("t") != 0 or not row.get("url"):
                continue
            results.append(
                {
                    "url": row["url"],
                    "title": row.get("title", ""),
                    "snippet": row.get("snippet", ""),
                }
            )
        return results

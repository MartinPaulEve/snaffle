"""Kagi Search API client, used for full-text and repository discovery.

Uses the v1 search endpoint: a POST with ``Authorization: Bearer <token>`` and a
JSON ``{"query": ...}`` body. Results are returned under ``data.search``.
"""

from __future__ import annotations

_ENDPOINT = "https://kagi.com/api/v1/search"


class KagiClient:
    def __init__(self, api_key: str, http=None) -> None:
        self.api_key = api_key
        self.http = http

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Return web results as ``[{"url", "title", "snippet"}, ...]``."""
        try:
            response = self.http.post(
                _ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"query": query, "limit": limit},
            )
        except Exception:  # noqa: BLE001 - discovery must never sink a run
            return []
        if response.status_code != 200:
            return []
        rows = (response.json().get("data") or {}).get("search") or []
        results = []
        for row in rows:
            url = row.get("url")
            if not url:
                continue
            results.append(
                {
                    "url": url,
                    "title": row.get("title", ""),
                    "snippet": row.get("snippet", ""),
                }
            )
        return results

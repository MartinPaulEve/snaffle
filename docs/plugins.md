# The snaffle plugin system

Everything snaffle does to *find* works or *fetch* copies lives in a plugin.
This document explains the contract and how to add your own.

## Two capabilities, one plugin

A plugin is a class that inherits from `Plugin` and one or both capability
mixins:

- `SearchCapability` — implement `search(academic) -> list[Publication]` to
  build the list of an academic's works.
- `DownloadCapability` — implement `can_download(pub) -> bool` and
  `download(pub, dest) -> DownloadResult` to fetch a copy.

A source that both lists *and* serves works (JSTOR, Project MUSE, several
repositories) inherits from both mixins and implements all the methods. That is
the whole answer to "how does one plugin expose both a search and a download
interface": mix in both, implement both.

```python
from pathlib import Path
from snaffle.models import CopyQuality, DownloadResult, Publication
from snaffle.plugins.base import DownloadCapability, Plugin, SearchCapability


class MyPlugin(Plugin, SearchCapability, DownloadCapability):
    name = "mysource"                 # unique; used by --only / --disable
    description = "My example source"
    priority = 50                     # download order; lower runs earlier

    def search(self, academic: str) -> list[Publication]:
        r = self.ctx.http.get("https://api.example/works", params={"au": academic})
        r.raise_for_status()
        return [Publication(title=..., year=..., sources=["mysource"]), ...]

    def can_download(self, pub: Publication) -> bool:
        return bool(pub.pdf_url) and "mysource" in pub.sources

    def download(self, pub: Publication, dest: Path) -> DownloadResult:
        r = self.ctx.http.get(pub.pdf_url)
        if r.status_code != 200:
            return DownloadResult(success=False, error=f"HTTP {r.status_code}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        return DownloadResult(success=True, path=dest, quality=CopyQuality.FINAL)
```

## Automatic discovery

Drop your module into one of the scanned directories and it is loaded — no
registration:

- `src/snaffle/plugins/public/` — shared, committed to the repository.
- `src/snaffle/plugins/private/` — **gitignored**; your local-only sources.
- Any directory named in `SNAFFLE_PLUGIN_DIR`.

Discovery imports each `*.py` file (names starting with `_` are skipped, so
name shared helpers `_helpers.py`) and registers every class that subclasses
`Plugin` and at least one capability mixin. Plain helper classes are ignored.

## The shared `ServiceContext`

Every plugin receives `self.ctx`, a `ServiceContext` bundling shared facilities
so that common behaviour is centralised, never copy-pasted between plugins:

| Attribute | Purpose |
|-----------|---------|
| `ctx.http` | Pre-configured `httpx.Client` (real user agent, redirects, timeout). **Always** make network calls through this — it is what tests mock. |
| `ctx.secrets` | `SecretStore`; `resolve("op://…")` and `totp("op://…")` via 1Password. |
| `ctx.browser` | Shared headless Selenium browser with human-like fingerprints. |
| `ctx.tor` | Tor SOCKS proxy settings for blocked pages. |
| `ctx.captcha` | 2Captcha client for reCAPTCHA / Turnstile. |
| `ctx.kagi` | Kagi Search client (`search(query)`) for discovering full-text copies and repositories. `None` if no key is configured. |
| `ctx.credentials` | List of `Credential` (institution, username, password/OTP refs, EZproxy base). |
| `ctx.config` | Endpoint URLs and contact emails from the environment. |
| `ctx.logger` | Progress logging (goes to stderr). |

Institutional login (EZproxy + TOTP) is provided centrally via
`snaffle.services.ezproxy`; do not reimplement it in a plugin.

## Download priority and copy quality

Download plugins run in ascending `priority` order and the **first success
blocks the rest** for that work. Set priority to reflect how likely the source
is to hold a final PDF:

- ~20 — legal open-access version of record (e.g. Unpaywall)
- ~40 — authenticated publisher platforms (JSTOR, Project MUSE)
- ~60 — institutional repositories (often accepted manuscripts)
- ~80 — preprint servers (arXiv) — a fallback, not the record

Report the copy you obtained with `DownloadResult.quality`
(`CopyQuality.FINAL`, `PREPRINT`, or `OTHER`) so a final PDF is preferred over a
draft, a Word file, or plain text.

## The `Publication` model

Return `Publication` objects (see `snaffle.models`). Populate what you can:
`title` is required; `doi`/`isbn` power deduplication; `year`, `venue`,
`publisher` drive the filename and citation; `pdf_url` feeds downloads. Always
add your plugin's `name` to `sources`. Books (which often lack DOIs) should set
`type=WorkType.BOOK`.

Deduplication across sources is automatic: works are merged by DOI/ISBN, or by
fuzzy title + year when no identifier is present.

## Author matching (false-positive control)

Search results are filtered before deduplication: a work is dropped if it lists
authors and **none** of them matches the target academic by surname and first
initial (see `snaffle.matching.author_matches`). A work with no listed authors
is kept, on the assumption that the source was searched by author (homepages,
repositories). This is what keeps unrelated same-name-fragment hits out of the
list. Populate `Publication.authors` accurately so this filter can do its job;
do not stuff unrelated names into the list.

## Discovering full text instead of configuring it

Repository locations are **discovered**, not pre-configured. If your plugin
needs to find where something lives (an author's repository, a full-text PDF),
use `ctx.kagi.search(query)` rather than requiring a hard-coded endpoint in the
environment. The `discovery` download plugin is the reference example: it finds
eprints, publisher, and open-repository copies by web search.

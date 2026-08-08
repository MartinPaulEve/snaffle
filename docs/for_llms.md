# Briefing: writing a snaffle plugin

You are an assistant asked to add a new source to **snaffle**, a tool that
gathers an academic's publications and downloads full text. Read this file,
then write the requested plugin. Follow these instructions exactly.

## What you are building

A plugin: a Python class that discovers works (*search*) and/or fetches copies
(*download*). Put it in `src/snaffle/plugins/public/<source>.py` for a shared
source, or `src/snaffle/plugins/private/<source>.py` for a local-only source
(that directory is gitignored). It is discovered automatically — there is no
registration step and nothing else to edit.

## Test-first, always

This project is built test-first. Before writing the plugin:

1. Write `tests/plugins/test_<source>.py`.
2. Test the **pure parser function** by feeding it a captured sample payload
   (JSON/HTML/XML) and asserting the returned `Publication` fields — do not
   assert on internal calls.
3. Test `search()`/`download()` with a mocked transport:
   `httpx.Client(transport=httpx.MockTransport(handler))` wrapped in a
   `ServiceContext`. Never hit the real network in a test.
4. Run `uv run pytest tests/plugins/test_<source>.py` and confirm it FAILS
   before you implement anything.
5. Implement until green. Run `uv run ruff check`.

## The contract

```python
from pathlib import Path
from snaffle.models import CopyQuality, DownloadResult, Publication, WorkType
from snaffle.plugins.base import DownloadCapability, Plugin, SearchCapability


class ExamplePlugin(Plugin, SearchCapability):   # add DownloadCapability if it serves files
    name = "example"            # unique machine name (used by --only/--disable)
    description = "Example catalogue"

    def search(self, academic: str) -> list[Publication]:
        r = self.ctx.http.get(URL, params={"q": academic})
        r.raise_for_status()
        return parse_example(r.json())           # keep parsing in a pure function
```

Rules:

- **All network I/O goes through `self.ctx.http`** (an `httpx.Client`). This is
  what tests mock and where the shared user agent lives.
- **Keep parsing in a module-level pure function** (e.g. `parse_example(payload)`)
  so it can be tested without the network.
- **Always append `self.name` to each `Publication.sources`.**
- For XML, parse with `defusedxml.ElementTree`, never the stdlib parser.
- Name non-plugin helper files/modules with a leading underscore
  (`_helpers.py`) so discovery skips them.

## `Publication` fields

`title` (required), `authors: list[str]`, `year: int|None`, `venue`,
`publisher`, `doi`, `isbn`, `issn`, `url`, `pdf_url`, `type: WorkType`,
`volume`, `issue`, `pages`, `abstract`, `sources: list[str]`.

- Set `doi`/`isbn` whenever available — deduplication keys on them.
- Set `type=WorkType.BOOK` for books; they often have no DOI.
- Set `pdf_url` if you know a direct file link — it feeds downloading.

## Download plugins

Implement `can_download(pub) -> bool` and `download(pub, dest: Path) ->
DownloadResult`. Set the class attribute `priority` (lower runs earlier):
~20 open-access record, ~40 authenticated publishers, ~60 repositories,
~80 preprints. The first plugin to succeed blocks the others for that work, so
order matters. Return `DownloadResult(success=True, path=dest,
quality=...)` where quality is `CopyQuality.FINAL` (version of record),
`PREPRINT`, or `OTHER` (Word/txt/non-final). On failure return
`DownloadResult(success=False, error="…")` — do not raise.

## Shared services on `self.ctx`

`ctx.http`, `ctx.secrets` (`resolve("op://…")`, `totp("op://…")`),
`ctx.browser` (human-like headless Selenium), `ctx.tor`, `ctx.captcha`
(2Captcha), `ctx.credentials` (list of institutional `Credential`s),
`ctx.config` (endpoint URLs / emails), `ctx.logger`. Reuse these; never
reimplement browser launching, login, or secret handling inside a plugin.

## Config values

If your source needs an endpoint or key, read it from `self.ctx.config` (which
is populated from `SNAFFLE_*` environment variables) and document the variable
in `.env.example`. Use `op://` references for anything secret.

## Definition of done

- A red-then-green test file exists under `tests/plugins/`.
- `uv run pytest` is fully green and `uv run ruff check` passes.
- The plugin appears in `uv run snaffle --list-plugins`.
- No secrets are hard-coded; no network calls happen in tests.

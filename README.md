# snaffle

Assemble a complete archive of an academic's published outputs. `snaffle`
discovers an academic's works across many catalogues, downloads full-text
copies (preferring the version of record, settling for a preprint or draft when
that's all that exists), and lays everything out in a tidy, year-organised
folder alongside a Zotero-importable HTML bibliography.

Everything that discovers works or fetches copies is a **plugin**. The two
capacities — *search* (build the list of works) and *download* (fetch a copy) —
are plug-in interfaces, and a single plugin may expose one or both. New sources
are added simply by dropping a module into a plugin directory; they are picked
up automatically.

## Install

```bash
uv sync --extra browser        # omit --extra browser if you don't need Selenium
```

## Usage

```bash
# Use every available plugin (the default):
uv run snaffle "Ada Lovelace"

# Only certain plugins, or all-but-some:
uv run snaffle "Ada Lovelace" --only crossref --only openalex
uv run snaffle "Ada Lovelace" --disable jstor

# Build the publication list without downloading anything:
uv run snaffle "Ada Lovelace" --no-download

# See what's installed:
uv run snaffle --list-plugins
```

The banner and all progress reporting go to **stderr**, so you can redirect the
run log to a file while keeping stdout clean:

```bash
uv run snaffle "Ada Lovelace" 2> run.log
```

## Output layout

```
output/
└── Ada Lovelace/
    ├── bibliography.html         # every work found, formatted + COinS for Zotero
    ├── failures.txt              # works whose full text could not be retrieved
    ├── 2026/
    │   └── Ada Lovelace - Journal of Software - 2026 - On the Origin of Testing.pdf
    └── 2019/
        └── Ada Lovelace - Compute Quarterly - 2019 - Notes on Analytical Engines.pdf
```

Re-running for the same academic rebuilds the publication list from scratch
(all search plugins run again) but downloads **incrementally**: an item whose
file already exists on disk is not fetched again.

## Secrets and credentials

Any configuration value written as `op://vault/item/field` is resolved at
runtime through the [1Password CLI](https://developer.1password.com/docs/cli/)
(`op`). TOTP two-factor codes are generated with `op item get --otp`. You can
supply **multiple** institutional credentials (e.g. Birkbeck and Michigan
State); each unlocks different journal access. See `.env.example`.

## Documentation

- `docs/plugins.md` — how the plugin system works and how to write one.
- `docs/for_llms.md` — a compact briefing so an AI assistant can author a new
  plugin from a single instruction.

## Development

```bash
uv run pytest          # run the test suite
uv run ruff check      # lint
```

Built test-first: every behaviour has a test that failed before its
implementation existed.

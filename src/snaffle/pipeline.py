"""Orchestrates search, dedupe, and prioritised download for one academic."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from snaffle.bibliography import write_bibliography, write_failures
from snaffle.dedupe import deduplicate
from snaffle.matching import author_matches
from snaffle.models import DownloadResult, Publication
from snaffle.output import already_downloaded, publication_path


@dataclass
class RunReport:
    author: str
    found: list[Publication] = field(default_factory=list)
    downloaded: list[Publication] = field(default_factory=list)
    failed: list[Publication] = field(default_factory=list)


def _log(logger, level, msg):
    (logger or logging.getLogger("snaffle")).log(level, msg)


def run_search(search_plugins: list, academic: str, logger=None) -> list[Publication]:
    """Run every search plugin, collect and deduplicate the results."""
    collected: list[Publication] = []
    for plugin in search_plugins:
        name = getattr(plugin, "name", plugin.__class__.__name__)
        try:
            results = plugin.search(academic)
        except Exception as exc:  # noqa: BLE001 - one plugin must not sink the run
            _log(logger, logging.WARNING, f"search plugin '{name}' failed: {exc}")
            continue
        kept = [p for p in results if author_matches(academic, p.authors)]
        dropped = len(results) - len(kept)
        msg = f"search plugin '{name}' found {len(results)} item(s)"
        if dropped:
            msg += f", dropped {dropped} as author mismatch"
        _log(logger, logging.INFO, msg)
        collected.extend(kept)
    return deduplicate(collected)


def download_one(
    download_plugins: list,
    pub: Publication,
    output_dir: Path,
    author: str,
    logger=None,
) -> DownloadResult:
    """Try download plugins in priority order; first success wins for this work."""
    last_error = "no download plugin could handle this item"
    for plugin in download_plugins:
        name = getattr(plugin, "name", plugin.__class__.__name__)
        try:
            if not plugin.can_download(pub):
                continue
        except Exception as exc:  # noqa: BLE001
            _log(logger, logging.WARNING, f"'{name}' can_download error: {exc}")
            continue

        ext_hint = "pdf"
        dest = publication_path(output_dir, author, pub, ext_hint)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = plugin.download(pub, dest)
        except Exception as exc:  # noqa: BLE001
            _log(logger, logging.WARNING, f"'{name}' download error for '{pub.title}': {exc}")
            last_error = str(exc)
            continue

        if result and result.success:
            _log(logger, logging.INFO, f"downloaded '{pub.title}' via '{name}'")
            return result
        last_error = (result.error if result else None) or last_error
        _log(logger, logging.INFO, f"'{name}' had no copy of '{pub.title}'")

    return DownloadResult(success=False, error=last_error)


def run(
    academic: str,
    output_dir: Path,
    search_plugins: list,
    download_plugins: list,
    logger=None,
    style: str = "chicago",
    download: bool = True,
) -> RunReport:
    """Full pipeline: fresh search each run, incremental download."""
    output_dir = Path(output_dir)
    report = RunReport(author=academic)
    report.found = run_search(search_plugins, academic, logger)
    _log(logger, logging.INFO, f"{len(report.found)} unique publication(s) after dedupe")

    if download:
        for pub in report.found:
            if already_downloaded(output_dir, academic, pub):
                _log(logger, logging.INFO, f"already have '{pub.title}', skipping")
                report.downloaded.append(pub)
                continue
            result = download_one(download_plugins, pub, output_dir, academic, logger)
            if result.success:
                report.downloaded.append(pub)
            else:
                _log(logger, logging.WARNING, f"could not retrieve '{pub.title}': {result.error}")
                report.failed.append(pub)

    write_bibliography(output_dir, academic, report.found, style)
    write_failures(output_dir, academic, report.failed)
    return report

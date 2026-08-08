"""Core data models shared by the pipeline and all plugins."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path


class WorkType(enum.StrEnum):
    ARTICLE = "article"
    BOOK = "book"
    CHAPTER = "chapter"
    THESIS = "thesis"
    REPORT = "report"
    DATASET = "dataset"
    OTHER = "other"


class CopyQuality(enum.IntEnum):
    """Quality of a retrieved copy. Higher is better."""

    OTHER = 1  # e.g. plain text, Word file
    PREPRINT = 2  # author manuscript / preprint PDF
    FINAL = 3  # publisher's version of record


@dataclass
class Publication:
    """A single academic output, merged from one or more sources."""

    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str | None = None  # journal, book series, or conference
    publisher: str | None = None
    doi: str | None = None
    isbn: str | None = None
    issn: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    type: WorkType = WorkType.ARTICLE
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    abstract: str | None = None
    sources: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


@dataclass
class DownloadResult:
    """Outcome of a single plugin's attempt to fetch a copy."""

    success: bool
    path: Path | None = None
    quality: CopyQuality = CopyQuality.FINAL
    error: str | None = None


@dataclass
class Credential:
    """One set of institutional credentials (e.g. Birkbeck, MSU)."""

    institution: str
    username: str
    password_ref: str  # op:// reference or literal
    otp_ref: str | None = None  # op:// item reference for TOTP
    ezproxy_base: str | None = None

"""Turn publications and downloaded copies into the on-disk archive layout."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from snaffle.models import Publication

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WS = re.compile(r"\s+")

#: Extensions we recognise as an existing copy, best first.
KNOWN_EXTENSIONS = ("pdf", "docx", "doc", "txt")


def sanitize_component(text: str) -> str:
    """Make a string safe to use as a single path component."""
    cleaned = _ILLEGAL.sub(" ", text or "")
    return _WS.sub(" ", cleaned).strip()


def _venue_or_publisher(pub: Publication) -> str:
    return pub.venue or pub.publisher or "Unknown"


def build_filename(pub: Publication, author: str, extension: str = "pdf") -> str:
    """`Author - Venue - Year - Title.pdf` with sanitised components."""
    parts = [
        sanitize_component(author),
        sanitize_component(_venue_or_publisher(pub)),
        str(pub.year) if pub.year else "n.d.",
        sanitize_component(pub.title),
    ]
    stem = " - ".join(parts)
    return f"{stem}.{extension.lstrip('.')}"


def _year_dir(output_dir: Path, author: str, pub: Publication) -> Path:
    year = str(pub.year) if pub.year else "undated"
    return Path(output_dir) / sanitize_component(author) / year


def publication_path(output_dir: Path, author: str, pub: Publication, extension: str) -> Path:
    """Full path `<output>/<author>/<year>/<filename>` for a publication copy."""
    return _year_dir(output_dir, author, pub) / build_filename(pub, author, extension)


def already_downloaded(output_dir: Path, author: str, pub: Publication) -> bool:
    """True if any copy of this publication already exists on disk."""
    year_dir = _year_dir(output_dir, author, pub)
    if not year_dir.is_dir():
        return False
    stem = build_filename(pub, author, "x").rsplit(".", 1)[0]
    return any(f.stem == stem for f in year_dir.iterdir() if f.is_file())


def ensure_author_dir(output_dir: Path, author: str) -> Path:
    path = Path(output_dir) / sanitize_component(author)
    path.mkdir(parents=True, exist_ok=True)
    return path


def nuke_author_dir(output_dir: Path, author: str) -> bool:
    """Delete the academic's output directory. True if one existed."""
    path = Path(output_dir) / sanitize_component(author)
    if path.is_dir():
        shutil.rmtree(path)
        return True
    return False

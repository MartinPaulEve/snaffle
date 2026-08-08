"""Persist the deduplicated publication list so search and download can run apart.

``search`` writes ``publications.json`` into the academic's directory; a later
``download`` reads it back, so the two activities need not run together.
"""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

from snaffle.models import Publication, WorkType
from snaffle.output import ensure_author_dir, sanitize_component

MANIFEST_NAME = "publications.json"


def _author_dir(output_dir, author: str) -> Path:
    return Path(output_dir) / sanitize_component(author)


def publication_to_dict(pub: Publication) -> dict:
    data = {f.name: getattr(pub, f.name) for f in fields(pub)}
    data["type"] = pub.type.value  # store the enum as its string value
    return data


def publication_from_dict(data: dict) -> Publication:
    known = {f.name for f in fields(Publication)}
    kwargs = {k: v for k, v in data.items() if k in known}
    if "type" in kwargs:
        kwargs["type"] = WorkType(kwargs["type"])
    return Publication(**kwargs)


def write_manifest(output_dir, author: str, pubs: list[Publication]) -> Path:
    author_dir = ensure_author_dir(output_dir, author)
    path = author_dir / MANIFEST_NAME
    payload = {"academic": author, "publications": [publication_to_dict(p) for p in pubs]}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def read_manifest(output_dir, author: str) -> list[Publication] | None:
    path = _author_dir(output_dir, author) / MANIFEST_NAME
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return [publication_from_dict(d) for d in data.get("publications", [])]

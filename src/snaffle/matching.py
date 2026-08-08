"""Author-name matching, used to reject false-positive search hits."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_NON_NAME = re.compile(r"[^\w\s,]")


def normalize_name(name: str) -> str:
    """Lowercase, strip accents and punctuation, collapse whitespace."""
    decomposed = unicodedata.normalize("NFKD", name or "")
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    cleaned = _NON_NAME.sub(" ", ascii_only.lower())
    return " ".join(cleaned.split())


@dataclass
class ParsedName:
    surname: str
    given_initials: list[str]
    given_names: list[str]


def parse_name(name: str) -> ParsedName:
    """Split a personal name into a surname and ordered given-name initials.

    Handles both ``Given Family`` and ``Family, Given`` orderings.
    """
    raw = name or ""
    if "," in raw:
        surname_part, _, given_part = raw.partition(",")
        surname = normalize_name(surname_part)
        given = normalize_name(given_part)
    else:
        tokens = normalize_name(raw).split()
        surname = tokens[-1] if tokens else ""
        given = " ".join(tokens[:-1])
    given_names = [tok for tok in given.split() if tok]
    initials = [tok[0] for tok in given_names]
    # A multi-word surname (e.g. "van Dijk") keeps only the final token as the
    # comparison key; that is enough for our reject/keep decision.
    surname = surname.split()[-1] if surname.split() else surname
    return ParsedName(surname=surname, given_initials=initials, given_names=given_names)


def _one_matches(target: ParsedName, candidate: ParsedName) -> bool:
    if not target.surname or target.surname != candidate.surname:
        return False
    # Surnames agree. If both sides name a first given initial, they must agree
    # — this is what separates "Martin Eve" from "Sarah Eve".
    if target.given_initials and candidate.given_initials:
        return target.given_initials[0] == candidate.given_initials[0]
    return True


def author_matches(target: str, authors: list[str]) -> bool:
    """True if ``target`` is plausibly among ``authors``.

    An empty author list returns True (the source is trusted to have searched
    by author). A populated list with no surname-and-initial match returns
    False, which is how obvious false positives are dropped.
    """
    if not authors:
        return True
    parsed_target = parse_name(target)
    return any(_one_matches(parsed_target, parse_name(a)) for a in authors)

"""Load configuration and institutional credentials from the environment."""

from __future__ import annotations

from pathlib import Path

from snaffle.models import Credential

_PREFIX = "SNAFFLE_CRED_"
_SUFFIXES = ("_USER", "_PASS", "_OTP", "_EZPROXY")


def _institution_from_key(key: str) -> str | None:
    if not key.startswith(_PREFIX):
        return None
    remainder = key[len(_PREFIX):]
    for suffix in _SUFFIXES:
        if remainder.endswith(suffix):
            return remainder[: -len(suffix)]
    return None


def parse_credentials(env: dict) -> list[Credential]:
    """Parse SNAFFLE_CRED_<INST>_* env vars into Credential objects.

    Multiple institutions are supported, e.g. SNAFFLE_CRED_BIRKBECK_USER and
    SNAFFLE_CRED_MSU_USER produce two separate credentials.
    """
    institutions: dict[str, dict] = {}
    for key, value in env.items():
        inst = _institution_from_key(key)
        if inst is None:
            continue
        field = key[len(_PREFIX) + len(inst):]
        institutions.setdefault(inst, {})[field] = value

    creds = []
    for inst, fields in institutions.items():
        if "_USER" not in fields:
            continue
        creds.append(
            Credential(
                institution=inst,
                username=fields.get("_USER", ""),
                password_ref=fields.get("_PASS", ""),
                otp_ref=fields.get("_OTP"),
                ezproxy_base=fields.get("_EZPROXY"),
            )
        )
    return creds


def plugin_dirs(env: dict) -> list[Path]:
    """Return the public and (if present) private plugin directories to scan."""
    base = Path(__file__).parent / "plugins"
    dirs = [base / "public"]
    private = base / "private"
    if private.is_dir():
        dirs.append(private)
    override = env.get("SNAFFLE_PLUGIN_DIR")
    if override:
        dirs.append(Path(override))
    return dirs

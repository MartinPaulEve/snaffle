"""Secret resolution via the 1Password CLI (``op``).

Any config value of the form ``op://vault/item/field`` is resolved by shelling
out to ``op read``. TOTP codes use ``op item get --otp``.
"""

from __future__ import annotations

import subprocess


def _default_runner(args: list[str]) -> str:
    return subprocess.run(  # noqa: S603
        args, capture_output=True, text=True, check=True
    ).stdout


class SecretStore:
    def __init__(self, runner=None) -> None:
        # runner(args: list[str]) -> str lets tests inject a fake `op`.
        self._runner = runner or _default_runner

    def is_reference(self, value: str) -> bool:
        """True if the value is an ``op://`` reference that must be resolved."""
        return isinstance(value, str) and value.startswith("op://")

    def resolve(self, value: str) -> str:
        """Resolve an ``op://`` reference, or return a literal unchanged."""
        if not self.is_reference(value):
            return value
        return self._runner(["op", "read", value]).strip()

    def totp(self, item_ref: str) -> str:
        """Return a current TOTP code for a 1Password item."""
        return self._runner(["op", "item", "get", item_ref, "--otp"]).strip()

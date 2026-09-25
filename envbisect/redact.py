"""Conservative presentation helpers for likely credentials."""

from __future__ import annotations

import re
from collections.abc import Iterable

_SECRET_PARTS = frozenset(
    {
        "SECRET",
        "TOKEN",
        "PASSWORD",
        "PASSWD",
        "PRIVATE",
        "CREDENTIAL",
        "CREDENTIALS",
        "AUTH",
        "AUTHORIZATION",
        "COOKIE",
        "SESSION",
        "APIKEY",
        "ACCESSKEY",
        "SECRETKEY",
        "PRIVATEKEY",
    }
)
_CONNECTION_NAMES = frozenset(
    {
        "DATABASE_URL",
        "DATABASE_URI",
        "DB_URL",
        "DB_URI",
        "DATABASE_DSN",
        "DB_DSN",
        "CONNECTION_STRING",
    }
)


def is_likely_secret(key: str) -> bool:
    """Match credential words without treating e.g. KEYBOARD as a secret."""

    upper = key.upper()
    if upper in _CONNECTION_NAMES:
        return True
    parts = [part for part in re.split(r"[^A-Z0-9]+", upper) if part]
    return any(part in _SECRET_PARTS or part == "KEY" for part in parts)


def format_value(key: str, value: str | None, present: bool) -> str:
    """Return a printable value that preserves absent versus empty."""

    if not present:
        return "[ABSENT]"
    if is_likely_secret(key):
        return "[REDACTED]"
    if value is None:
        raise ValueError("A present environment value cannot be None")
    return '""' if value == "" else value


def redact_text(text: str, secrets: Iterable[str]) -> str:
    """Remove exact secret values from optional command output before display."""

    for secret in sorted({secret for secret in secrets if secret}, key=len, reverse=True):
        text = text.replace(secret, "[REDACTED]")
    return text

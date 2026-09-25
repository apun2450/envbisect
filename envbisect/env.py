"""Read dotenv snapshots without expanding values or changing process state."""

from __future__ import annotations

import re
from pathlib import Path

_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_ASSIGNMENT = re.compile(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\Z")


class EnvParseError(ValueError):
    """A dotenv line cannot be interpreted safely."""


def _quoted_value(raw: str, quote: str, line_number: int) -> str:
    chars: list[str] = []
    index = 1
    while index < len(raw):
        char = raw[index]
        if char == quote:
            if raw[index + 1 :].strip() and not raw[index + 1 :].lstrip().startswith("#"):
                raise EnvParseError(f"Invalid content after quoted value on line {line_number}")
            return "".join(chars)
        if char == "\\" and quote == '"' and index + 1 < len(raw):
            next_char = raw[index + 1]
            escapes = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}
            if next_char in escapes:
                chars.append(escapes[next_char])
                index += 2
                continue
        chars.append(char)
        index += 1
    raise EnvParseError(f"Unterminated quoted value on line {line_number}")


def _unquoted_value(raw: str) -> str:
    # A # starts an inline comment only after whitespace. URL fragments and
    # literal hashes in values therefore survive unchanged.
    match = re.search(r"\s+#", raw)
    if match is not None:
        raw = raw[: match.start()]
    return raw.rstrip()


def parse_env_file(path: str | Path) -> dict[str, str]:
    """Parse a UTF-8 dotenv file as a complete environment snapshot.

    Variable expansion and references to the host environment are intentionally
    unsupported; experiments must use the literal values from the two files.
    Values are never included in parse-error messages.
    """

    result: dict[str, str] = {}
    with Path(path).open("r", encoding="utf-8-sig") as source:
        for line_number, line in enumerate(source, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            match = _ASSIGNMENT.fullmatch(line.rstrip("\r\n"))
            if match is None:
                raise EnvParseError(f"Invalid environment assignment on line {line_number}")
            key, raw = match.groups()
            if not _KEY.fullmatch(key):
                raise EnvParseError(f"Invalid environment key on line {line_number}")
            if raw.startswith(("'", '"')):
                value = _quoted_value(raw, raw[0], line_number)
            else:
                value = _unquoted_value(raw)
            result[key] = value
    return result

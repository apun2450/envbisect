from __future__ import annotations

import pytest

from envbisect.redact import format_value, redact_text


@pytest.mark.parametrize(
    "name",
    [
        "GITHUB_TOKEN",
        "OPENAI_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "PASSWORD",
        "DB_PASSWD",
        "PRIVATE_KEY",
        "AUTH_TOKEN",
        "SESSION_COOKIE",
        "DATABASE_URL",
    ],
)
def test_likely_secrets_are_masked(name: str) -> None:
    assert "literal-secret" not in format_value(name, "literal-secret", True)


def test_ordinary_value_and_absence_are_distinguishable() -> None:
    assert format_value("FEATURE_CACHE", "1", True) == "1"
    assert format_value("FEATURE_CACHE", "", True) != format_value("FEATURE_CACHE", None, False)


def test_redact_text_removes_known_secret_literals() -> None:
    output = redact_text("token=literal-secret; other=visible", ["literal-secret"])
    assert "literal-secret" not in output
    assert "visible" in output

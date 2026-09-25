from __future__ import annotations

from pathlib import Path

from envbisect.env import parse_env_file


def test_parse_dotenv_values_quotes_comments_and_whitespace(tmp_path: Path) -> None:
    path = tmp_path / "sample.env"
    path.write_text(
        "# whole-line comment\n"
        "\n"
        "  PLAIN = hello  \n"
        "EMPTY=\n"
        'DOUBLE="two words"\n'
        "SINGLE='three words'\n"
        "URL=https://example.test/path#fragment\n",
        encoding="utf-8",
    )

    assert parse_env_file(path) == {
        "PLAIN": "hello",
        "EMPTY": "",
        "DOUBLE": "two words",
        "SINGLE": "three words",
        "URL": "https://example.test/path#fragment",
    }


def test_parsing_does_not_change_source_file(tmp_path: Path) -> None:
    path = tmp_path / "original.env"
    content = "# keep this comment\nSECRET_TOKEN=unmodified-value\n"
    path.write_text(content, encoding="utf-8")

    assert parse_env_file(path)["SECRET_TOKEN"] == "unmodified-value"
    assert path.read_text(encoding="utf-8") == content

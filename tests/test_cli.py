from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def diagnose(
    tmp_path: Path,
    passing: str,
    failing: str,
    program: str,
    *options: str,
) -> subprocess.CompletedProcess[str]:
    pass_file = tmp_path / "pass.env"
    fail_file = tmp_path / "fail.env"
    pass_file.write_text(passing, encoding="utf-8")
    fail_file.write_text(failing, encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "envbisect",
            "diagnose",
            "--pass",
            str(pass_file),
            "--fail",
            str(fail_file),
            *options,
            "--",
            sys.executable,
            "-c",
            program,
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
        check=False,
    )


def output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def test_cli_isolates_a_removed_variable(tmp_path: Path) -> None:
    result = diagnose(
        tmp_path,
        "REQUIRED=present\nNOISE=old\n",
        "NOISE=new\n",
        "import os,sys; sys.exit('REQUIRED' not in os.environ)",
        "--no-color",
    )

    assert result.returncode == 0, output(result)
    assert "REQUIRED" in output(result)
    assert "Verification" in output(result)
    assert re.search(r"Runs:\s*\d+", output(result))


def test_cli_distinguishes_empty_from_absent(tmp_path: Path) -> None:
    result = diagnose(
        tmp_path,
        "FOO=\n",
        "",
        "import os,sys; sys.exit('FOO' not in os.environ)",
        "--no-color",
    )

    assert result.returncode == 0, output(result)
    assert "FOO" in output(result)


@pytest.mark.parametrize("program", ["import sys; sys.exit(0)", "import sys; sys.exit(1)"])
def test_cli_rejects_baseline_mismatch(tmp_path: Path, program: str) -> None:
    result = diagnose(tmp_path, "X=0\n", "X=1\n", program, "--no-color")

    assert result.returncode == 2, output(result)
    assert "PASS" in output(result)
    assert "FAIL" in output(result)


def test_cli_rejects_reversed_baselines(tmp_path: Path) -> None:
    result = diagnose(
        tmp_path,
        "X=1\n",
        "X=0\n",
        "import os,sys; sys.exit(os.environ['X'] == '1')",
        "--no-color",
    )

    assert result.returncode == 2, output(result)


def test_cli_explains_no_differences(tmp_path: Path) -> None:
    result = diagnose(
        tmp_path,
        "SAME=value\n",
        "SAME=value\n",
        "import sys; sys.exit(0)",
        "--no-color",
    )

    assert result.returncode == 3, output(result)
    assert "differ" in output(result).lower()


def test_cli_does_not_claim_causality_for_controlled_flakiness(tmp_path: Path) -> None:
    counter = tmp_path / "counter.txt"
    program = (
        "from pathlib import Path; import sys; "
        f"p=Path({str(counter)!r}); "
        "n=int(p.read_text()) if p.exists() else 0; "
        "p.write_text(str(n+1)); sys.exit(n % 2)"
    )
    result = diagnose(
        tmp_path,
        "MODE=pass\n",
        "MODE=fail\n",
        program,
        "--repeats",
        "3",
        "--no-color",
    )

    assert result.returncode == 4, output(result)
    assert "flak" in output(result).lower() or "nondetermin" in output(result).lower()
    assert "minimal failure-inducing set" not in output(result).lower()


@pytest.mark.parametrize("mode", ["default", "verbose"])
def test_cli_never_displays_secret_values(tmp_path: Path, mode: str) -> None:
    old_value = "old-sensitive-value"
    new_value = "super-secret-value"
    program = (
        "import os,sys; token=os.environ['GITHUB_TOKEN']; "
        "print(token); print(token, file=sys.stderr); "
        f"sys.exit(token == {new_value!r})"
    )
    options = ("--verbose", "--no-color") if mode == "verbose" else ("--no-color",)
    result = diagnose(
        tmp_path,
        f"GITHUB_TOKEN={old_value}\n",
        f"GITHUB_TOKEN={new_value}\n",
        program,
        *options,
    )

    assert result.returncode == 0, output(result)
    assert "GITHUB_TOKEN" in output(result)
    assert old_value not in output(result)
    assert new_value not in output(result)
    assert "REDACTED" in output(result).upper()
    assert (tmp_path / "pass.env").read_text(encoding="utf-8") == (f"GITHUB_TOKEN={old_value}\n")


def test_cli_reports_timeout_distinctly(tmp_path: Path) -> None:
    result = diagnose(
        tmp_path,
        "MODE=pass\n",
        "MODE=fail\n",
        "import time; time.sleep(0.5)",
        "--timeout",
        "0.05",
        "--no-color",
    )

    assert result.returncode != 0, output(result)
    assert "TIMEOUT" in output(result).upper()


def test_readme_demo_end_to_end() -> None:
    demo = PROJECT_ROOT / "examples" / "demo"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "envbisect",
            "diagnose",
            "--pass",
            str(demo / "pass.env"),
            "--fail",
            str(demo / "fail.env"),
            "--no-color",
            "--",
            sys.executable,
            str(demo / "app.py"),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, output(result)
    assert "TZ" in output(result)
    assert "FEATURE_CACHE" in output(result)
    assert "Verification" in output(result)


def test_cli_does_not_claim_a_minimum_when_only_candidates_are_flaky(tmp_path: Path) -> None:
    counter = tmp_path / "candidate-counter.txt"
    program = (
        "from pathlib import Path; import os,sys; "
        "a=os.environ['A']; b=os.environ['B']; "
        f"p=Path({str(counter)!r}); "
        "n=int(p.read_text()) if p.exists() else 0; "
        "mixed=a != b; "
        "p.write_text(str(n+1)) if mixed else None; "
        "sys.exit(n % 2 if mixed else a == '1')"
    )
    result = diagnose(
        tmp_path,
        "A=0\nB=0\n",
        "A=1\nB=1\n",
        program,
        "--repeats",
        "3",
        "--no-color",
    )

    assert result.returncode == 4, output(result)
    assert "uncertain candidate" in output(result).lower()
    assert "FLAKY" in output(result)
    assert "minimal failure-inducing set" not in output(result).lower()


def test_cli_rejects_candidate_that_fails_reverse_verification(tmp_path: Path) -> None:
    result = diagnose(
        tmp_path,
        "A=0\nB=0\n",
        "A=1\nB=1\n",
        "import os,sys; sys.exit(os.environ['A'] == '1' or os.environ['B'] == '1')",
        "--no-color",
    )

    assert result.returncode == 4, output(result)
    assert "Verification did not establish" in output(result)
    assert "PASS + changes" in output(result)
    assert "FAIL - changes" in output(result)
    assert "FAIL 5/5" in output(result)
    assert "Minimal failure-inducing set" not in output(result)


def test_cli_quiet_prints_only_identified_keys(tmp_path: Path) -> None:
    result = diagnose(
        tmp_path,
        "CULPRIT=0\nNOISE=old\n",
        "CULPRIT=1\nNOISE=new\n",
        "import os,sys; sys.exit(os.environ['CULPRIT'] == '1')",
        "--quiet",
        "--no-color",
    )

    assert result.returncode == 0, output(result)
    assert result.stdout.splitlines() == ["CULPRIT"]
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("option", "value"),
    [("--repeats", "0"), ("--timeout", "0"), ("--timeout", "nan")],
)
def test_cli_rejects_invalid_execution_options(tmp_path: Path, option: str, value: str) -> None:
    result = diagnose(
        tmp_path,
        "X=0\n",
        "X=1\n",
        "import sys; sys.exit(0)",
        option,
        value,
    )

    assert result.returncode == 1, output(result)
    assert "error" in output(result).lower()


def test_cli_reports_timeout_during_minimization(tmp_path: Path) -> None:
    program = (
        "import os,sys,time; a=os.environ['A']; b=os.environ['B']; "
        "time.sleep(1.5) if a != b else None; "
        "sys.exit(a == '1' and b == '1')"
    )
    result = diagnose(
        tmp_path,
        "A=0\nB=0\n",
        "A=1\nB=1\n",
        program,
        "--timeout",
        "0.5",
        "--no-color",
    )

    assert result.returncode == 4, output(result)
    assert "uncertain candidate" in output(result).lower()
    assert "TIMEOUT" in output(result)
    assert "Minimal failure-inducing set" not in output(result)

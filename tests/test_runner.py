from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

from envbisect.models import Status
from envbisect.runner import CommandRunner


def test_runner_captures_exit_code_output_and_duration() -> None:
    command = [
        sys.executable,
        "-c",
        "import os,sys; print(os.environ['CHECK']); print('detail', file=sys.stderr); sys.exit(7)",
    ]

    result = CommandRunner(command, timeout=3).run({"CHECK": "injected"})

    assert result.status is Status.FAIL
    assert result.exit_code == 7
    assert "injected" in result.stdout
    assert "detail" in result.stderr
    assert result.duration >= 0


def test_runner_timeout_is_distinct_from_nonzero_exit() -> None:
    command = [sys.executable, "-c", "import time; time.sleep(1)"]

    result = CommandRunner(command, timeout=0.05).run({"UNRELATED": "value"})

    assert result.status is Status.TIMEOUT
    assert result.duration >= 0.05


@pytest.mark.skipif(os.name != "nt", reason="Windows command launchers use PATHEXT")
def test_runner_resolves_cmd_launcher_from_child_path(tmp_path: Path) -> None:
    launcher = tmp_path / "envbisect-test-launcher.cmd"
    launcher.write_text("@echo off\r\necho launcher-ok\r\n", encoding="ascii")
    environment = dict(os.environ)
    environment["PATH"] = str(tmp_path) + os.pathsep + environment.get("PATH", "")

    result = CommandRunner(["envbisect-test-launcher"], timeout=3).run(environment)

    assert result.status is Status.PASS
    assert result.exit_code == 0
    assert "launcher-ok" in result.stdout


def test_runner_timeout_stops_child_processes(tmp_path: Path) -> None:
    marker = tmp_path / "orphaned-child.txt"
    child = (
        "import time; from pathlib import Path; "
        f"time.sleep(0.8); Path({str(marker)!r}).write_text('orphaned')"
    )
    parent = (
        "import subprocess,sys,time; "
        f"subprocess.Popen([sys.executable, '-c', {child!r}]); "
        "time.sleep(2)"
    )

    result = CommandRunner([sys.executable, "-c", parent], timeout=0.3).run(dict(os.environ))
    time.sleep(1)

    assert result.status is Status.TIMEOUT
    assert not marker.exists()

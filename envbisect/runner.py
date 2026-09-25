"""Execute one controlled command trial under an explicit environment."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from collections.abc import Mapping, Sequence

from .models import RunResult, Status


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def _child_environment(environment: Mapping[str, str]) -> dict[str, str]:
    if os.name != "nt":
        return dict(environment)
    # CreateProcess treats names case insensitively, so never pass PATH and Path
    # or other casing duplicates in the same environment block.
    deduplicated: dict[str, tuple[str, str]] = {}
    for key, value in environment.items():
        deduplicated[key.casefold()] = (key, value)
    return {key: value for key, value in deduplicated.values()}


def _resolved_command(command: list[str], environment: Mapping[str, str]) -> list[str]:
    if os.name != "nt":
        return command
    # CreateProcess does not search PATHEXT for bare names such as npm.
    # which resolves npm.CMD while keeping shell=False for the subprocess.
    path = next((value for key, value in environment.items() if key.casefold() == "path"), "")
    executable = shutil.which(command[0], path=path)
    return [executable, *command[1:]] if executable else command


def _stop_process_tree(process: subprocess.Popen[str]) -> None:
    """Stop descendants as well as the direct command after a timeout."""

    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass


class CommandRunner:
    """Runs one trial; higher layers decide how many repeats are needed."""

    def __init__(self, command: Sequence[str], timeout: float | None = None) -> None:
        if not command:
            raise ValueError("A command is required")
        if timeout is not None and timeout <= 0:
            raise ValueError("Timeout must be greater than zero")
        self.command = list(command)
        self.timeout = timeout

    def run(self, env: Mapping[str, str]) -> RunResult:
        started = time.monotonic()
        try:
            child_env = _child_environment(env)
            process = subprocess.Popen(
                _resolved_command(self.command, child_env),
                env=child_env,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                start_new_session=os.name != "nt",
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
            stdout, stderr = process.communicate(timeout=self.timeout)
        except subprocess.TimeoutExpired as error:
            _stop_process_tree(process)
            try:
                stdout, stderr = process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                stdout, stderr = _as_text(error.stdout), _as_text(error.stderr)
                if process.stdout is not None:
                    process.stdout.close()
                if process.stderr is not None:
                    process.stderr.close()
            return RunResult(
                status=Status.TIMEOUT,
                exit_code=None,
                duration=time.monotonic() - started,
                stdout=stdout,
                stderr=stderr,
            )
        except (OSError, UnicodeError, ValueError) as error:
            # Exception strings can contain command arguments and values; the
            # report should not accidentally expose a credential passed there.
            return RunResult(
                status=Status.ERROR,
                exit_code=None,
                duration=time.monotonic() - started,
                stdout="",
                stderr=f"Could not execute command ({type(error).__name__})",
            )
        return RunResult(
            status=Status.PASS if process.returncode == 0 else Status.FAIL,
            exit_code=process.returncode,
            duration=time.monotonic() - started,
            stdout=stdout,
            stderr=stderr,
        )

"""Readable terminal reporting with credential-safe value display."""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Iterable
from typing import TextIO

from .diagnose import BatchResult, DiagnosisProblem, DiagnosisResult
from .models import Change, Status
from .redact import format_value, redact_text

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _safe_display(value: str) -> str:
    """Prevent a dotenv value from creating terminal control sequences."""

    if _CONTROL.search(value):
        return value.encode("unicode_escape").decode("ascii")
    return value


def _counts(batch: BatchResult) -> str:
    return ", ".join(
        f"{status.value} {batch.count(status)}/{len(batch.runs)}"
        for status in Status
        if batch.count(status)
    )


class ConsoleReporter:
    """Progress and final output for interactive and CI terminals."""

    def __init__(
        self,
        *,
        quiet: bool = False,
        verbose: bool = False,
        no_color: bool = False,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
    ) -> None:
        self.quiet = quiet
        self.verbose = verbose and not quiet
        self.stdout = sys.stdout if stdout is None else stdout
        self.stderr = sys.stderr if stderr is None else stderr
        self.color = bool(not no_color and "NO_COLOR" not in os.environ and self.stdout.isatty())
        self.secrets: set[str] = set()

    def _line(self, message: str = "", *, error: bool = False) -> None:
        stream = self.stderr if error else self.stdout
        encoding = getattr(stream, "encoding", None) or "utf-8"
        try:
            message.encode(encoding)
        except UnicodeEncodeError:
            # Redirected Windows consoles commonly use cp1252. Keep their
            # output readable without requiring a UTF-8 locale switch.
            message = message.replace("→", "->").replace("✓", "+")
            message = message.encode(encoding, errors="backslashreplace").decode(encoding)
        print(message, file=stream, flush=True)

    def _status(self, status: Status) -> str:
        if not self.color:
            return status.value
        color = {
            Status.PASS: "\x1b[32m",
            Status.FAIL: "\x1b[31m",
            Status.FLAKY: "\x1b[33m",
            Status.TIMEOUT: "\x1b[33m",
            Status.ERROR: "\x1b[31m",
        }[status]
        return f"{color}{status.value}\x1b[0m"

    def set_secrets(self, values: set[str]) -> None:
        self.secrets = values

    def checking_baselines(self) -> None:
        if not self.quiet:
            self._line("EnvBisect")
            self._line()
            self._line("Checking baselines...")

    def baseline(self, label: str, batch: BatchResult) -> None:
        if not self.quiet:
            self._line(f"  {label} environment → {self._status(batch.status)} ({_counts(batch)})")
            self._show_runs(batch)

    def differences(self, changes: tuple[Change, ...]) -> None:
        if not self.quiet:
            self._line()
            self._line(f"{len(changes)} environment differences found.")
            self._line("Minimizing failure-inducing changes...")

    def experiment(self, number: int, candidate: tuple[Change, ...], batch: BatchResult) -> None:
        if self.quiet:
            return
        if self.verbose:
            names = ", ".join(change.key for change in candidate) or "(none)"
            self._line(
                f"Experiment {number}: {names} → {self._status(batch.status)} ({_counts(batch)})"
            )
            self._show_runs(batch)
        elif number == 1 or number % 10 == 0:
            self._line(f"  {number} experiments completed; latest: {self._status(batch.status)}")

    def _show_runs(self, batch: BatchResult) -> None:
        if not self.verbose:
            return
        for index, run in enumerate(batch.runs, start=1):
            self._line(
                f"    run {index}: {self._status(run.status)}, "
                f"exit={run.exit_code}, {run.duration:.3f}s"
            )
            for stream_name, stream in (("stdout", run.stdout), ("stderr", run.stderr)):
                if stream:
                    safe = redact_text(stream, self.secrets)
                    self._line(f"      {stream_name}: {_safe_display(safe)}")

    def _changes(self, changes: Iterable[Change]) -> None:
        for change in changes:
            before = _safe_display(
                format_value(change.key, change.passing_value, change.passing_present)
            )
            after = _safe_display(
                format_value(change.key, change.failing_value, change.failing_present)
            )
            self._line(f"  {change.key}")
            self._line(f"    {before} → {after}")

    def success(self, result: DiagnosisResult) -> None:
        if self.quiet:
            for change in result.minimal_changes:
                self._line(change.key)
            return
        self._line()
        self._line("Minimal failure-inducing set (1-minimal under the tested conditions):")
        self._changes(result.minimal_changes)
        if len(result.minimal_changes) > 1:
            self._line("These changes act together in the observed failure.")
        self._line()
        self._line("Verification")
        self._line(f"  PASS + changes → {_counts(result.forward)}")
        self._line(f"  FAIL - changes → {_counts(result.reverse)}")
        self._line()
        self._line(f"Runs: {result.runs}")
        self._line(f"Experiments: {result.experiments}")
        self._line(f"Duration: {result.duration:.2f}s")
        if result.deterministic:
            self._line("All observed runs were consistent.")
        else:
            self._line(
                "Some intermediate experiments were indeterminate; "
                "final verification was consistent."
            )
        self._show_runs(result.forward)
        self._show_runs(result.reverse)

    def problem(self, problem: DiagnosisProblem, *, runs: int) -> None:
        self._line(str(problem), error=True)
        if problem.stage == "baseline" and problem.pass_batch and problem.fail_batch:
            self._line("Expected: PASS environment → PASS; FAIL environment → FAIL", error=True)
            observed_pass = f"{problem.pass_batch.status.value} ({_counts(problem.pass_batch)})"
            observed_fail = f"{problem.fail_batch.status.value} ({_counts(problem.fail_batch)})"
            self._line(
                f"Observed: PASS environment → {observed_pass}; FAIL environment → {observed_fail}",
                error=True,
            )
        if problem.stage == "verification":
            self._line("Unverified candidate set:", error=True)
            for change in problem.minimal:
                self._line(f"  {change.key}", error=True)
            if problem.forward is not None and problem.reverse is not None:
                self._line(f"PASS + changes → {_counts(problem.forward)}", error=True)
                self._line(f"FAIL - changes → {_counts(problem.reverse)}", error=True)
        if runs:
            self._line(f"Runs: {runs}", error=True)

"""Coordinate controlled experiments and verify a ddmin result."""

from __future__ import annotations

import os
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .ddmin import IndeterminateError, ddmin
from .diff import apply_changes, diff_environments
from .env import parse_env_file
from .models import Change, RunResult, Status
from .redact import is_likely_secret
from .runner import CommandRunner


@dataclass(frozen=True, slots=True)
class BatchResult:
    """A repeat-based classification of one candidate environment."""

    status: Status
    runs: tuple[RunResult, ...]

    def count(self, status: Status) -> int:
        return sum(run.status is status for run in self.runs)

    @property
    def counts(self) -> Counter[Status]:
        return Counter(run.status for run in self.runs)


@dataclass(frozen=True, slots=True)
class DiagnosisResult:
    differing_changes: tuple[Change, ...]
    minimal_changes: tuple[Change, ...]
    baseline_pass: BatchResult
    baseline_fail: BatchResult
    forward: BatchResult
    reverse: BatchResult
    runs: int
    experiments: int
    duration: float
    deterministic: bool


class DiagnosisObserver(Protocol):
    """Receive progress without tying the experiment engine to terminal I/O."""

    def set_secrets(self, values: set[str]) -> None: ...

    def checking_baselines(self) -> None: ...

    def baseline(self, label: str, batch: BatchResult) -> None: ...

    def differences(self, changes: tuple[Change, ...]) -> None: ...

    def experiment(
        self, number: int, candidate: tuple[Change, ...], batch: BatchResult
    ) -> None: ...


class DiagnosisProblem(Exception):
    """An expected, user-facing reason that diagnosis cannot be certified."""

    def __init__(
        self,
        message: str,
        code: int,
        *,
        stage: str = "",
        pass_batch: BatchResult | None = None,
        fail_batch: BatchResult | None = None,
        minimal: tuple[Change, ...] = (),
        forward: BatchResult | None = None,
        reverse: BatchResult | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.pass_batch = pass_batch
        self.fail_batch = fail_batch
        self.minimal = minimal
        self.forward = forward
        self.reverse = reverse


def _identity(key: str) -> str:
    return key.casefold() if os.name == "nt" else key


def _snapshot_environment(
    host: Mapping[str, str],
    snapshot: Mapping[str, str],
    mentioned_keys: set[str],
) -> dict[str, str]:
    """Apply one snapshot to the same captured host environment.

    Every name mentioned by either snapshot is removed first. Thus a name
    absent from one file remains absent even if the host has that name.
    """

    environment = {
        key: value for key, value in host.items() if _identity(key) not in mentioned_keys
    }
    environment.update(snapshot)
    return environment


def _classify(runs: tuple[RunResult, ...]) -> Status:
    statuses = {run.status for run in runs}
    if Status.ERROR in statuses:
        return Status.ERROR
    if Status.TIMEOUT in statuses:
        return Status.TIMEOUT
    if statuses == {Status.PASS}:
        return Status.PASS
    if statuses == {Status.FAIL}:
        return Status.FAIL
    return Status.FLAKY


class Diagnoser:
    """Run baselines, ddmin experiments, and independent verification."""

    def __init__(
        self,
        command: Sequence[str],
        *,
        repeats: int = 3,
        timeout: float | None = None,
        observer: DiagnosisObserver | None = None,
        host_environment: Mapping[str, str] | None = None,
    ) -> None:
        if repeats < 1:
            raise ValueError("Repeats must be at least 1")
        self.runner = CommandRunner(command, timeout)
        self.repeats = repeats
        self.observer = observer
        self.host_environment = dict(os.environ if host_environment is None else host_environment)
        self.runs = 0
        self.experiments = 0
        self.uncertain_experiments = 0

    def _batch(self, environment: Mapping[str, str], count: int | None = None) -> BatchResult:
        trials: list[RunResult] = []
        for _ in range(self.repeats if count is None else count):
            result = self.runner.run(environment)
            self.runs += 1
            trials.append(result)
        recorded = tuple(trials)
        return BatchResult(_classify(recorded), recorded)

    def diagnose(self, passing_file: str | Path, failing_file: str | Path) -> DiagnosisResult:
        started = time.monotonic()
        passing_snapshot = parse_env_file(passing_file)
        failing_snapshot = parse_env_file(failing_file)
        changes = tuple(diff_environments(passing_snapshot, failing_snapshot))
        if not changes:
            raise DiagnosisProblem("No differing environment variables were found.", 3)

        mentioned = {_identity(key) for key in passing_snapshot.keys() | failing_snapshot.keys()}
        passing = _snapshot_environment(self.host_environment, passing_snapshot, mentioned)
        failing = _snapshot_environment(self.host_environment, failing_snapshot, mentioned)
        if self.observer is not None:
            secret_values = {
                value
                for environment in (self.host_environment, passing_snapshot, failing_snapshot)
                for key, value in environment.items()
                if value and is_likely_secret(key)
            }
            self.observer.set_secrets(secret_values)
            self.observer.checking_baselines()

        pass_batch = self._batch(passing)
        if self.observer is not None:
            self.observer.baseline("PASS", pass_batch)
        fail_batch = self._batch(failing)
        if self.observer is not None:
            self.observer.baseline("FAIL", fail_batch)

        if Status.ERROR in (pass_batch.status, fail_batch.status):
            raise DiagnosisProblem(
                "The command could not be executed under a baseline environment.",
                5,
                stage="baseline",
                pass_batch=pass_batch,
                fail_batch=fail_batch,
            )
        if Status.TIMEOUT in (pass_batch.status, fail_batch.status):
            raise DiagnosisProblem(
                "A baseline command timed out; no PASS/FAIL conclusion is possible.",
                4,
                stage="baseline",
                pass_batch=pass_batch,
                fail_batch=fail_batch,
            )
        if Status.FLAKY in (pass_batch.status, fail_batch.status):
            raise DiagnosisProblem(
                "A baseline command was nondeterministic; no reliable minimization is possible.",
                4,
                stage="baseline",
                pass_batch=pass_batch,
                fail_batch=fail_batch,
            )
        if pass_batch.status is not Status.PASS or fail_batch.status is not Status.FAIL:
            raise DiagnosisProblem(
                "EnvBisect cannot diagnose this case: the baselines do not match "
                "the expected behavior.",
                2,
                stage="baseline",
                pass_batch=pass_batch,
                fail_batch=fail_batch,
            )

        if self.observer is not None:
            self.observer.differences(changes)

        # The baseline observations are equivalent to the empty and full
        # candidate sets, so there is no reason to execute either again.
        cache: dict[frozenset[Change], BatchResult] = {
            frozenset(): pass_batch,
            frozenset(changes): fail_batch,
        }

        def test(candidate: tuple[Change, ...]) -> Status:
            key = frozenset(candidate)
            if key not in cache:
                environment = apply_changes(passing, candidate)
                batch = self._batch(environment)
                cache[key] = batch
                self.experiments += 1
                if batch.status in (Status.FLAKY, Status.TIMEOUT, Status.ERROR):
                    self.uncertain_experiments += 1
                if self.observer is not None:
                    self.observer.experiment(self.experiments, candidate, batch)
            return cache[key].status

        try:
            minimal = tuple(ddmin(changes, test))
        except IndeterminateError as error:
            statuses = ", ".join(sorted(status.value for status in error.statuses))
            raise DiagnosisProblem(
                f"An uncertain candidate ({statuses}) prevents a reliable minimality claim.",
                4,
                stage="minimization",
                pass_batch=pass_batch,
                fail_batch=fail_batch,
            ) from error

        # Verification must be independent of cached minimization evidence.
        verification_repeats = max(5, self.repeats)
        forward = self._batch(apply_changes(passing, minimal), verification_repeats)
        reverse_changes = tuple(
            Change(
                key=change.key,
                passing_value=change.failing_value,
                failing_value=change.passing_value,
                passing_present=change.failing_present,
                failing_present=change.passing_present,
            )
            for change in minimal
        )
        reverse = self._batch(apply_changes(failing, reverse_changes), verification_repeats)
        if forward.status is not Status.FAIL or reverse.status is not Status.PASS:
            raise DiagnosisProblem(
                "Verification did not establish both forward failure and reverse recovery.",
                4,
                stage="verification",
                pass_batch=pass_batch,
                fail_batch=fail_batch,
                minimal=minimal,
                forward=forward,
                reverse=reverse,
            )

        return DiagnosisResult(
            differing_changes=changes,
            minimal_changes=minimal,
            baseline_pass=pass_batch,
            baseline_fail=fail_batch,
            forward=forward,
            reverse=reverse,
            runs=self.runs,
            experiments=self.experiments,
            duration=time.monotonic() - started,
            deterministic=self.uncertain_experiments == 0,
        )

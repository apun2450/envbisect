"""Small, typed values shared by the diagnosis pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Status(StrEnum):
    """Outcome of one execution or a group of repeated executions."""

    PASS = "PASS"
    FAIL = "FAIL"
    FLAKY = "FLAKY"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class Change:
    """One difference between passing and failing environment snapshots.

    Presence is explicit because an absent variable and an empty variable are
    observably different to a child process.
    """

    key: str
    passing_value: str | None
    failing_value: str | None
    passing_present: bool
    failing_present: bool

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("An environment change needs a key")
        if self.passing_present != (self.passing_value is not None):
            raise ValueError("Passing presence and value disagree")
        if self.failing_present != (self.failing_value is not None):
            raise ValueError("Failing presence and value disagree")
        if (
            self.passing_present == self.failing_present
            and self.passing_value == self.failing_value
        ):
            raise ValueError("A change must describe different states")


@dataclass(frozen=True, slots=True)
class RunResult:
    """Observed result of a single command execution."""

    status: Status
    exit_code: int | None
    duration: float
    stdout: str
    stderr: str

from __future__ import annotations

import pytest

from envbisect.ddmin import IndeterminateError, ddmin
from envbisect.models import Change, Status


def make_changes(count: int) -> list[Change]:
    return [Change(f"V{i:02d}", "0", "1", True, True) for i in range(count)]


def test_finds_one_culprit_among_thirty_irrelevant_differences() -> None:
    changes = make_changes(31)

    def test(candidate: tuple[Change, ...]) -> Status:
        return Status.FAIL if "V17" in {change.key for change in candidate} else Status.PASS

    assert [change.key for change in ddmin(changes, test)] == ["V17"]


def test_finds_interacting_pair_among_forty_irrelevant_differences() -> None:
    changes = make_changes(42)

    def test(candidate: tuple[Change, ...]) -> Status:
        keys = {change.key for change in candidate}
        return Status.FAIL if {"V07", "V36"} <= keys else Status.PASS

    assert {change.key for change in ddmin(changes, test)} == {"V07", "V36"}
    assert test(tuple(change for change in changes if change.key == "V07")) is Status.PASS
    assert test(tuple(change for change in changes if change.key == "V36")) is Status.PASS


def test_predicate_is_not_reexecuted_for_identical_candidate() -> None:
    changes = make_changes(12)
    calls: list[frozenset[str]] = []

    def test(candidate: tuple[Change, ...]) -> Status:
        keyset = frozenset(change.key for change in candidate)
        calls.append(keyset)
        return Status.FAIL if {"V02", "V11"} <= keyset else Status.PASS

    assert {change.key for change in ddmin(changes, test)} == {"V02", "V11"}
    assert len(calls) == len(set(calls))


@pytest.mark.parametrize("uncertain", [Status.FLAKY, Status.TIMEOUT, Status.ERROR])
def test_does_not_claim_certain_minimum_from_uncertain_results(uncertain: Status) -> None:
    changes = make_changes(2)

    def test(candidate: tuple[Change, ...]) -> Status:
        return Status.FAIL if len(candidate) == 2 else uncertain

    with pytest.raises(IndeterminateError):
        ddmin(changes, test)

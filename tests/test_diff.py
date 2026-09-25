from __future__ import annotations

import os

import pytest

from envbisect.diff import apply_changes, diff_environments


def test_diff_distinguishes_absent_from_empty() -> None:
    changes = diff_environments({"EMPTY": "", "REMOVED": "value"}, {"ADDED": ""})
    by_key = {change.key: change for change in changes}

    assert set(by_key) == {"EMPTY", "REMOVED", "ADDED"}
    assert by_key["EMPTY"].passing_present is True
    assert by_key["EMPTY"].passing_value == ""
    assert by_key["EMPTY"].failing_present is False
    assert by_key["REMOVED"].passing_present is True
    assert by_key["REMOVED"].failing_present is False
    assert by_key["ADDED"].passing_present is False
    assert by_key["ADDED"].failing_present is True
    assert by_key["ADDED"].failing_value == ""


def test_apply_changes_adds_updates_and_removes_without_mutating_base() -> None:
    passing = {"SAME": "stable", "REMOVED": "old", "UPDATED": "before"}
    failing = {"SAME": "stable", "ADDED": "", "UPDATED": "after"}
    changes = diff_environments(passing, failing)

    assert apply_changes(passing, changes) == failing
    assert passing == {"SAME": "stable", "REMOVED": "old", "UPDATED": "before"}


def test_unchanged_values_are_not_changes() -> None:
    assert diff_environments({"X": "same"}, {"X": "same"}) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows environment names are case insensitive")
def test_windows_key_casing_does_not_create_a_spurious_difference() -> None:
    assert diff_environments({"ENVBISECT_CASE": "same"}, {"envbisect_case": "same"}) == []

    changes = diff_environments({"ENVBISECT_CASE": "old"}, {"envbisect_case": "new"})
    assert len(changes) == 1
    assert changes[0].passing_value == "old"
    assert changes[0].failing_value == "new"
    assert apply_changes({"ENVBISECT_CASE": "old"}, changes) == {"envbisect_case": "new"}

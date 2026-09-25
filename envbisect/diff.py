"""Describe and apply environment changes, including variable removal."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping

from .models import Change


def _identity(key: str) -> str:
    return key.casefold() if os.name == "nt" else key


def _indexed(environment: Mapping[str, str]) -> dict[str, tuple[str, str]]:
    # Windows environment names are case insensitive. If a caller accidentally
    # supplies duplicate casings, the last entry wins, as it does in a dotenv.
    return {_identity(key): (key, value) for key, value in environment.items()}


def diff_environments(passing: Mapping[str, str], failing: Mapping[str, str]) -> list[Change]:
    """Return stable, key-sorted changes from passing to failing snapshots."""

    pass_index = _indexed(passing)
    fail_index = _indexed(failing)
    changes: list[Change] = []
    for identity in sorted(pass_index.keys() | fail_index.keys()):
        pass_entry = pass_index.get(identity)
        fail_entry = fail_index.get(identity)
        passing_value = pass_entry[1] if pass_entry is not None else None
        failing_value = fail_entry[1] if fail_entry is not None else None
        if passing_value == failing_value and (pass_entry is None) == (fail_entry is None):
            continue
        # Prefer the failing key's spelling for additions or changed values.
        if fail_entry is not None:
            key = fail_entry[0]
        else:
            assert pass_entry is not None
            key = pass_entry[0]
        changes.append(
            Change(
                key=key,
                passing_value=passing_value,
                failing_value=failing_value,
                passing_present=pass_entry is not None,
                failing_present=fail_entry is not None,
            )
        )
    return changes


def apply_changes(base: Mapping[str, str], changes: Iterable[Change]) -> dict[str, str]:
    """Start with ``base`` and apply only the failing side of ``changes``."""

    result = dict(base)
    for change in changes:
        identity = _identity(change.key)
        for existing in tuple(result):
            if _identity(existing) == identity:
                del result[existing]
        if change.failing_present:
            assert change.failing_value is not None
            result[change.key] = change.failing_value
    return result

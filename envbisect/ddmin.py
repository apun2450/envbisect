"""Delta debugging for a failure-inducing set of environment changes."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from .models import Change, Status


class IndeterminateError(RuntimeError):
    """An uncertain experiment prevented a defensible minimality claim."""

    def __init__(self, statuses: set[Status]) -> None:
        self.statuses = frozenset(statuses)
        names = ", ".join(sorted(status.value for status in statuses))
        super().__init__(f"Cannot establish a minimal set: indeterminate result ({names})")


def _partition(items: tuple[Change, ...], count: int) -> list[tuple[Change, ...]]:
    size, extra = divmod(len(items), count)
    groups: list[tuple[Change, ...]] = []
    offset = 0
    for index in range(count):
        end = offset + size + (index < extra)
        groups.append(items[offset:end])
        offset = end
    return groups


def ddmin(
    changes: Sequence[Change],
    test: Callable[[tuple[Change, ...]], Status],
    on_test: Callable[[tuple[Change, ...], Status], None] | None = None,
) -> list[Change]:
    """Return a 1-minimal failure-inducing subset using ddmin.

    The caller must establish that the empty set passes and the full set fails
    before calling this function. A subset is tested against the passing
    environment by the supplied predicate. PASS and FAIL are decisive; FLAKY,
    TIMEOUT, and ERROR are indeterminate. Uncertain branches are skipped while
    another reduction remains possible, but uncertainty blocks a final claim
    when it could hide a smaller failing set.
    """

    current = tuple(changes)
    if len(current) < 2:
        return list(current)

    cache: dict[frozenset[Change], Status] = {}

    def probe(candidate: tuple[Change, ...]) -> Status:
        key = frozenset(candidate)
        if key not in cache:
            status = test(candidate)
            if not isinstance(status, Status):
                raise TypeError("ddmin test must return a Status")
            cache[key] = status
            if on_test is not None:
                on_test(candidate, status)
        return cache[key]

    granularity = 2
    while len(current) >= 2:
        groups = _partition(current, granularity)
        unresolved: set[Status] = set()
        reduced = False

        for group in groups:
            status = probe(group)
            if status is Status.FAIL:
                current = group
                granularity = max(2, granularity - 1)
                reduced = True
                break
            if status is not Status.PASS:
                unresolved.add(status)
        if reduced:
            continue

        offset = 0
        for group in groups:
            complement = current[:offset] + current[offset + len(group) :]
            offset += len(group)
            status = probe(complement)
            if status is Status.FAIL:
                current = complement
                granularity = max(2, granularity - 1)
                reduced = True
                break
            if status is not Status.PASS:
                unresolved.add(status)
        if reduced:
            continue

        if granularity == len(current):
            if unresolved:
                raise IndeterminateError(unresolved)
            return list(current)
        granularity = min(len(current), granularity * 2)

    return list(current)

from __future__ import annotations

import os
import sys
from pathlib import Path

from envbisect.diff import apply_changes, diff_environments
from envbisect.env import parse_env_file
from envbisect.models import Status
from envbisect.runner import CommandRunner


def test_showcase_has_forty_six_differences_and_requires_both_causes() -> None:
    demo = Path(__file__).resolve().parents[1] / "examples" / "demo"
    passing = parse_env_file(demo / "pass.env")
    failing = parse_env_file(demo / "fail.env")
    changes = diff_environments(passing, failing)
    assert len(changes) == 46

    clean_host = {key: value for key, value in os.environ.items() if key not in passing | failing}
    pass_env = clean_host | passing
    command = CommandRunner([sys.executable, str(demo / "app.py")], timeout=3)

    assert command.run(pass_env).status is Status.PASS
    assert command.run(apply_changes(pass_env, changes)).status is Status.FAIL
    for culprit in ("TZ", "FEATURE_CACHE"):
        only_one = [change for change in changes if change.key == culprit]
        assert command.run(apply_changes(pass_env, only_one)).status is Status.PASS

# Contributing to EnvBisect

Thanks for helping make environment debugging more reliable. EnvBisect has a narrow scope: diagnose changes in environment-variable values and presence by rerunning a command. Please discuss major feature proposals in an issue before building them.

## Set up a checkout

Python 3.11 or newer is required.

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Run the showcase from the repository root:

```bash
envbisect diagnose --pass examples/demo/pass.env --fail examples/demo/fail.env -- python examples/demo/app.py
```

The result should identify `TZ` and `FEATURE_CACHE`. The command should be deterministic and quick.

## Make a change

- Keep the command-line interface, environment parsing, command runner, minimizer, and reporting concerns separate.
- Add a focused test for behavior changes. Especially cover interacting variables, missing versus empty values, baseline mismatch, flakiness, timeout, and secret redaction where relevant.
- Use typed models and clear names. Prefer readable experiments over clever shortcuts.
- Treat exit code 0 as PASS, nonzero as FAIL, and uncertain outcomes as uncertain. Never turn a timeout or mixed repeat outcome into a confident diagnosis.
- Do not include real credentials in tests, examples, issue reports, or CLI transcripts. Use obvious synthetic values.
- Update the README, technical write-up, or changelog when a user-facing behavior changes.

To test a CLI change, exercise the installed `envbisect` command as well as the Python API or module involved. Check both ordinary and `--no-color` output when formatting changes.

## Submit a pull request

Describe the problem, the behavior before and after the change, and the commands you ran to verify it. Small, focused pull requests are easiest to review. If a new diagnosis path can fail or become indeterminate, include a test and explain how the CLI communicates that outcome.

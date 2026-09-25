# EnvBisect v0.1.0

EnvBisect v0.1.0 is the first public release.

It diagnoses “works on my machine” environment drift by running controlled experiments between a known passing and known failing dotenv snapshot. The included demo has 46 differing variables. EnvBisect reduces them to the two-variable interaction, `FEATURE_CACHE` and `TZ`, that reproduces the demo failure.

## Included

- Snapshot comparison, including absent versus empty environment values.
- Ddmin style minimization that can find interacting variables.
- Forward and reverse verification of a candidate set.
- Repeated command execution to expose flaky outcomes, plus distinct timeout reporting.
- Heuristic redaction of likely secret values in EnvBisect reports.
- A deterministic 46-difference demo and automated tests.

From a checkout, install with `python -m pip install -e .`, then run:

```bash
envbisect diagnose --pass examples/demo/pass.env --fail examples/demo/fail.env -- python examples/demo/app.py
```

The result is 1-minimal under the tested conditions. It is not a claim that the set is the only possible cause or the smallest set across every environment. Read [How it works](how-it-works.md) for the exact model and [Security](../SECURITY.md) before sharing logs or snapshots.

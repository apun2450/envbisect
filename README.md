# EnvBisect

**Find the environment difference that actually broke your program.**

Works locally. Fails in CI. Forty-six environment variables differ. EnvBisect runs your command under controlled combinations and finds the two that matter in the included demo.

```bash
python -m pip install -e .
envbisect diagnose --pass examples/demo/pass.env --fail examples/demo/fail.env -- python examples/demo/app.py
```

The demo reports `TZ` and `FEATURE_CACHE`. Neither change causes its failure alone; both are required. The 44 `DEMO_NOISE_*` changes do nothing.

An environment diff tells you **what changed**. EnvBisect tests **which combinations reproduce the failure** under a specified command and execution environment.

## Install

Requires Python 3.11 or newer. From a checkout:

```bash
python -m pip install -e .
envbisect --help
```

There are no required runtime dependencies. You can also run `python -m envbisect` from the checkout.

## Diagnose your command

Create two dotenv snapshots. The passing snapshot describes the environment in which the command succeeds; the failing snapshot describes the one in which it fails.

```dotenv
# working.env
TZ=Asia/Kolkata
FEATURE_CACHE=0
```

```dotenv
# broken.env
TZ=UTC
FEATURE_CACHE=1
```

Run the **same command** against both snapshots:

```bash
envbisect diagnose --pass working.env --fail broken.env -- python your_script.py
```

Everything after `--` is the command and its arguments. To use shell expansion, pipes, or shell builtins, invoke a shell explicitly as that command. EnvBisect runs each candidate in a subprocess and treats exit code 0 as PASS and a nonzero exit code as FAIL.

EnvBisect identifies the snapshot differences, then confirms that the command passes with `--pass` and fails with `--fail`. It stops with a clear message if these baselines disagree with the labels. It minimizes the failure-inducing changes and verifies the result. A typical successful report contains:

```text
46 environment differences found.

Minimal failure-inducing set (1-minimal under the tested conditions):
  FEATURE_CACHE
    0 → 1
  TZ
    Asia/Kolkata → UTC

Verification
  PASS + changes → FAIL 5/5
  FAIL - changes → PASS 5/5

Runs: 46
```

The example run count is for this deterministic fixture with the default repeat count; other commands and settings can require a different number of executions. The actual report also shows elapsed time.

### Snapshot semantics

EnvBisect captures the current process environment once. For each experiment it copies that environment, removes every key mentioned in either dotenv file, and applies the chosen snapshot's values. Keys absent from **both** files remain inherited from the captured host environment. A key present in only one file is absent from the other snapshot, even if that key was present in the host environment.

This makes small snapshots usable while preserving an executable search path and other host settings. Run both baselines on the same machine and keep inputs outside the snapshots stable. EnvBisect never edits the snapshot files or your permanent environment.

Dotenv files support assignments such as `KEY=value`, empty values (`KEY=`), comments, whitespace, and quoted values. Missing and empty values have different meanings.

## Why minimization matters

Suppose the passing environment has `A=0` and `B=0`, while the failing one has `A=1` and `B=1`:

| Changes applied to the passing snapshot | Command |
| --- | --- |
| Neither | PASS |
| `A` only | PASS |
| `B` only | PASS |
| `A` and `B` | FAIL |

Checking each variable alone misses this case. EnvBisect uses a ddmin style algorithm that tests subsets **and complements** of the differing changes. The resulting set is *1-minimal* for the observed behavior: removing any one selected change no longer reproduces the failure. It is not a guarantee of the smallest possible set by cardinality or a unique root cause. See [How it works](docs/how-it-works.md).

## Reliability and output

EnvBisect uses three runs per baseline and candidate by default, and at least five runs for final verification. Repeated execution helps expose unstable commands:

```bash
envbisect diagnose --pass working.env --fail broken.env --repeats 3 --timeout 30 -- python your_script.py
```

For a repeated candidate, unanimous zero exits mean PASS; unanimous nonzero exits mean FAIL; mixed outcomes are FLAKY. A timeout is reported separately. If outcomes do not support a reliable minimization, EnvBisect reports uncertainty instead of claiming a cause.

Use `--verbose` to inspect command output, `--quiet` to print only identified keys on success, and `--no-color` for plain terminals. Quiet and color settings do not change classification.

Variable names suggesting secrets, including tokens, passwords, credentials, auth data, private keys, and API keys, have their values redacted in reports. Real values still reach the tested command. Redaction is heuristic: review snapshots before sharing them, and remember that a command can itself print secrets to stdout or stderr, especially in verbose mode.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Diagnosis and verification completed |
| 1 | Invalid usage or configuration |
| 2 | Baselines do not match PASS/FAIL expectations |
| 3 | No differing environment variables |
| 4 | Flaky, timed out, or otherwise indeterminate evidence |
| 5 | Command execution or internal error |

## Limits of the conclusion

A diagnosis is a minimal failure-inducing set **under the tested environment and command**. Other causes may exist. Files, network responses, time, process state, external services, and the inherited host environment can change outcomes independently of the dotenv differences. Side effects from one run can affect later runs. A command that is flaky or whose behavior changes over time may not admit a trustworthy result.

EnvBisect diagnoses environment-variable values and presence in two snapshots. It does not inspect dependency versions, the filesystem, containers, or network behavior.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

See [Contributing](CONTRIBUTING.md) for the project workflow and [the changelog](CHANGELOG.md) for release notes. Future work will stay focused on making experiments and explanations more reliable before adding other kinds of environment drift.

## License

EnvBisect is available under the [MIT License](LICENSE).

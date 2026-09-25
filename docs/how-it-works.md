# How EnvBisect works

## From a diff to an experiment

A “works on my machine” failure often starts with a long list of differences: time zone, feature flags, service URLs, tokens, and dozens of incidental settings. A textual diff answers which values changed. It does not establish which changes altered a particular command's exit status.

EnvBisect accepts two dotenv snapshots and one command. Let `P` be the passing snapshot and `F` the failing snapshot. The tool identifies every key whose value **or presence** differs. Each difference is a change such as:

```text
TZ:             "Asia/Kolkata" → "UTC"
FEATURE_CACHE:  "0"            → "1"
HTTP_PROXY:     present        → absent
```

A candidate set `S` is tested by starting with `P` and applying only the changes in `S` from `F`. The command's exit status supplies the observation:

```text
test(S) = PASS  if the command exits 0
test(S) = FAIL  if the command exits nonzero
```

Timeouts, execution errors, and mixed outcomes across repeat runs have separate classifications. They are not quietly promoted to FAIL.

Before searching, EnvBisect checks the two endpoints: `test(∅)` must PASS and `test(all changes)` must FAIL. A mismatch means the stated comparison cannot be reproduced in this run, so minimization would lack its basic premise.

For each subprocess, EnvBisect begins with a single captured copy of the host environment. It removes all keys mentioned in either snapshot, then sets the values for the chosen candidate. Thus a key missing from a snapshot is actually absent in that experiment, while a key absent from *both* files is inherited. This keeps the execution context, including `PATH`, usable without pretending that the files fully describe the host.

## Why single-variable testing fails

Imagine a program fails only when `TZ=UTC` and `FEATURE_CACHE=1` occur together. From a passing baseline, changing either one by itself gives PASS. A search that tests only individual changes declares both harmless. The pair gives FAIL.

This is an interaction: the effect of one variable depends on another. More complicated commands can have several such interactions or even multiple independent failure-inducing sets. EnvBisect therefore tests groups of changes and asks whether parts can be removed while preserving failure.

## Delta debugging in brief

EnvBisect uses a ddmin style reduction over the set of differences:

1. Start with the full, known failing set.
2. Partition it into chunks.
3. Test each chunk and each complement (the current set with that chunk removed).
4. If a smaller set still fails, keep that set and continue.
5. If none fails, increase the partition granularity.
6. Stop when no single selected change can be removed while preserving the observed failure.

The complement tests are crucial: they let the algorithm discard many irrelevant variables while retaining variables that fail only together. For the included demo, 44 differences are noise and the result is `{TZ, FEATURE_CACHE}`.

The result is **1-minimal** under the test oracle: removing any one of its changes yields PASS when tested from the passing baseline. This is a local minimality condition, not a proof that the set has the smallest possible number of variables among *all* failing subsets. Several 1-minimal sets may exist. Search order and the command's behavior can influence which one is found.

Classical ddmin can require quadratic numbers of candidate tests in the worst case, roughly `O(n²)` for `n` differences. Favorable cases can need closer to `O(n log n)` tests. A candidate test itself runs the user's command, so wall time is dominated by command duration and by the repeat count. EnvBisect caches classifications for exact candidate sets to avoid redundant experiments during one diagnosis. That cache does not make an unstable command deterministic.

## Verification is a separate step

Finding a reduced failing set is not enough to publish a confident result. EnvBisect reapplies the selected changes to the passing environment and repeats the command. It also tries the reverse experiment: start with the failing environment, revert those changes to their passing values, and check whether the command passes.

These tests ask different questions:

- **Forward:** Are the selected changes sufficient to reproduce FAIL from this passing baseline?
- **Reverse:** Does reverting those changes repair the given failing baseline?

The reverse check may fail when another independent cause remains in the failing environment, even though the selected set is genuinely failure inducing. A report should make that evidence visible instead of claiming a sole cause.

Even unanimous verification does not prove a universal causal law. It supports a conclusion for the chosen snapshots, command, host environment, and time of execution. It cannot rule out unobserved inputs or a different failure-inducing set.

## Nondeterminism and cost

A command may depend on scheduling, external services, random input, file state, or time. EnvBisect can run each candidate more than once. With a repeat count of `k`:

- `k` zero exits classify PASS.
- `k` nonzero exits classify FAIL.
- A mixture classifies FLAKY.
- A timeout remains TIMEOUT and is surfaced distinctly.

Unanimity is evidence, not a statistical guarantee. A rare failure may escape a small repeat count. Increasing repeats costs more command executions; choosing a repeat count should reflect the command's runtime and observed stability. When a flaky or timed out candidate prevents reliable reduction, the appropriate outcome is an indeterminate diagnosis.

The command may also have side effects. If one experiment modifies a database, cache, or file that later experiments read, subsequent results no longer compare the same conditions. Use a disposable, resettable test target when possible.

## Security boundary

The subprocess receives the actual environment values. EnvBisect uses name-based heuristics to hide likely secret values in its own reports, including token, password, credential, private-key, auth, cookie, and session names. Heuristics can miss an unusually named secret. The tested command can also print a secret itself; inspect verbose output before sharing logs. Snapshot files should be handled with the same care as any configuration containing credentials.

## Scope and future work

Version 0.1 deliberately limits its model to environment-variable presence and values. It does not isolate filesystem, dependency, container, network, clock, or process-state differences. Possible future improvements include stronger handling of unstable tests, richer experiment records, and more control over execution isolation. Any extension should preserve the central rule: report only what the experiments establish.

# Changelog

Changes to EnvBisect are recorded here.

## 0.1.0

First public release.

### Added

- Compare passing and failing dotenv snapshots, including changed values and presence.
- Minimize failure-inducing differences with a ddmin style algorithm that handles interacting variables.
- Verify selected changes from the passing baseline and attempt reverse verification from the failing baseline.
- Repeat command executions to detect flaky outcomes, report timeouts distinctly, and count runs.
- Heuristically redact likely secret environment values in ordinary reports.
- Include a deterministic 46-difference demo, automated tests, and contributor documentation.

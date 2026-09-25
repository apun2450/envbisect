# Changelog

Changes to EnvBisect are recorded here.

## Unreleased (0.1.0)

### Added

- Diagnose a command using passing and failing dotenv snapshots.
- Compare environment-variable values and presence, including empty versus absent values.
- Minimize failure-inducing differences with a ddmin style algorithm that handles interacting variables.
- Verify the selected changes from the passing baseline and attempt reverse verification from the failing baseline.
- Repeat candidate commands to identify mixed outcomes, report timeouts distinctly, and count command executions.
- Redact likely secret environment values in ordinary reports.
- Provide the 46-difference demo, automated tests, and contributor documentation.

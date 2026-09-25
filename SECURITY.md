# Security

## Reporting a vulnerability

Please report a suspected security vulnerability privately through GitHub's **Report a vulnerability** option in this repository's Security tab, if available. If private reporting is unavailable, open an issue asking the maintainers for a private contact channel without including exploit details or sensitive data.

Do not post credentials, unredacted environment snapshots, command output containing secrets, or exploit details in a public issue.

## Data handling

EnvBisect runs the supplied command locally with the actual environment values. Its own reports use name-based heuristics to redact likely secret values, but unusual names can be missed. The diagnosed command can print secrets to stdout or stderr, particularly when `--verbose` displays that output. Review all snapshots, logs, and recordings before sharing them.

Use synthetic credentials in reproduction cases whenever possible.

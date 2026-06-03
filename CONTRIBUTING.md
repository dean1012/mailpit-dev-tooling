# Contributing

Thank you for your interest in improving `mailpit-dev-tooling`.

## Development Setup

See [README.md](README.md) for installation, configuration, and local Mailpit
usage.

## Validation

Run the same validation commands used by CI:

```bash
python3 -m unittest discover -s tests -v
shellcheck mailpitctl
yamllint .
docker compose config
markdownlint-cli2 .
```

The unit test suite measures `mailpitctl` shell line coverage with a Bash
`DEBUG` trap and fails if coverage falls below the 90% threshold configured in
`tests/test_mailpitctl.py`. This coverage gate is intentionally strict for
executable script lines, but it is still line coverage for a shell script. It
does not prove every branch, error path, Docker side effect, or Compose
interaction has been exercised.

Treat the Codecov badge and pull request comments as a regression signal, not
as a substitute for thoughtful test review. When changing command behavior,
configuration parsing, Docker arguments, or security-sensitive validation, add
unit tests for the meaningful success and failure cases even if the coverage
percentage remains at 100%.

CI also generates `coverage.xml` and uploads it to Codecov using GitHub Actions
OIDC authentication. No `CODECOV_TOKEN` repository secret is required.
Project coverage checks and pull request comments are configured in
`codecov.yml`.

Before committing changes, also check the current diff for whitespace errors:

```bash
git diff --check
```

## Pull Requests

Create a focused feature branch for each change. Reference the related issue in
each commit and include `Closes #<issue-number>` in the pull request
description when the pull request should close an issue after merging.

Sign each commit so GitHub can verify its authorship. The `main` branch ruleset
requires signed commits before merging:

```bash
git commit -S -m "<message> (Refs #<issue-number>)"
```

CI runs on pushes, pull requests, and manual workflow dispatches. Dependabot
checks GitHub Actions weekly.

## Documentation Guidelines

Keep user-facing behavior documented in `README.md` and contributor workflows
documented in `CONTRIBUTING.md`. In shell scripts and Compose files, add inline
comments for non-obvious implementation decisions, security boundaries, and
assumptions. Avoid comments that merely restate straightforward code.

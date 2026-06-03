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

The unit test suite measures `mailpitctl` shell line coverage and fails if
coverage falls below the 90% threshold configured in
`tests/test_mailpitctl.py`.

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

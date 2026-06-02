# Contributor Guide

Thank you for helping improve Mailpit Development Tooling. This project is
intended to stay small, predictable, and easy to run on a local development
machine.

## Development Setup

1. Install Docker with the Compose plugin.
2. Clone the repository.
3. Optionally copy `config.env.example` to `config.env` and adjust local ports.
4. Run `./mailpitctl start` to verify the local Mailpit service starts.

## Validation

Before opening a pull request, run the checks that match your change:

```bash
python3 -m unittest discover -s tests -v
shellcheck mailpitctl
yamllint .
docker compose config
```

For documentation-only changes, run markdownlint if it is available locally.

## Pull Requests

Pull requests should keep changes focused and explain the user-visible effect.
When possible, include the issue number in the commit message and close the
issue from the pull request body.

## Documentation Guidelines

Keep the README oriented around common local development workflows. Prefer
documenting configuration values in `config.env.example` so the working example
and the reference documentation stay together.

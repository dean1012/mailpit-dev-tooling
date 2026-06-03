# Mailpit Development Tooling

[![CI](https://github.com/dean1012/mailpit-dev-tooling/actions/workflows/ci.yml/badge.svg)](https://github.com/dean1012/mailpit-dev-tooling/actions/workflows/ci.yml)
[![Unit Tests](https://github.com/dean1012/mailpit-dev-tooling/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/dean1012/mailpit-dev-tooling/actions/workflows/unit-tests.yml)
[![codecov](https://codecov.io/gh/dean1012/mailpit-dev-tooling/graph/badge.svg)](https://codecov.io/gh/dean1012/mailpit-dev-tooling)

A tiny local-development wrapper for running
[Mailpit](https://mailpit.axllent.org/) with Docker Compose.

The repository provides two ways to manage the same service:

- `mailpitctl`, a small shell script for common lifecycle commands.
- `compose.yml`, for teams or developers who prefer direct Docker Compose usage.

## Features

- Starts a local Mailpit SMTP server and web UI.
- Binds to `127.0.0.1` by default so the service is local-only.
- Supports local bind address, port, and health-wait configuration.
- Uses Docker Compose health checks when starting, updating, or restarting.
- Pins the Mailpit image by version and digest for reproducibility.
- Runs the container with reduced privileges for safer local defaults.

## Requirements

- Bash
- Docker
- Docker Compose plugin (`docker compose`)

## Installation

Clone the repository and run the script from the project directory:

```bash
git clone https://github.com/dean1012/mailpit-dev-tooling.git
cd mailpit-dev-tooling
./mailpitctl start
```

Mailpit will be available at <http://127.0.0.1:8025>, and SMTP will listen on
`127.0.0.1:1025`.

## Configuration

No configuration file is required. The script and Compose file use sensible
defaults when `config.env` is absent.

To customize your local ports or bind addresses:

```bash
cp config.env.example config.env
vim config.env
```

The example file is a working configuration and documents each supported value.
Keep `127.0.0.1` for local-only access. Use a wider bind address such as
`0.0.0.0` only when another machine must reach this development environment.

## Usage

```bash
./mailpitctl start      # Create and start Mailpit
./mailpitctl status     # Show container and health status
./mailpitctl logs       # Display logs
./mailpitctl stop       # Stop the container
./mailpitctl restart    # Restart and wait for health
./mailpitctl update     # Pull, recreate, and start the pinned image
./mailpitctl destroy    # Stop and remove the container
```

`logs` forwards options to Docker Compose:

```bash
./mailpitctl logs --tail 50 --follow
```

## Updating Mailpit

The `update` command pulls and recreates the container using the image pinned in
`compose.yml`. It does not choose a newer Mailpit version automatically.

To upgrade Mailpit, update the image tag and digest in `compose.yml`, review the
upstream release notes, then run:

```bash
./mailpitctl update
```

The command keeps your local `config.env` settings, recreates the container, and
waits for the configured health check before returning.

## Docker Compose

You can also use Docker Compose directly. Defaults work without any extra flags:

```bash
docker compose up --detach --wait mailpit
docker compose ps --all mailpit
docker compose logs mailpit
docker compose down
```

If you created `config.env`, pass it to Compose so direct commands use the same
local settings as `mailpitctl`:

```bash
docker compose --env-file config.env up --detach --wait mailpit
```

The script automatically passes `config.env` to Compose when the file exists.

## Security Notes

This project is designed for local development, not production hosting. The
default loopback bind keeps the web UI and SMTP listener off the LAN. The
container also runs as a non-root user with a read-only root filesystem, dropped
Linux capabilities, `no-new-privileges`, and a constrained writable `/tmp`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and validation notes.

## License

MIT

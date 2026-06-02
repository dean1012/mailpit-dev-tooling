# Mailpit Development Tooling

Simple local Mailpit container management tooling for development workflows.

## Services

| Service        | URL / Port              |
| -------------- | ----------------------- |
| Mailpit Web UI | <http://localhost:8025> |
| SMTP Server    | `localhost:1025`        |

## Prerequisites

- Docker or Docker Desktop with Docker Compose
- Bash-compatible shell
- Local development application capable of sending SMTP email

## Installation

Clone the repository and make the management utility executable:

```bash
git clone https://github.com/dean1012/mailpit-dev-tooling.git
cd mailpit-dev-tooling
chmod +x mailpitctl
```

## Usage

```text
Usage: ./mailpitctl [--help] <command>

Options:
  -h, --help    Display usage information

Commands:
  start, up     Create the mailpit container if needed, then start it
  update        Pull the configured image, then recreate and start the mailpit container
  stop, down    Stop the mailpit container
  restart       Restart the mailpit container
  status        Show mailpit container status
  logs [-f|--follow]
                Display container logs
                -f, --follow   Follow log output live
  destroy       Stop and remove the mailpit container
```

## Usage Examples

Start the Mailpit container:

```bash
./mailpitctl start
```

Use alternate local host ports when the defaults are already in use:

```bash
MAILPIT_WEB_PORT=18025 MAILPIT_SMTP_PORT=11025 ./mailpitctl start
```

Use a longer healthcheck wait timeout on slower machines:

```bash
MAILPIT_WAIT_TIMEOUT=60 ./mailpitctl start
```

Expose Mailpit on a different host interface only when that is intentional:

```bash
MAILPIT_WEB_BIND=0.0.0.0 MAILPIT_SMTP_BIND=0.0.0.0 ./mailpitctl start
```

Update the Mailpit container to the configured image:

```bash
./mailpitctl update
```

Stop the Mailpit container:

```bash
./mailpitctl stop
```

Restart the Mailpit container:

```bash
./mailpitctl restart
```

View container status:

```bash
./mailpitctl status
```

Follow container logs live:

```bash
./mailpitctl logs -f
```

Destroy the Mailpit container:

```bash
./mailpitctl destroy
```

## Express Backend Configuration

Configure your local Express backend to send mail through Mailpit using the
following SMTP settings:

```text
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_SECURE=false
```

Example `nodemailer` configuration:

```javascript
import nodemailer from "nodemailer";

const transporter = nodemailer.createTransport({
  host: "localhost",
  port: 1025,
  secure: false,
});
```

Captured email can be viewed at:

```text
http://localhost:8025
```

## Docker Compose

A `compose.yml` file is included for users who prefer direct Docker Compose
workflows instead of the provided management utility.

By default, Mailpit binds to `127.0.0.1` on web port `8025` and SMTP port
`1025`. The loopback bind keeps the local development service off the LAN.

Start the Mailpit container using Docker Compose:

```bash
docker compose up -d
```

Use alternate host ports with Docker Compose:

```bash
MAILPIT_WEB_PORT=18025 MAILPIT_SMTP_PORT=11025 docker compose up -d
```

## Image Update Policy

The Compose file pins Mailpit to a reviewed version tag and immutable
multi-platform image digest. Running `./mailpitctl update` pulls that exact
image, then recreates and starts the container.

To upgrade Mailpit, update both the version tag and digest in `compose.yml`,
review the upstream release notes, then run:

```bash
./mailpitctl update
```

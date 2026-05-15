# Mailpit Development Tooling

Simple local Mailpit container management tooling for development workflows.

## Services

| Service        | URL / Port            |
| -------------- | --------------------- |
| Mailpit Web UI | http://localhost:8025 |
| SMTP Server    | localhost:1025        |

## Prerequisites

- Docker or Docker Desktop
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

Start the Mailpit container using Docker Compose:

```bash
docker compose up -d
```

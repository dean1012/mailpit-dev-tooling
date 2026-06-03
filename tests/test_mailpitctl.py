"""Unit tests for the mailpitctl shell entrypoint.

The tests run mailpitctl in a temporary project directory with a fake Docker CLI.
That keeps CI deterministic while still validating the Docker/Compose commands
the script would execute on a developer workstation.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from textwrap import dedent


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SOURCE = REPO_ROOT / "mailpitctl"
COVERAGE_TRACE = REPO_ROOT / ".coverage.mailpitctl.lines"
COVERAGE_XML = REPO_ROOT / "coverage.xml"
MINIMUM_LINE_COVERAGE = 90.0


FAKE_DOCKER = r"""#!/usr/bin/env python3
import json
import os
import sys

state_path = os.environ["FAKE_DOCKER_STATE"]
log_path = os.environ["FAKE_DOCKER_LOG"]


def load_state():
    with open(state_path, encoding="utf-8") as handle:
        return json.load(handle)


def save_state(state):
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, sort_keys=True)


def log_call(command, args, compose_options=None):
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "command": command,
            "args": args,
            "compose_options": compose_options or [],
        }) + "\n")


def fail_if_requested(state, key):
    if state.get(key):
        sys.exit(1)


def service_id(state):
    return "mailpit-id" if state.get("compose_exists") else ""


def main():
    args = sys.argv[1:]
    state = load_state()

    if args == ["info"]:
        log_call("info", [])
        sys.exit(0 if state.get("info_ok", True) else 1)

    if args[:2] == ["container", "inspect"]:
        log_call("container inspect", args[2:])
        exists = state.get("compose_exists") or state.get("legacy_exists")
        sys.exit(0 if exists else 1)

    if not args or args[0] != "compose":
        log_call("unknown", args)
        sys.exit(1)

    compose_options = []
    rest = args[1:]
    while rest and rest[0].startswith("--"):
        option = rest.pop(0)
        compose_options.append(option)
        if option in {"--project-directory", "--file", "--env-file"}:
            if not rest:
                sys.exit(1)
            compose_options.append(rest.pop(0))

    if rest == ["version"]:
        log_call("compose version", [], compose_options)
        sys.exit(0 if state.get("compose_ok", True) else 1)

    if not rest:
        log_call("compose", [], compose_options)
        sys.exit(1)

    command = rest[0]
    command_args = rest[1:]
    log_call(f"compose {command}", command_args, compose_options)

    if command == "ps":
        if "--all" in command_args and "--quiet" in command_args:
            if service_id(state):
                print(service_id(state))
            sys.exit(0)

        if "--status" in command_args and "running" in command_args and "--quiet" in command_args:
            if state.get("compose_exists") and state.get("running"):
                print(service_id(state))
            sys.exit(0)

        if "--format" in command_args and "json" in command_args:
            if state.get("compose_exists"):
                health = state.get("health") or ""
                status = "running" if state.get("running") else "exited"
                print(json.dumps({
                    "Name": "mailpit",
                    "Service": "mailpit",
                    "State": status,
                    "Health": health,
                }, separators=(",", ":")))
            sys.exit(0)

        if "--all" in command_args:
            if state.get("compose_exists"):
                print("NAME      SERVICE   STATUS")
                print(f"mailpit   mailpit   {state.get('health') or 'stopped'}")
            sys.exit(0)

        sys.exit(0)

    if command == "up":
        fail_if_requested(state, "up_fails")
        state["compose_exists"] = True
        state["legacy_exists"] = False
        state["running"] = True
        state["health"] = "healthy"
        save_state(state)
        sys.exit(0)

    if command == "pull":
        fail_if_requested(state, "pull_fails")
        sys.exit(0)

    if command == "start":
        fail_if_requested(state, "start_fails")
        state["compose_exists"] = True
        state["running"] = True
        save_state(state)
        sys.exit(0)

    if command == "restart":
        fail_if_requested(state, "restart_fails")
        state["running"] = True
        state["health"] = "healthy"
        save_state(state)
        sys.exit(0)

    if command == "stop":
        fail_if_requested(state, "stop_fails")
        state["running"] = False
        state["health"] = ""
        save_state(state)
        sys.exit(0)

    if command == "down":
        fail_if_requested(state, "down_fails")
        state["compose_exists"] = False
        state["running"] = False
        state["health"] = ""
        save_state(state)
        sys.exit(0)

    if command == "logs":
        fail_if_requested(state, "logs_fails")
        print(state.get("logs_output", "mailpit log line"))
        sys.exit(0)

    sys.exit(1)


if __name__ == "__main__":
    main()
"""


TRACE_SCRIPT = r"""
set -o functrace
__mailpitctl_cov_file="${MAILPITCTL_COVERAGE_FILE:-}"
trap '{
  __src="${BASH_SOURCE[0]}"
  __line="${LINENO}"
  if [[ -n "${__mailpitctl_cov_file}" && "$(basename "${__src}")" == "mailpitctl" ]]; then
    printf "%s\n" "${__line}" >> "${__mailpitctl_cov_file}"
  fi
}' DEBUG
"""


class MailpitctlTestCase(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        COVERAGE_TRACE.unlink(missing_ok=True)
        COVERAGE_XML.unlink(missing_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._write_coverage_report()

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)
        self.project = self.workdir / "project"
        self.project.mkdir()
        self.bin_dir = self.workdir / "bin"
        self.bin_dir.mkdir()

        self.script = self.project / "mailpitctl"
        shutil.copy2(SCRIPT_SOURCE, self.script)
        self.script.chmod(self.script.stat().st_mode | stat.S_IXUSR)
        shutil.copy2(REPO_ROOT / "compose.yml", self.project / "compose.yml")

        self.state_path = self.workdir / "state.json"
        self.log_path = self.workdir / "docker-calls.jsonl"
        self.trace_script = self.workdir / "trace.bash"
        self.trace_script.write_text(TRACE_SCRIPT, encoding="utf-8")

        docker_path = self.bin_dir / "docker"
        docker_path.write_text(FAKE_DOCKER, encoding="utf-8")
        docker_path.chmod(docker_path.stat().st_mode | stat.S_IXUSR)

        self.write_state()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_state(self, **overrides: object) -> None:
        state = {
            "compose_exists": False,
            "compose_ok": True,
            "health": "",
            "info_ok": True,
            "legacy_exists": False,
            "logs_output": "mailpit log line",
            "running": False,
        }
        state.update(overrides)
        self.state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")

    def read_state(self) -> dict[str, object]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def docker_calls(self) -> list[dict[str, object]]:
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def run_ctl(
        self,
        *args: str,
        env: dict[str, str] | None = None,
        path: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        run_env = {
            "BASH_ENV": str(self.trace_script),
            "FAKE_DOCKER_LOG": str(self.log_path),
            "FAKE_DOCKER_STATE": str(self.state_path),
            "MAILPITCTL_COVERAGE_FILE": str(COVERAGE_TRACE),
            "PATH": path or f"{self.bin_dir}:{os.environ['PATH']}",
        }
        if env:
            run_env.update(env)

        return subprocess.run(
            [str(self.script), *args],
            check=False,
            cwd=self.project,
            env=run_env,
            text=True,
            capture_output=True,
        )

    def assert_success(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def assert_failure(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_help_does_not_require_docker(self) -> None:
        result = self.run_ctl("--help")

        self.assert_success(result)
        self.assertIn("Usage:", result.stdout)
        self.assertEqual(self.docker_calls(), [])

    def test_invalid_command_prints_usage(self) -> None:
        result = self.run_ctl("bogus")

        self.assert_failure(result)
        self.assertIn("invalid command: bogus", result.stderr)
        self.assertIn("Usage:", result.stdout)

    def test_rejects_too_many_arguments_for_simple_command(self) -> None:
        result = self.run_ctl("status", "extra")

        self.assert_failure(result)
        self.assertIn("too many arguments for command: status", result.stderr)
        self.assertEqual(self.docker_calls(), [])

    def test_requires_docker_cli(self) -> None:
        bash_only = self.workdir / "bash-only"
        bash_only.mkdir()
        os.symlink(shutil.which("bash"), bash_only / "bash")

        result = self.run_ctl("status", path=str(bash_only))

        self.assert_failure(result)
        self.assertIn("Docker CLI is not installed", result.stderr)

    def test_requires_docker_daemon(self) -> None:
        self.write_state(info_ok=False)

        result = self.run_ctl("status")

        self.assert_failure(result)
        self.assertIn("unable to communicate with the Docker daemon", result.stderr)

    def test_requires_docker_compose(self) -> None:
        self.write_state(compose_ok=False)

        result = self.run_ctl("status")

        self.assert_failure(result)
        self.assertIn("Docker Compose is not installed", result.stderr)

    def test_status_reports_missing_container(self) -> None:
        result = self.run_ctl("status")

        self.assert_failure(result)
        self.assertIn("container does not exist", result.stderr)
        self.assertIn("Try running:", result.stderr)

    def test_status_reports_legacy_container_conflict(self) -> None:
        self.write_state(legacy_exists=True)

        result = self.run_ctl("status")

        self.assert_failure(result)
        self.assertIn("container is not managed by Docker Compose", result.stderr)
        self.assertIn("docker rm -f mailpit", result.stderr)

    def test_status_reports_running_and_healthy(self) -> None:
        self.write_state(compose_exists=True, health="healthy", running=True)

        result = self.run_ctl("status")

        self.assert_success(result)
        self.assertIn("Container is running", result.stdout)
        self.assertIn("Container is healthy", result.stdout)
        self.assertIn("NAME", result.stdout)

    def test_status_warns_when_running_but_unhealthy(self) -> None:
        self.write_state(compose_exists=True, health="starting", running=True)

        result = self.run_ctl("status")

        self.assert_success(result)
        self.assertIn("Container is running", result.stdout)
        self.assertIn("not healthy", result.stderr)

    def test_status_reports_stopped_container(self) -> None:
        self.write_state(compose_exists=True, health="", running=False)

        result = self.run_ctl("status")

        self.assert_success(result)
        self.assertIn("Container is stopped", result.stdout)

    def test_start_creates_container_with_defaults(self) -> None:
        result = self.run_ctl("start")

        self.assert_success(result)
        self.assertIn("Started container: mailpit", result.stdout)
        self.assertIn("http://127.0.0.1:8025", result.stdout)
        self.assertIn("SMTP: 127.0.0.1:1025", result.stdout)
        self.assertTrue(self.read_state()["running"])
        up_calls = [call for call in self.docker_calls() if call["command"] == "compose up"]
        self.assertEqual(len(up_calls), 1)
        self.assertIn("--wait-timeout", up_calls[0]["args"])
        self.assertNotIn("--env-file", up_calls[0]["compose_options"])

    def test_start_uses_config_env_and_passes_env_file_to_compose(self) -> None:
        (self.project / "config.env").write_text(
            dedent(
                """
                MAILPIT_WEB_BIND=0.0.0.0
                MAILPIT_WEB_PORT=18025
                MAILPIT_SMTP_BIND=127.0.0.1
                MAILPIT_SMTP_PORT=11025
                MAILPIT_WAIT_TIMEOUT=7
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        result = self.run_ctl("start")

        self.assert_success(result)
        self.assertIn("http://0.0.0.0:18025", result.stdout)
        self.assertIn("SMTP: 127.0.0.1:11025", result.stdout)
        up_call = [call for call in self.docker_calls() if call["command"] == "compose up"][0]
        self.assertIn("--env-file", up_call["compose_options"])
        self.assertIn(str(self.project / "config.env"), up_call["compose_options"])
        self.assertEqual(up_call["args"][up_call["args"].index("--wait-timeout") + 1], "7")

    def test_environment_overrides_defaults_without_config_file(self) -> None:
        result = self.run_ctl(
            "start",
            env={
                "MAILPIT_WEB_BIND": "127.0.0.2",
                "MAILPIT_WEB_PORT": "9001",
                "MAILPIT_SMTP_BIND": "127.0.0.3",
                "MAILPIT_SMTP_PORT": "9002",
            },
        )

        self.assert_success(result)
        self.assertIn("http://127.0.0.2:9001", result.stdout)
        self.assertIn("SMTP: 127.0.0.3:9002", result.stdout)

    def test_start_running_healthy_container_is_noop(self) -> None:
        self.write_state(compose_exists=True, health="healthy", running=True)

        result = self.run_ctl("up")

        self.assert_success(result)
        self.assertIn("Container is already running", result.stdout)
        self.assertFalse(any(call["command"] == "compose up" for call in self.docker_calls()))

    def test_start_running_unhealthy_container_waits_for_health(self) -> None:
        self.write_state(compose_exists=True, health="starting", running=True)

        result = self.run_ctl("start")

        self.assert_success(result)
        self.assertIn("not healthy", result.stderr)
        self.assertIn("Container is running and healthy", result.stdout)
        self.assertTrue(any(call["command"] == "compose up" for call in self.docker_calls()))

    def test_start_rejects_legacy_container_conflict(self) -> None:
        self.write_state(legacy_exists=True)

        result = self.run_ctl("start")

        self.assert_failure(result)
        self.assertIn("container is not managed by Docker Compose", result.stderr)

    def test_start_reports_compose_up_failure(self) -> None:
        self.write_state(up_fails=True)

        result = self.run_ctl("start")

        self.assert_failure(result)
        self.assertIn("failed to wait container", result.stderr)

    def test_update_pulls_and_recreates(self) -> None:
        self.write_state(compose_exists=True, health="healthy", running=True)

        result = self.run_ctl("update")

        self.assert_success(result)
        commands = [call["command"] for call in self.docker_calls()]
        self.assertIn("compose pull", commands)
        self.assertIn("compose up", commands)
        self.assertIn("Updated container: mailpit", result.stdout)

    def test_update_rejects_legacy_container_conflict(self) -> None:
        self.write_state(legacy_exists=True)

        result = self.run_ctl("update")

        self.assert_failure(result)
        self.assertIn("container is not managed by Docker Compose", result.stderr)

    def test_update_reports_pull_failure(self) -> None:
        self.write_state(compose_exists=True, pull_fails=True)

        result = self.run_ctl("update")

        self.assert_failure(result)
        self.assertIn("failed to update container", result.stderr)

    def test_stop_requires_existing_compose_container(self) -> None:
        result = self.run_ctl("stop")

        self.assert_failure(result)
        self.assertIn("container does not exist", result.stderr)

    def test_stop_running_container(self) -> None:
        self.write_state(compose_exists=True, health="healthy", running=True)

        result = self.run_ctl("down")

        self.assert_success(result)
        self.assertIn("Stopped container", result.stdout)
        self.assertFalse(self.read_state()["running"])

    def test_stop_stopped_container_is_noop(self) -> None:
        self.write_state(compose_exists=True, running=False)

        result = self.run_ctl("stop")

        self.assert_success(result)
        self.assertIn("Container is not running", result.stdout)
        self.assertFalse(any(call["command"] == "compose stop" for call in self.docker_calls()))

    def test_stop_reports_compose_failure(self) -> None:
        self.write_state(compose_exists=True, health="healthy", running=True, stop_fails=True)

        result = self.run_ctl("stop")

        self.assert_failure(result)
        self.assertIn("failed to stop container", result.stderr)

    def test_restart_running_container(self) -> None:
        self.write_state(compose_exists=True, health="healthy", running=True)

        result = self.run_ctl("restart")

        self.assert_success(result)
        self.assertIn("Restarted container: mailpit", result.stdout)
        commands = [call["command"] for call in self.docker_calls()]
        self.assertIn("compose restart", commands)
        self.assertIn("compose up", commands)

    def test_restart_stopped_container_starts_it(self) -> None:
        self.write_state(compose_exists=True, health="", running=False)

        result = self.run_ctl("restart")

        self.assert_success(result)
        self.assertIn("container is stopped; starting it now", result.stderr)
        commands = [call["command"] for call in self.docker_calls()]
        self.assertIn("compose start", commands)
        self.assertIn("compose up", commands)

    def test_restart_reports_compose_failure(self) -> None:
        self.write_state(compose_exists=True, health="healthy", restart_fails=True, running=True)

        result = self.run_ctl("restart")

        self.assert_failure(result)
        self.assertIn("failed to restart container", result.stderr)

    def test_destroy_removes_container(self) -> None:
        self.write_state(compose_exists=True, health="healthy", running=True)

        result = self.run_ctl("destroy")

        self.assert_success(result)
        self.assertIn("Destroyed container", result.stdout)
        self.assertFalse(self.read_state()["compose_exists"])

    def test_destroy_reports_down_failure(self) -> None:
        self.write_state(compose_exists=True, down_fails=True, running=True)

        result = self.run_ctl("destroy")

        self.assert_failure(result)
        self.assertIn("failed to destroy container", result.stderr)

    def test_logs_forwards_options(self) -> None:
        self.write_state(compose_exists=True, health="healthy", logs_output="hello from mailpit")

        result = self.run_ctl("logs", "--tail", "20", "--follow")

        self.assert_success(result)
        self.assertIn("hello from mailpit", result.stdout)
        logs_call = [call for call in self.docker_calls() if call["command"] == "compose logs"][0]
        self.assertEqual(logs_call["args"], ["--tail", "20", "--follow", "mailpit"])

    def test_logs_requires_existing_container(self) -> None:
        result = self.run_ctl("logs", "--tail", "5")

        self.assert_failure(result)
        self.assertIn("container does not exist", result.stderr)

    @staticmethod
    def _executable_lines() -> list[int]:
        lines: list[int] = []
        in_heredoc = False
        in_array_literal = False

        for number, raw_line in enumerate(SCRIPT_SOURCE.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = raw_line.strip()

            if in_heredoc:
                if stripped == "EOF":
                    in_heredoc = False
                continue

            if not stripped or stripped.startswith("#"):
                continue

            if in_array_literal:
                if stripped == ")":
                    in_array_literal = False
                continue

            if stripped in {"}", ";;", "esac", "fi", "done", "else"}:
                continue

            if stripped.endswith("() {"):
                continue

            lines.append(number)

            if "<< EOF" in raw_line:
                in_heredoc = True
            elif stripped.endswith("("):
                in_array_literal = True

        return lines

    @classmethod
    def _write_coverage_report(cls) -> None:
        executable_lines = cls._executable_lines()
        covered_trace_lines: set[int] = set()
        if COVERAGE_TRACE.exists():
            covered_trace_lines = {
                int(line)
                for line in COVERAGE_TRACE.read_text(encoding="utf-8").splitlines()
                if line.strip().isdigit()
            }

        covered = cls._normalize_covered_lines(executable_lines, covered_trace_lines)
        covered_executable = [line for line in executable_lines if line in covered]
        coverage = 100.0 * len(covered_executable) / len(executable_lines)
        cls._write_cobertura_xml(executable_lines, covered)

        if coverage < MINIMUM_LINE_COVERAGE:
            raise AssertionError(
                f"mailpitctl line coverage {coverage:.2f}% is below "
                f"{MINIMUM_LINE_COVERAGE:.2f}%"
            )

    @staticmethod
    def _normalize_covered_lines(executable_lines: list[int], trace_lines: set[int]) -> set[int]:
        executable = set(executable_lines)
        covered: set[int] = set()

        for trace_line in trace_lines:
            for candidate in (trace_line, trace_line - 1, trace_line - 2):
                if candidate in executable:
                    covered.add(candidate)

        return covered

    @staticmethod
    def _write_cobertura_xml(executable_lines: list[int], covered: set[int]) -> None:
        hits = {line: 1 if line in covered else 0 for line in executable_lines}
        line_rate = sum(hits.values()) / len(executable_lines)
        timestamp = str(int(time.time()))

        coverage = ET.Element(
            "coverage",
            {
                "line-rate": f"{line_rate:.4f}",
                "branch-rate": "0",
                "version": "mailpitctl-unittest",
                "timestamp": timestamp,
                "lines-covered": str(sum(hits.values())),
                "lines-valid": str(len(executable_lines)),
                "branches-covered": "0",
                "branches-valid": "0",
            },
        )
        ET.SubElement(coverage, "sources").append(ET.Element("source"))
        coverage.find("sources/source").text = str(REPO_ROOT)

        packages = ET.SubElement(coverage, "packages")
        package = ET.SubElement(
            packages,
            "package",
            {"name": "mailpit-dev-tooling", "line-rate": f"{line_rate:.4f}", "branch-rate": "0"},
        )
        classes = ET.SubElement(package, "classes")
        class_node = ET.SubElement(
            classes,
            "class",
            {
                "name": "mailpitctl",
                "filename": "mailpitctl",
                "line-rate": f"{line_rate:.4f}",
                "branch-rate": "0",
            },
        )
        lines_node = ET.SubElement(class_node, "lines")
        for number in executable_lines:
            ET.SubElement(lines_node, "line", {"number": str(number), "hits": str(hits[number])})

        ET.ElementTree(coverage).write(COVERAGE_XML, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)

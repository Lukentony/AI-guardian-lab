"""Onboarding CLI: parsing, validation, diagnostics and the demo contract."""

from __future__ import annotations

import json
import socket
import stat
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.onboarding import checks as check_module
from tools.onboarding import cli
from tools.onboarding import demo as demo_module
from tools.onboarding.checks import Check, port_is_free
from tools.onboarding.demo import run_demo
from tools.onboarding.envfile import (
    EnvError,
    generate_env,
    read_env_file,
    validate_env,
    write_env_file,
)


def _values() -> dict[str, str]:
    return generate_env("demo", 1000, 1000)


def test_read_env_parses_quotes_comments_and_export(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text(
        "# comment\n\nexport API_KEY=\"abc123\"\nUI_PASSWORD='secret value'\n",
        encoding="utf-8",
    )

    values = read_env_file(path)

    assert values == {"API_KEY": "abc123", "UI_PASSWORD": "secret value"}


def test_read_env_rejects_duplicates_and_invalid_keys(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.env"
    duplicate.write_text("API_KEY=a\nAPI_KEY=b\n", encoding="utf-8")
    with pytest.raises(EnvError, match="duplicate"):
        read_env_file(duplicate)

    invalid = tmp_path / "invalid.env"
    invalid.write_text("not a key\n", encoding="utf-8")
    with pytest.raises(EnvError):
        read_env_file(invalid)


def test_generated_configuration_is_private_complete_and_not_overwritten(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    values = _values()

    write_env_file(path, values)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert read_env_file(path) == values
    assert len({values["API_KEY"], values["LOG_HMAC_KEY"], values["TASK_API_KEY"]}) == 3
    with pytest.raises(EnvError):
        write_env_file(path, values)


def test_validation_rejects_shared_secrets_placeholders_and_unsafe_demo() -> None:
    values = _values()
    assert [issue for issue in validate_env(values) if issue.level == "error"] == []

    values["TASK_API_KEY"] = values["API_KEY"]
    assert any("distinct" in issue.message for issue in validate_env(values))

    values = _values()
    values["EXECUTE_COMMANDS"] = "true"
    assert any("execution disabled" in issue.message for issue in validate_env(values, "demo"))

    values = _values()
    values["GUARDIAN_PORT"] = values["AGENT_PORT"]
    assert any(issue.key == "ports" for issue in validate_env(values))

    values = _values()
    values["UI_PASSWORD"] = "CHANGE_ME"
    assert any(issue.key == "UI_PASSWORD" for issue in validate_env(values))


def test_port_probe_detects_an_active_listener() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = int(sock.getsockname()[1])
        assert port_is_free("127.0.0.1", port) is False
    assert port_is_free("127.0.0.1", port) is True


class FakeGuardian(BaseHTTPRequestHandler):
    total = 0
    reject_all = False

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"status": "healthy"})
            return
        if self.path == "/audit":
            stats = {"total": FakeGuardian.total, "executed": 0, "rejected": FakeGuardian.total}
            self._json(200, {"stats": stats, "commands": []})
            return
        if self.path == "/":
            if not self.headers.get("Authorization"):
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="test"')
                self.end_headers()
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"dashboard")
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/validate":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        approved = (not FakeGuardian.reject_all) and payload.get("command") == "ls /tmp"
        FakeGuardian.total += 1
        self._json(
            200,
            {
                "approved": approved,
                "intent_source": "mapping" if approved else "shell",
                "reason": "Approved" if approved else "Blocked for the demo",
            },
        )


@pytest.fixture
def fake_guardian() -> Iterator[tuple[int, int, ThreadingHTTPServer, ThreadingHTTPServer]]:
    FakeGuardian.total = 0
    FakeGuardian.reject_all = False

    def start() -> tuple[ThreadingHTTPServer, int]:
        server = ThreadingHTTPServer(("127.0.0.1", 0), FakeGuardian)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, int(server.server_address[1])

    guardian, guardian_port = start()
    ui, ui_port = start()
    try:
        yield guardian_port, ui_port, guardian, ui
    finally:
        for server in (guardian, ui):
            server.shutdown()
            server.server_close()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _demo_values(guardian_port: int, ui_port: int) -> dict[str, str]:
    values = _values()
    values["GUARDIAN_PORT"] = str(guardian_port)
    values["AGENT_PORT"] = str(_free_port())
    values["UI_PORT"] = str(ui_port)
    return values


def _fake_audit(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (root / "state/audit").mkdir(parents=True)
    (root / "state/audit/audit.db").write_bytes(b"")
    monkeypatch.setattr(
        demo_module,
        "check_audit_chain",
        lambda *_: [Check("audit", "signature chain", True, True, "test chain")],
    )


def test_demo_passes_against_the_expected_contract(
    tmp_path: Path,
    fake_guardian: tuple[int, int, ThreadingHTTPServer, ThreadingHTTPServer],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guardian_port, ui_port, _, _ = fake_guardian
    _fake_audit(tmp_path, monkeypatch)
    messages: list[str] = []

    code = run_demo(
        tmp_path,
        tmp_path / ".env",
        tmp_path / "docker-compose.yml",
        start=False,
        values=_demo_values(guardian_port, ui_port),
        out=messages.append,
    )

    assert code == 0
    output = "\n".join(messages)
    assert "5/5 cases" in output
    assert "Result:   PASS" in output
    assert "+5 decisions" in output


def test_demo_fails_when_a_decision_diverges(
    tmp_path: Path,
    fake_guardian: tuple[int, int, ThreadingHTTPServer, ThreadingHTTPServer],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guardian_port, ui_port, _, _ = fake_guardian
    _fake_audit(tmp_path, monkeypatch)
    FakeGuardian.reject_all = True
    messages: list[str] = []

    code = run_demo(
        tmp_path,
        tmp_path / ".env",
        tmp_path / "docker-compose.yml",
        start=False,
        values=_demo_values(guardian_port, ui_port),
        out=messages.append,
    )

    assert code == 1
    assert "Result:   FAIL" in "\n".join(messages)


def test_compose_up_places_build_after_the_subcommand(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    class Result:
        returncode = 0

    def fake_run(command: list[str], **kwargs: object) -> Result:
        calls.append(command)
        return Result()

    monkeypatch.setattr(check_module.subprocess, "run", fake_run)

    code = check_module.compose_up(
        tmp_path,
        tmp_path / ".env",
        tmp_path / "docker-compose.yml",
        build=True,
    )

    assert code == 0
    assert calls[0][calls[0].index("up") + 1] == "--build"


def test_compose_up_skips_build_for_an_image_only_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("services:\n  demo:\n    image: python:3.11-slim\n", encoding="utf-8")
    calls: list[list[str]] = []

    class Result:
        returncode = 0

    def fake_run(command: list[str], **kwargs: object) -> Result:
        calls.append(command)
        return Result()

    monkeypatch.setattr(check_module.subprocess, "run", fake_run)

    code = check_module.compose_up(tmp_path, tmp_path / ".env", compose, build=True)

    assert code == 0
    assert "--build" not in calls[0]


def test_setup_creates_config_without_printing_secrets(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ok = [Check("docker", "daemon", True, True, "ok")]
    with (
        patch.object(cli, "check_docker", return_value=ok),
        patch.object(cli, "check_ports", return_value=ok),
        patch.object(cli, "compose_up") as compose_up,
    ):
        code = cli.main(["--root", str(tmp_path), "setup", "--no-start"])

    assert code == 0
    compose_up.assert_not_called()
    env_file = tmp_path / ".env"
    assert env_file.is_file()
    values = read_env_file(env_file)
    output = capsys.readouterr().out
    assert values["API_KEY"] not in output
    assert values["UI_PASSWORD"] not in output
    assert "Secrets are not printed" in output


def test_setup_refuses_to_overwrite_an_existing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    existing = tmp_path / ".env"
    existing.write_text("API_KEY=keep-me\n", encoding="utf-8")

    code = cli.main(["--root", str(tmp_path), "setup", "--no-start"])

    assert code == 2
    assert "already exists" in capsys.readouterr().err
    assert existing.read_text(encoding="utf-8") == "API_KEY=keep-me\n"


def test_doctor_json_is_redacted_when_configuration_is_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["--root", str(tmp_path), "doctor", "--json"])

    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["component"] == "config"
    assert "API_KEY" not in json.dumps(payload)

import re
import time

import pytest

from database.audit_logger import mask_secrets
from guardian.guardian import main
from guardian.guardian.shell_commands import UnsupportedShellError, extract_binaries


@pytest.mark.parametrize(
    "command",
    ["ls /tmp", "cat README.md", "pwd", "echo hello", "date", "df -h", "/usr/bin/ls /tmp"],
)
def test_safe_production_policy(command):
    assert main.validate_command(command, "list project information")[0] is True


@pytest.mark.parametrize(
    "command,task",
    [
        ("curl http://example.com", "list all files"),
        ("ls /tmp && curl http://example.com", "list all files"),
        ("cat README.md > /tmp/target", "read project notes"),
        ("echo hello >> /tmp/target", "list project information"),
        ("/tmp/ls /tmp", "list all files"),
        ("./ls /tmp", "list all files"),
        ("PATH=/tmp ls", "list all files"),
        ("LD_PRELOAD=/tmp/library.so ls", "list all files"),
        ("ls & curl http://example.com", "list all files"),
        ("echo $(date)", "print current date"),
        ("echo `date`", "print current date"),
        ("ls /tmp\ncat README.md", "list all files"),
        ("ls *", "list all files"),
        ("ls", ""),
        ("ls", None),
        (None, "list all files"),
        ("rm -rf /", "delete all files"),
        ("echo 'cm0gLXJmIC90bXA=' | base64 -d", "print message"),
    ],
)
def test_security_regressions(command, task):
    assert main.validate_command(command, task)[0] is False


def test_length_limit():
    assert "exceeds max length" in main.validate_command("ls " + "a" * 1100, "list all files")[1]


def test_normalization_is_only_an_additional_view():
    assert main.normalize_command("ls${IFS}-la") == "ls -la"
    assert main.normalize_command("echo '6964' | xxd -r -p") == "id"
    assert main.normalize_command("echo 'cm0gLXJmIC90bXA=' | base64 -d") == "rm -rf /tmp"
    assert not main.validate_command("ls${IFS}-la", "list all files")[0]


def test_binaries_and_redirects():
    assert extract_binaries("ls>/dev/null && cat < input.txt > output.txt") == ["ls", "cat"]
    with pytest.raises(UnsupportedShellError):
        extract_binaries("0<<EOF cat")


def test_regex_timeout_is_real_and_denies(monkeypatch):
    monkeypatch.setattr(main, "REGEX_TIMEOUT", 0.001)
    pattern = main.safe_compile("(a|aa)+$")
    started = time.monotonic()
    with pytest.raises(main.RegexEvaluationError):
        main.regex_match_with_timeout(pattern, "a" * 300 + "!")
    monkeypatch.setattr(main, "patterns", [(pattern, "test", False)])
    assert main.validate_command("echo " + "a" * 300 + "!", "print message")[2] == "regex_error"
    assert time.monotonic() - started < 1


def test_regex_semantics_not_rewritten():
    compiled = main.safe_compile("a.*b")
    assert compiled is not None and compiled.pattern == "a.*b"


def test_pattern_failure_denies(monkeypatch):
    monkeypatch.setattr(main, "patterns", [(re.compile("x"), "test", False)])

    def fail(*args):
        raise main.RegexEvaluationError()

    monkeypatch.setattr(main, "regex_match_with_timeout", fail)
    assert main.validate_command("ls", "list all files")[0] is False


def test_secret_masking():
    raw = "API_KEY: sk-1234567890abcdef12345678"
    assert "12345678" not in mask_secrets(raw)


@pytest.mark.parametrize("data", [None, [], "text", {"command": []}, {"command": "ls", "task": 2}])
def test_validate_rejects_invalid_json(client, headers, data):
    assert client.post("/validate", json=data, headers=headers).status_code == 400


def test_validation_is_not_execution(client, headers):
    response = client.post(
        "/validate", json={"command": "ls /tmp", "task": "list files"}, headers=headers
    )
    assert response.status_code == 200 and response.json["approved"] is True
    connection = main.connect(main.DB_PATH)
    try:
        assert connection.execute("SELECT status FROM command_log").fetchone()[0] == "approved"
    finally:
        connection.close()
    report = {
        "validation_id": response.json["validation_id"],
        "command": "ls /tmp",
        "status": "simulated",
    }
    assert client.post("/report", json=report, headers=headers).status_code == 200
    assert client.post("/report", json=report, headers=headers).status_code == 200
    report["command"] = "cat private.txt"
    assert client.post("/report", json=report, headers=headers).status_code == 409


def test_audit_view_requires_auth_and_counts_decisions(client, headers):
    assert client.get("/audit").status_code == 401
    response = client.post(
        "/validate", json={"command": "ls /tmp", "task": "list files"}, headers=headers
    )
    client.post("/validate", json={"command": "rm -rf /", "task": "list files"}, headers=headers)
    report = {
        "validation_id": response.json["validation_id"],
        "command": "ls /tmp",
        "status": "simulated",
    }
    assert client.post("/report", json=report, headers=headers).status_code == 200
    result = client.get("/audit", headers=headers)
    assert result.status_code == 200
    assert result.json["stats"] == {"total": 2, "executed": 0, "rejected": 1}
    assert len(result.json["commands"]) == 3
    assert result.json["commands"][0]["status"] == "simulated"


def test_audit_view_limits_rows(client, headers):
    for index in range(25):
        main.log_command("list files", f"ls /tmp/{index}", "approved", path=main.DB_PATH)
    result = client.get("/audit", headers=headers)
    assert result.json["stats"]["total"] == 25
    assert len(result.json["commands"]) == 20
    assert result.json["commands"][0]["command"] == "ls /tmp/24"


def test_audit_view_unavailable(client, headers, monkeypatch):
    import sqlite3

    def unavailable(*args):
        raise sqlite3.OperationalError("unavailable")

    monkeypatch.setattr(main, "connect", unavailable)
    assert client.get("/audit", headers=headers).status_code == 503


def test_audit_failure_never_authorizes(client, headers, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("unavailable")

    monkeypatch.setattr(main, "log_command", fail)
    response = client.post(
        "/validate", json={"command": "ls", "task": "list files"}, headers=headers
    )
    assert response.status_code == 503 and response.json["approved"] is False

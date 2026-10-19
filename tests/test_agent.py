from types import SimpleNamespace

import pytest
import requests

from agent.agent import main as agent


@pytest.fixture
def agent_client(monkeypatch):
    monkeypatch.setattr(agent, "API_KEY", "ci-test-key")
    monkeypatch.setattr(agent, "EXECUTE_COMMANDS", False)
    agent.limiter.reset()
    agent.app.config["TESTING"] = True
    return agent.app.test_client()


def test_clean_command():
    assert agent.clean_command("```bash\nls -la\n```") == "ls -la"
    assert agent.clean_command("pwd") == "pwd"
    assert agent.clean_command("echo `date`") == "echo `date`"


@pytest.mark.parametrize(
    "payload,status",
    [
        ({"approved": "true", "validation_id": "1"}, 200),
        ({}, 200),
        ({"approved": True}, 200),
        ({"approved": True, "validation_id": "1"}, 500),
    ],
)
def test_invalid_authorization_never_executes(
    agent_client, headers, requests_mock, monkeypatch, payload, status
):
    monkeypatch.setattr(agent, "generate_command", lambda task: "ls /tmp")
    requests_mock.post(f"{agent.GUARDIAN_URL}/validate", json=payload, status_code=status)

    def forbidden(command):
        pytest.fail("Command must not execute")

    monkeypatch.setattr(agent, "run_command", forbidden)
    assert (
        agent_client.post("/execute", json={"task": "list all files"}, headers=headers).status_code
        == 502
    )


def test_dry_run_and_outcome_report(agent_client, headers, requests_mock, monkeypatch):
    monkeypatch.setattr(agent, "generate_command", lambda task: "ls /tmp")
    requests_mock.post(
        f"{agent.GUARDIAN_URL}/validate", json={"approved": True, "validation_id": "example-id"}
    )
    report = requests_mock.post(f"{agent.GUARDIAN_URL}/report", json={"status": "logged"})
    result = agent_client.post("/execute", json={"task": "list all files"}, headers=headers)
    assert result.status_code == 200 and result.json["status"] == "simulated"
    assert report.last_request.json()["status"] == "simulated"


def test_real_execution_requires_registered_task(agent_client, headers, monkeypatch):
    monkeypatch.setattr(agent, "EXECUTE_COMMANDS", True)
    assert (
        agent_client.post("/execute", json={"task": "list all files"}, headers=headers).status_code
        == 400
    )


def test_lost_report_does_not_trigger_reexecution(
    agent_client, headers, requests_mock, monkeypatch
):
    monkeypatch.setattr(agent, "generate_command", lambda task: "ls /tmp")
    requests_mock.post(
        f"{agent.GUARDIAN_URL}/validate", json={"approved": True, "validation_id": "example-id"}
    )
    requests_mock.post(f"{agent.GUARDIAN_URL}/report", exc=requests.Timeout)
    response = agent_client.post("/execute", json={"task": "list files"}, headers=headers)
    assert response.status_code == 503 and response.json["status"] == "outcome_unreported"
    assert response.json["execution_may_have_occurred"] is False


def test_subprocess_does_not_inherit_credentials(monkeypatch):
    calls = []

    def run(*args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(stdout="ok", stderr="", returncode=0)

    monkeypatch.setattr(agent.subprocess, "run", run)
    assert agent.run_command("ls")["exit_code"] == 0
    assert "API_KEY" not in calls[0]["env"] and "BASH_ENV" not in calls[0]["env"]
    assert calls[0]["cwd"] == agent.EXECUTION_WORKSPACE


@pytest.mark.parametrize("payload", [[], None, "hello", {"task": 3}, {"task": ""}])
def test_invalid_requests(agent_client, headers, payload):
    assert agent_client.post("/execute", json=payload, headers=headers).status_code == 400

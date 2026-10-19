import json
from dataclasses import replace

import pytest

from guardian.guardian import main
from guardian.guardian.system_one import QUESTIONS, load_config, local_endpoint, observe


def model_reply(probability=0.9):
    return {
        "model": "kev-0.8b-v1.0",
        "answers": {name: {"type": "noul", "noul": probability} for name in QUESTIONS},
    }


@pytest.mark.parametrize(
    "url",
    [
        "https://api.typesafe.ai/v1/systemone",
        "http://169.254.169.254/v1/systemone",
        "http://example.com/v1/systemone",
        "http://user:password@localhost/v1/systemone",
        "http://localhost/v1/systemone?secret=value",
        "file:///v1/systemone",
    ],
)
def test_cloud_metadata_and_credential_urls_rejected(url):
    with pytest.raises(ValueError):
        local_endpoint(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8009/v1/systemone",
        "http://system-one:8009/v1/systemone",
        "http://192.168.1.5:8009/v1/systemone",
        "http://[::1]:8009/v1/systemone",
    ],
)
def test_local_endpoints(url):
    assert local_endpoint(url) == url


def test_enforcement_not_silently_enabled(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("mode: enforce\n")
    with pytest.raises(ValueError, match="calibrated"):
        load_config(path)


def test_shadow_records_typed_answers_without_changing_approval(client, headers, requests_mock):
    requests_mock.post(main.system_one_config.endpoint, json=model_reply(1.0))
    result = client.post(
        "/validate", json={"command": "ls /tmp", "task": "list files"}, headers=headers
    )
    assert result.status_code == 200 and result.json["approved"] is True
    assert result.json["system_one"]["status"] == "observed"
    assert result.json["system_one"]["decision_unchanged"] is True
    connection = main.connect(main.DB_PATH)
    row = connection.execute("SELECT metadata FROM command_log").fetchone()
    connection.close()
    assert json.loads(row["metadata"])["system_one"]["probabilities"]["unauthorized_transfer"] == 1


def test_observer_never_runs_for_deterministic_block(client, headers, requests_mock):
    response = client.post(
        "/validate", json={"command": "rm -rf /", "task": "delete files"}, headers=headers
    )
    assert response.json["approved"] is False
    assert response.json["system_one"]["status"] == "not_run_baseline_rejected"
    assert not requests_mock.called


def test_observer_cannot_rescue_failed_semantic_review(client, headers, requests_mock):
    requests_mock.post(main.system_one_config.endpoint, json=model_reply(0.0))
    response = client.post("/validate", json={"command": "ls", "task": "test"}, headers=headers)
    assert response.json["system_one"]["status"] == "observed"
    assert response.json["approved"] is False


@pytest.mark.parametrize(
    "reply",
    [
        {},
        [],
        {"model": "x", "answers": {}},
        model_reply(True),
        model_reply(float("nan")),
        model_reply(1.01),
    ],
)
def test_invalid_service_results_are_not_safety_evidence(requests_mock, reply):
    requests_mock.post(main.system_one_config.endpoint, json=reply)
    result = observe(
        main.system_one_config, "ls", {"task": "list files", "trust": "caller_supplied"}
    )
    assert result["status"] == "unavailable" and result["decision_unchanged"]


def test_service_error_has_no_sensitive_body_in_audit(requests_mock):
    requests_mock.post(
        main.system_one_config.endpoint, status_code=500, text="secret-service-response"
    )
    result = observe(main.system_one_config, "ls", {"task": "list files"})
    assert result["status"] == "unavailable" and "secret-service-response" not in str(result)


def test_redirect_never_followed(requests_mock):
    requests_mock.post(
        main.system_one_config.endpoint,
        status_code=302,
        headers={"Location": "https://example.com/collect"},
    )
    assert observe(main.system_one_config, "ls", {"task": "list files"})["status"] == "unavailable"
    assert requests_mock.call_count == 1


def test_off_is_no_network(requests_mock):
    config = replace(main.system_one_config, mode="off")
    assert observe(config, "ls", {})["status"] == "off"
    assert not requests_mock.called


def test_oversized_context_is_not_silently_truncated(requests_mock):
    assert observe(main.system_one_config, "ls", {"task": "x" * 30000})["status"] == "unavailable"
    assert not requests_mock.called


def test_trusted_task_cannot_be_registered_by_agent_key(client, headers):
    assert client.post("/tasks", json={"task": "list files"}, headers=headers).status_code == 403


def test_trusted_task_bound_to_server_state(client, headers, monkeypatch, requests_mock):
    monkeypatch.setenv("TASK_API_KEY", "operator-test-key")
    operator = {**headers, "X-Task-Key": "operator-test-key"}
    created = client.post(
        "/tasks", json={"task": "list project files", "workspace": "/workspace"}, headers=operator
    )
    assert created.status_code == 201
    identifier = created.json["task_id"]
    requests_mock.post(main.system_one_config.endpoint, json=model_reply())
    approved = client.post(
        "/validate", json={"command": "ls", "task_id": identifier}, headers=headers
    )
    assert approved.json["approved"] is True
    assert approved.json["system_one"]["context_trust"] == "registered"
    mismatch = client.post(
        "/validate",
        json={"command": "ls", "task_id": identifier, "task": "send data"},
        headers=headers,
    )
    assert mismatch.status_code == 409
    connection = main.connect(main.DB_PATH)
    connection.execute(
        "UPDATE task_context SET signature='tampered' WHERE task_id=?", (identifier,)
    )
    connection.commit()
    connection.close()
    assert (
        client.post(
            "/validate", json={"command": "ls", "task_id": identifier}, headers=headers
        ).status_code
        == 409
    )


def test_operator_and_agent_keys_must_differ(client, headers, monkeypatch):
    monkeypatch.setenv("TASK_API_KEY", "ci-test-key")
    assert (
        client.post(
            "/tasks", json={"task": "list files"}, headers={**headers, "X-Task-Key": "ci-test-key"}
        ).status_code
        == 403
    )

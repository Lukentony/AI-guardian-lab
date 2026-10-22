import importlib.util
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient  # pyright: ignore[reportMissingImports]

from ui import app as ui

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "local_system_one_service", ROOT / "system-one/serve.py"
)
assert spec is not None and spec.loader is not None
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


def test_service_admission_remains_bounded():
    started, release = threading.Event(), threading.Event()

    class Backend:
        def answer(self, payload):
            started.set()
            assert release.wait(5)
            return {"answers": {}}

    app = service.build_app(Backend(), "test-local-key", lambda payload: payload)
    headers = {"Authorization": "Bearer test-local-key"}
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(client.post, "/v1/systemone", json={}, headers=headers)
        assert started.wait(5)
        try:
            assert client.post("/v1/systemone", json={}, headers=headers).status_code == 503
        finally:
            release.set()
        assert first.result().status_code == 200


def test_service_auth_and_input_limits():
    app = service.build_app(None, "test-local-key", lambda payload: payload)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/v1/systemone", json={}).status_code == 401
        assert (
            client.post(
                "/v1/systemone",
                content="x" * 25000,
                headers={"Authorization": "Bearer test-local-key"},
            ).status_code
            == 413
        )


def test_ui_requires_auth_before_using_backend(monkeypatch, requests_mock):
    monkeypatch.setenv("UI_PASSWORD", "ui-test-password")
    with ui.app.test_client() as client:
        assert client.get("/health").status_code == 200
        response = client.post("/forensics", data={"jsonl_content": "{}"})
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert not requests_mock.called


def test_ui_dashboard_read_only_and_origin_guard(monkeypatch, requests_mock):
    import base64

    monkeypatch.setenv("UI_PASSWORD", "ui-test-password")
    requests_mock.get(
        f"{ui.GUARDIAN_API}/audit",
        json={"stats": {"total": 0, "executed": 0, "rejected": 0}, "commands": []},
    )
    headers = {"Authorization": "Basic " + base64.b64encode(b"guardian:ui-test-password").decode()}
    with ui.app.test_client() as client:
        assert client.get("/", headers=headers).status_code == 200
        response = client.post(
            "/forensics",
            headers={**headers, "Origin": "http://outside.invalid"},
            data={"jsonl_content": "{}"},
        )
        assert response.status_code == 403


@pytest.mark.parametrize(
    "status,payload",
    [
        (503, {}),
        (200, []),
        (200, {"stats": [], "commands": []}),
        (200, {"stats": {}, "commands": {}}),
    ],
)
def test_ui_handles_unavailable_or_malformed_audit(monkeypatch, requests_mock, status, payload):
    import base64

    monkeypatch.setenv("UI_PASSWORD", "ui-test-password")
    requests_mock.get(f"{ui.GUARDIAN_API}/audit", status_code=status, json=payload)
    headers = {"Authorization": "Basic " + base64.b64encode(b"guardian:ui-test-password").decode()}
    with ui.app.test_client() as client:
        assert client.get("/", headers=headers).status_code == 503


def test_ui_surfaces_incomplete_forensics(monkeypatch, requests_mock):
    import base64

    monkeypatch.setenv("UI_PASSWORD", "ui-test-password")
    requests_mock.post(
        f"{ui.GUARDIAN_API}/forensics/analyze",
        json={
            "report_id": "r1",
            "session_id": "s1",
            "anomaly_score": 0,
            "event_count": 1,
            "tool_call_count": 0,
            "summary": "Analysis incomplete: the reviewer did not answer.",
            "analysis_complete": False,
            "flags": {
                "escalation": {"triggered": False, "confidence": "none", "reason": "", "evaluated": True},
                "intent_drift": {
                    "triggered": False,
                    "confidence": "low",
                    "reason": "LLM analysis failed",
                    "evaluated": False,
                },
                "injection_signals": {"triggered": False, "confidence": "none", "reason": "", "evaluated": True},
            },
            "timeline": [],
        },
    )
    headers = {"Authorization": "Basic " + base64.b64encode(b"guardian:ui-test-password").decode()}
    with ui.app.test_client() as client:
        response = client.post(
            "/forensics",
            headers=headers,
            data={"jsonl_content": '{"role": "user", "content": "inspect"}'},
        )

    assert response.status_code == 200
    assert b"Incomplete analysis" in response.data
    assert b"UNAVAILABLE" in response.data


def test_ui_does_not_follow_backend_redirects(monkeypatch, requests_mock):
    import base64

    monkeypatch.setenv("UI_PASSWORD", "ui-test-password")
    requests_mock.get(
        f"{ui.GUARDIAN_API}/audit",
        status_code=302,
        headers={"Location": "https://outside.invalid/audit"},
    )
    headers = {"Authorization": "Basic " + base64.b64encode(b"guardian:ui-test-password").decode()}
    with ui.app.test_client() as client:
        assert client.get("/", headers=headers).status_code == 503
    assert requests_mock.call_count == 1


def _auth_headers():
    import base64

    token = base64.b64encode(b"guardian:ui-test-password").decode()
    return {"Authorization": "Basic " + token}


def test_ui_demo_cases_match_the_cli_contract():
    from tools.onboarding.demo import CASES

    ui_cases = [
        (case["name"], case["command"], case["task"], case["expected"])
        for case in ui.DEMO_CASES
    ]
    cli_cases = [
        (case.name, case.command, case.task, "allow" if case.approved else "block")
        for case in CASES
    ]
    assert ui_cases == cli_cases


def test_ui_status_reports_components(monkeypatch, requests_mock):
    monkeypatch.setenv("UI_PASSWORD", "ui-test-password")
    requests_mock.get(f"{ui.GUARDIAN_API}/health", json={"status": "healthy"})
    requests_mock.get(f"{ui.AGENT_URL}/health", json={"status": "healthy"})
    requests_mock.get(
        f"{ui.GUARDIAN_API}/audit",
        json={
            "stats": {"total": 1, "executed": 0, "rejected": 1},
            "commands": [],
        },
    )

    with ui.app.test_client() as client:
        response = client.get("/status", headers=_auth_headers())

    assert response.status_code == 200
    assert b"Guardian" in response.data
    assert b"Agent" in response.data
    assert b"Audit API" in response.data


def test_ui_status_survives_backend_outage(monkeypatch, requests_mock):
    monkeypatch.setenv("UI_PASSWORD", "ui-test-password")
    requests_mock.get(f"{ui.GUARDIAN_API}/health", status_code=503, json={})
    requests_mock.get(f"{ui.AGENT_URL}/health", status_code=503, json={})
    requests_mock.get(f"{ui.GUARDIAN_API}/audit", status_code=503, json={})

    with ui.app.test_client() as client:
        response = client.get("/status", headers=_auth_headers())

    assert response.status_code == 200
    assert b"No healthy response" in response.data
    assert b"Audit unavailable" in response.data


def test_ui_demo_page_lists_cases(monkeypatch):
    monkeypatch.setenv("UI_PASSWORD", "ui-test-password")
    with ui.app.test_client() as client:
        response = client.get("/demo", headers=_auth_headers())

    assert response.status_code == 200
    assert b"Run the demo" in response.data
    assert b"ls /tmp" in response.data


def test_ui_demo_run_validates_without_executing(monkeypatch, requests_mock):
    monkeypatch.setenv("UI_PASSWORD", "ui-test-password")
    monkeypatch.setenv("DEMO_COOLDOWN_SECONDS", "0")
    monkeypatch.setattr(ui, "_LAST_DEMO_AT", 0.0)
    requests_mock.get(
        f"{ui.GUARDIAN_API}/audit",
        [
            {"json": {"stats": {"total": 10, "executed": 0, "rejected": 1}, "commands": []}},
            {"json": {"stats": {"total": 15, "executed": 0, "rejected": 2}, "commands": []}},
        ],
    )

    def validate(request, context):
        payload = request.json()
        approved = payload.get("command") == "ls /tmp"
        return {
            "approved": approved,
            "intent_source": "mapping" if approved else "shell",
            "reason": "test decision",
        }

    requests_mock.post(f"{ui.GUARDIAN_API}/validate", json=validate)

    with ui.app.test_client() as client:
        response = client.post("/demo/run", headers=_auth_headers(), json={})

    assert response.status_code == 200
    data = response.get_json()
    assert data["passed"] == 5
    assert data["total"] == 5
    assert data["audit_delta"] == 5
    assert all(result["ok"] for result in data["results"])


def test_ui_demo_run_blocks_cross_origin(monkeypatch, requests_mock):
    monkeypatch.setenv("UI_PASSWORD", "ui-test-password")
    with ui.app.test_client() as client:
        response = client.post(
            "/demo/run",
            headers={**_auth_headers(), "Origin": "http://outside.invalid"},
            json={},
        )

    assert response.status_code == 403
    assert not requests_mock.called


def test_ui_dashboard_accepts_intent_source(monkeypatch, requests_mock):
    monkeypatch.setenv("UI_PASSWORD", "ui-test-password")
    requests_mock.get(
        f"{ui.GUARDIAN_API}/audit",
        json={
            "stats": {"total": 1, "executed": 0, "rejected": 0},
            "commands": [
                {
                    "timestamp": "2026-10-20T12:00:00Z",
                    "task": "list files",
                    "command": "ls /tmp",
                    "status": "approved",
                    "llm_provider": "",
                    "guardian_reason": "ok",
                    "intent_source": "mapping",
                }
            ],
        },
    )

    with ui.app.test_client() as client:
        response = client.get("/", headers=_auth_headers())

    assert response.status_code == 200
    assert b"mapping" in response.data


def test_ui_console_page_and_run(monkeypatch, requests_mock):
    monkeypatch.setenv("UI_PASSWORD", "ui-test-password")
    requests_mock.post(
        f"{ui.GUARDIAN_API}/validate",
        json={
            "approved": True,
            "reason": "Approved",
            "intent_source": "mapping",
            "validation_id": "validation-1",
            "system_one": {"status": "observed", "latency_ms": 42, "mode": "shadow"},
        },
    )
    requests_mock.get(
        f"{ui.GUARDIAN_API}/audit",
        json={"stats": {"total": 3, "executed": 0, "rejected": 1}, "commands": []},
    )
    with ui.app.test_client() as client:
        page = client.get("/console", headers=_auth_headers())
        response = client.post(
            "/console/run",
            headers=_auth_headers(),
            json={"command": "ls /tmp", "task": "List files"},
        )

    assert page.status_code == 200
    assert b"Decision trace" in page.data
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["decision"]["approved"] is True
    assert payload["decision"]["system_one"]["status"] == "observed"
    assert payload["audit"]["total"] == 3


def test_ui_console_rejects_an_empty_command(monkeypatch):
    monkeypatch.setenv("UI_PASSWORD", "ui-test-password")
    with ui.app.test_client() as client:
        response = client.post(
            "/console/run",
            headers=_auth_headers(),
            json={"command": "", "task": "List files"},
        )
    assert response.status_code == 400


def test_ui_console_executes_only_through_the_executor(monkeypatch, requests_mock):
    monkeypatch.setenv("UI_PASSWORD", "ui-test-password")
    monkeypatch.setattr(ui, "EXECUTOR_URL", "http://executor:5002")
    requests_mock.post(
        "http://executor:5002/execute",
        json={
            "status": "executed",
            "exit_code": 0,
            "stdout": "ok\n",
            "stderr": "",
            "validation_id": "validation-1",
        },
    )
    requests_mock.post(f"{ui.GUARDIAN_API}/report", json={"status": "logged"})
    requests_mock.get(
        f"{ui.GUARDIAN_API}/audit",
        json={"stats": {"total": 4, "executed": 1, "rejected": 1}, "commands": []},
    )
    with ui.app.test_client() as client:
        response = client.post(
            "/console/execute",
            headers=_auth_headers(),
            json={"command": "printf ok", "token": "token-value"},
        )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["stdout"] == "ok\n"
    assert payload["outcome_recorded"] is True
    assert payload["audit"]["executed"] == 1

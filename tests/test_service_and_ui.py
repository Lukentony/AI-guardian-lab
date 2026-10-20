import importlib.util
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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

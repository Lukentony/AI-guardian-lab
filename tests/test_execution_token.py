from __future__ import annotations

from executor.app import create_app
from guardian.guardian.execution_token import issue, verify, verify_payload


def test_token_binds_command_and_expiry() -> None:
    key = "test-executor-key"
    token = issue("validation-1", "ls /tmp", key, now=1000, ttl=60)
    assert token
    assert verify(token, "ls /tmp", key, now=1001)
    assert not verify(token, "rm -rf /tmp", key, now=1001)
    assert not verify(token, "ls /tmp", "other-key", now=1001)
    assert not verify(token, "ls /tmp", key, now=1061)
    payload = verify_payload(token, "ls /tmp", key, now=1001)
    assert payload is not None and payload["vid"] == "validation-1"
    assert issue("validation-1", "ls /tmp", "", now=1000) is None


def test_executor_requires_a_single_use_token(tmp_path) -> None:
    from guardian.guardian.execution_token import issue

    key = "test-executor-key"
    token = issue("validation-1", "printf ok", key)
    app = create_app(key, str(tmp_path))
    with app.test_client() as client:
        assert client.get("/health").status_code == 200
        assert (
            client.post(
                "/execute", json={"command": "printf ok", "token": "bad"}
            ).status_code
            == 401
        )
        first = client.post("/execute", json={"command": "printf ok", "token": token})
        assert first.status_code == 200
        assert first.get_json()["stdout"] == "ok"
        replay = client.post("/execute", json={"command": "printf ok", "token": token})
        assert replay.status_code == 409

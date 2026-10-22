"""Isolated test state. No live model, network, credentials or user database."""

import importlib
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
_runtime = tempfile.TemporaryDirectory(prefix="guardian-tests-")
os.environ.update(
    {
        "TESTING": "1",
        "API_KEY": "ci-test-key",
        "LOG_HMAC_KEY": "ci-audit-key",
        "PATTERNS_PATH": str(ROOT_DIR / "guardian/config/patterns.yaml"),
        "POLICY_PATH": str(ROOT_DIR / "guardian/config/policy.yaml"),
        "DB_PATH": str(Path(_runtime.name) / "audit.db"),
        "LEARNED_PATH": str(Path(_runtime.name) / "learned.yaml"),
        "LLM_API_BASE": "http://127.0.0.1:18080/v1",
        "LLM_API_KEY": "ci-model-key",
        "SYSTEM_ONE_CONFIG": str(ROOT_DIR / "guardian/config/system_one.yaml"),
    }
)
# Historical test imports resolve to the same modules, not competing app copies.
for alias, name in [
    ("intent", "guardian.guardian.intent"),
    ("auth", "guardian.guardian.auth"),
    ("forensics", "guardian.forensics"),
    ("forensics.parser", "guardian.forensics.parser"),
    ("forensics.annotator", "guardian.forensics.annotator"),
    ("forensics.analyzer", "guardian.forensics.analyzer"),
    ("forensics.report", "guardian.forensics.report"),
    ("forensics_routes", "guardian.guardian.forensics_routes"),
    ("main", "guardian.guardian.main"),
]:
    sys.modules[alias] = importlib.import_module(name)


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch, tmp_path, requests_mock):
    from database.audit_logger import init_db
    from guardian.forensics import analyzer
    from guardian.guardian import auth, intent, main

    path = str(tmp_path / "audit.db")
    monkeypatch.setenv("DB_PATH", path)
    monkeypatch.setenv("API_KEY", "ci-test-key")
    monkeypatch.setenv("LOG_HMAC_KEY", "ci-audit-key")
    monkeypatch.setattr(auth, "API_KEY", "ci-test-key")
    monkeypatch.setattr(main, "DB_PATH", path)
    monkeypatch.setattr(main, "LEARNED_PATH", str(tmp_path / "learned.yaml"))
    init_db(path)
    main.limiter.reset()
    monkeypatch.setattr(analyzer, "_openai_chat", lambda *args, **kwargs: None)

    def offline_completion(**kwargs):
        raise RuntimeError("Live model calls are disabled in tests")

    monkeypatch.setattr(intent, "completion", offline_completion)
    # requests_mock blocks all unmatched HTTP requests by default.
    yield


@pytest.fixture
def client():
    from guardian.guardian.main import app

    app.config["TESTING"] = True
    with app.test_client() as value:
        yield value


@pytest.fixture
def headers():
    return {"X-API-Key": "ci-test-key"}

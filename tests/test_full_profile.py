"""Static and configuration-level checks for the full local profile."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from tools.onboarding.checks import _configured_models
from tools.onboarding.cli import build_parser
from tools.onboarding.demo import FULL_CASES, run_full_demo
from tools.onboarding.envfile import generate_env, validate_env

ROOT = Path(__file__).resolve().parents[1]


def _load_qualification():
    spec = importlib.util.spec_from_file_location(
        "guardian_qualification", ROOT / "system-one/qualification.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_doctor_defaults_to_the_profile_stored_in_env() -> None:
    parser = build_parser()
    assert parser.parse_args(["doctor"]).profile is None
    assert parser.parse_args(["doctor", "--profile", "full"]).profile == "full"


def test_full_profile_configures_models_and_observer_budget() -> None:
    values = generate_env("full", 1000, 1000)

    assert values["GUARDIAN_PROFILE"] == "full"
    assert values["COMPOSE_PROFILES"] == "full"
    assert values["OLLAMA_URL"] == "http://ollama:11434"
    assert values["SYSTEM_ONE_TIMEOUT_SECONDS"] == "2.0"
    assert values["INTENT_LLM_TIMEOUT_SECONDS"] == "30"
    assert values["GUARDIAN_TIMEOUT_SECONDS"] == "15"
    assert [issue for issue in validate_env(values, "full") if issue.level == "error"] == []


def test_full_profile_requires_the_observer_key() -> None:
    values = generate_env("full", 1000, 1000)
    values["SYSTEM_ONE_API_KEY"] = ""
    assert any(
        issue.level == "error" and issue.key == "SYSTEM_ONE_API_KEY"
        for issue in validate_env(values, "full")
    )


def test_full_profile_keeps_execution_disabled() -> None:
    values = generate_env("full", 1000, 1000)
    values["EXECUTE_COMMANDS"] = "true"
    issues = validate_env(values, "full")
    assert any(
        issue.level == "warning" and "not an OS-level sandbox" in issue.message for issue in issues
    )
    assert not any(issue.level == "error" for issue in issues)


def test_full_demo_cases_cover_each_decision_path() -> None:
    assert [case.name for case in FULL_CASES] == [
        "Deterministic allow",
        "Deterministic block",
        "Semantic review",
    ]
    assert [case.expected_source for case in FULL_CASES] == ["mapping", "", "llm"]
    assert [case.expected_system_one for case in FULL_CASES] == [
        "observed",
        "not_run_baseline_rejected",
        "observed",
    ]


def test_full_demo_refuses_the_default_profile(tmp_path) -> None:
    values = generate_env("demo", 1000, 1000)
    code = run_full_demo(
        tmp_path,
        tmp_path / ".env",
        tmp_path / "docker-compose.yml",
        start=False,
        build=False,
        values=values,
        out=lambda _: None,
    )
    assert code == 2


def test_configured_models_are_deduplicated() -> None:
    values = {
        "INTENT_LLM_MODEL": "ollama/qwen2.5:3b",
        "LLM_MODEL_EXPLAIN": "qwen2.5:3b",
        "LLM_MODEL_CODER": "qwen2.5-coder:3b",
    }
    assert _configured_models(values) == ["qwen2.5:3b", "qwen2.5-coder:3b"]


def test_qualification_accepts_only_the_reviewed_torch_range(monkeypatch) -> None:
    module = _load_qualification()
    versions = {"torch": "2.13.0+cpu", "kev": "0.1.0"}
    monkeypatch.setattr(module, "version", lambda name: versions[name])
    module.require_qualified_runtime()

    versions["torch"] = "2.8.0+cpu"
    with pytest.raises(RuntimeError, match="Unsupported torch"):
        module.require_qualified_runtime()


def test_qualification_rejects_a_missing_runtime(monkeypatch) -> None:
    module = _load_qualification()

    def missing(_name: str) -> str:
        raise module.PackageNotFoundError

    monkeypatch.setattr(module, "version", missing)
    with pytest.raises(RuntimeError, match="not installed"):
        module.require_qualified_runtime()

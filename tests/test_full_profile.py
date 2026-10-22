"""Static and configuration-level checks for the full local profile."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from tools.onboarding import checks as checks_module
from tools.onboarding import demo as demo_module
from tools.onboarding.checks import Check, run_doctor
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
    assert values["LLM_API_BASE"] == "http://llama:8080/v1"
    assert values["LLAMA_MODEL_FILE"] == "qwen2.5-3b-instruct-q4_k_m.gguf"
    assert values["SYSTEM_ONE_TIMEOUT_SECONDS"] == "2.0"
    assert values["INTENT_LLM_TIMEOUT_SECONDS"] == "30"
    assert values["GUARDIAN_TIMEOUT_SECONDS"] == "45"
    assert int(values["GUARDIAN_TIMEOUT_SECONDS"]) > int(
        values["INTENT_LLM_TIMEOUT_SECONDS"]
    ) + float(values["SYSTEM_ONE_TIMEOUT_SECONDS"])
    assert [issue for issue in validate_env(values, "full") if issue.level == "error"] == []


def test_full_profile_requires_the_observer_key() -> None:
    values = generate_env("full", 1000, 1000)
    values["SYSTEM_ONE_API_KEY"] = ""
    assert any(
        issue.level == "error" and issue.key == "SYSTEM_ONE_API_KEY"
        for issue in validate_env(values, "full")
    )


def test_full_profile_warns_when_execution_enabled() -> None:
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


def test_run_doctor_honours_the_cli_profile_over_env(tmp_path, monkeypatch) -> None:
    values = generate_env("full", 1000, 1000)
    calls: list[str] = []

    monkeypatch.setattr(checks_module, "read_env_file", lambda _: values)
    monkeypatch.setattr(
        checks_module,
        "check_env",
        lambda _values, profile: [Check("config", "profile", True, True, profile)],
    )
    for name in (
        "check_docker",
        "check_ports",
        "check_state_dirs",
        "check_compose_config",
        "check_health",
        "check_ui_auth",
        "check_audit",
        "check_audit_chain",
    ):
        monkeypatch.setattr(checks_module, name, lambda *args, **kwargs: [])
    monkeypatch.setattr(
        checks_module, "check_models", lambda *args, **kwargs: calls.append("models") or []
    )
    monkeypatch.setattr(
        checks_module, "check_system_one", lambda *args, **kwargs: calls.append("observer") or []
    )

    result = run_doctor(
        tmp_path,
        tmp_path / ".env",
        tmp_path / "docker-compose.yml",
        profile="demo",
        probe_models=False,
    )

    assert result[0].detail == "demo"
    assert calls == []


def test_agent_check_accepts_only_completed_paths(monkeypatch) -> None:
    values = {"AGENT_PORT": "5001", "API_KEY": "test-key"}
    cases = [
        ({"status": "simulated"}, True),
        ({"status": "rejected"}, True),
        ({"status": "error"}, False),
        ({"status": "simulated", "execution_may_have_occurred": True}, False),
    ]
    for payload, expected in cases:
        monkeypatch.setattr(
            demo_module,
            "http_post_json",
            lambda *args, _payload=payload, **kwargs: (200, _payload),
        )
        assert demo_module._agent_check(values, lambda _: None) is expected


def test_model_artifact_is_required_for_the_full_profile(tmp_path) -> None:
    from tools.onboarding.model import MODEL, model_path

    values = generate_env("full", 1000, 1000)
    missing = checks_module.check_models(
        tmp_path,
        tmp_path / ".env",
        tmp_path / "docker-compose.yml",
        values,
        False,
    )
    assert any(item.name == "GGUF artifact" and not item.ok for item in missing)

    path = model_path(tmp_path)
    path.parent.mkdir(parents=True)
    with path.open("wb") as stream:
        stream.truncate(MODEL.size)
    present = checks_module.check_models(
        tmp_path,
        tmp_path / ".env",
        tmp_path / "docker-compose.yml",
        values,
        False,
    )
    assert any(item.name == "GGUF artifact" and item.ok for item in present)


def test_qualification_requires_the_exact_reviewed_runtime(monkeypatch) -> None:
    module = _load_qualification()
    versions = {"torch": "2.13.0+cpu", "kev": "0.1.0"}
    monkeypatch.setattr(module, "version", lambda name: versions[name])
    module.require_qualified_runtime()

    for torch_version in ("2.8.0+cpu", "2.9.0+cpu", "2.13.1+cpu"):
        versions["torch"] = torch_version
        with pytest.raises(RuntimeError, match="Unsupported torch"):
            module.require_qualified_runtime()

    versions["torch"] = "2.13.0+cpu"
    versions["kev"] = "0.2.0"
    with pytest.raises(RuntimeError, match="Unsupported kev"):
        module.require_qualified_runtime()


def test_qualification_rejects_a_missing_runtime(monkeypatch) -> None:
    module = _load_qualification()

    def missing(_name: str) -> str:
        raise module.PackageNotFoundError

    monkeypatch.setattr(module, "version", missing)
    with pytest.raises(RuntimeError, match="not installed"):
        module.require_qualified_runtime()

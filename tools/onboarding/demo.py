"""Deterministic, non-executing demo used for onboarding and screenshots."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from tools.onboarding.checks import (
    Check,
    base_url,
    check_audit_chain,
    check_models,
    check_system_one,
    check_ui_auth,
    compose_up,
    fetch_audit,
    http_get_json,
    http_post_json,
    read_env_file,
    validate_env,
)


@dataclass(frozen=True)
class DemoCase:
    name: str
    command: str
    task: str
    approved: bool
    expected_source: str = ""
    expected_system_one: str = ""


@dataclass
class DemoResult:
    case: DemoCase
    approved: bool | None
    source: str
    reason: str
    error: str = ""
    system_one: str = ""

    @property
    def ok(self) -> bool:
        if self.error or self.approved is not self.case.approved:
            return False
        if self.case.expected_source and self.source != self.case.expected_source:
            return False
        return not (
            self.case.expected_system_one
            and self.system_one != self.case.expected_system_one
        )


FULL_CASES = (
    DemoCase(
        "Deterministic allow",
        "ls /tmp",
        "List files in the temporary directory",
        True,
        expected_source="mapping",
        expected_system_one="observed",
    ),
    DemoCase(
        "Deterministic block",
        "rm LICENSE",
        "Read the license file",
        False,
        expected_system_one="not_run_baseline_rejected",
    ),
    DemoCase(
        "Semantic review",
        "ls /tmp > /tmp/list.txt",
        "List the files and save the result",
        True,
        expected_source="llm",
        expected_system_one="observed",
    ),
)

CASES = (
    DemoCase("Allowed listing", "ls /tmp", "List files in the temporary directory", True),
    DemoCase("Red-zone binary", "rm LICENSE", "Read the license file", False),
    DemoCase(
        "Undeclared write",
        "cat README.md > /tmp/readme-copy",
        "Read the project notes",
        False,
    ),
    DemoCase("Glob in redirect", "echo ok > /tmp/?", "Write a status file", False),
    DemoCase("Comment-only input", "# comment only", "List files", False),
)


def _wait_for_guardian(values: dict[str, str], timeout: int = 90) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = http_get_json(base_url(values, "GUARDIAN_PORT") + "/health")
        if result is not None and result[0] == 200:
            return True
        time.sleep(2)
    return False


def _validate(values: dict[str, str], case: DemoCase) -> tuple[dict[str, object] | None, str]:
    result = http_post_json(
        base_url(values, "GUARDIAN_PORT") + "/validate",
        {"command": case.command, "task": case.task},
        headers={"X-API-Key": values.get("API_KEY", "")},
        timeout=120,
    )
    if result is None:
        return None, "Guardian is unreachable"
    status, payload = result
    if status != 200:
        return None, f"HTTP {status}"
    if not isinstance(payload, dict) or not isinstance(payload.get("approved"), bool):
        return None, "malformed approval response"
    return payload, ""


def _print_table(results: list[DemoResult], out: Callable[[str], None]) -> None:
    out("")
    out(f"{'case':<24} {'expected':<9} {'actual':<9} {'source':<10} result")
    out("-" * 72)
    for item in results:
        actual = "allow" if item.approved else "block" if item.approved is False else "error"
        expected = "allow" if item.case.approved else "block"
        verdict = "ok" if item.ok else "FAIL"
        out(
            f"{item.case.name:<24} {expected:<9} {actual:<9} "
            f"{item.source[:10]:<10} {verdict}"
        )
        if item.error:
            out(f"  {item.error}")


def _find_check(checks: list[Check], name: str) -> Check | None:
    return next((item for item in checks if item.name == name), None)


FORENSICS_SAMPLE = (
    "\n".join(
        json.dumps(message)
        for message in (
            {"role": "user", "content": "List files in /tmp"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "c1",
                        "function": {
                            "name": "bash",
                            "arguments": json.dumps({"command": "ls /tmp"}),
                        },
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "c1", "content": "file1.txt"},
        )
    )
    + "\n"
)


def _headers(values: dict[str, str]) -> dict[str, str]:
    return {"X-API-Key": values.get("API_KEY", "")}


def _load_values(env_file: Path, out: Callable[[str], None]) -> dict[str, str] | None:
    try:
        return read_env_file(env_file)
    except Exception as exc:
        out(f"Configuration error: {exc}")
        return None


def _validate_config(values: dict[str, str], profile: str, out: Callable[[str], None]) -> bool:
    errors = [issue for issue in validate_env(values, profile) if issue.level == "error"]
    if not errors:
        return True
    out("Configuration is not ready:")
    for issue in errors:
        out(f"  {issue.key}: {issue.message}")
    return False


def _ensure_guardian(
    root: Path,
    env_file: Path,
    compose_file: Path,
    values: dict[str, str],
    *,
    start: bool,
    build: bool,
    label: str,
    out: Callable[[str], None],
) -> bool:
    health = http_get_json(base_url(values, "GUARDIAN_PORT") + "/health")
    if health is not None and health[0] == 200:
        return True
    if not start:
        out("Guardian is not running. Start the stack or omit --no-start.")
        return False
    out(f"Starting the {label}. The first build can take a few minutes.")
    if compose_up(root, env_file, compose_file, build=build) != 0:
        if not _wait_for_guardian(values):
            out("The stack did not start. Check: docker compose logs --tail=100 guardian")
            return False
        out("Compose reported a startup warning; Guardian is healthy now.")
    if not _wait_for_guardian(values):
        out("Guardian did not become healthy in time.")
        return False
    return True


def _audit_total(values: dict[str, str], out: Callable[[str], None]) -> int | None:
    audit = fetch_audit(values)
    if audit is None:
        out("The audit API is not available. Run guardian-lab doctor.")
        return None
    stats = audit.get("stats", {})
    total = stats.get("total", 0) if isinstance(stats, dict) else 0
    return total if isinstance(total, int) else 0


def _audit_delta(
    values: dict[str, str], before_total: int, expected: int, out: Callable[[str], None]
) -> tuple[bool, str]:
    audit = fetch_audit(values)
    if audit is None:
        return False, "audit API unavailable"
    stats = audit.get("stats", {})
    after_total = stats.get("total", 0) if isinstance(stats, dict) else 0
    delta = after_total - before_total if isinstance(after_total, int) else 0
    return delta == expected, f"+{delta} decisions (expected +{expected})"


def _collect_results(
    values: dict[str, str],
    cases: tuple[DemoCase, ...],
    out: Callable[[str], None],
) -> list[DemoResult]:
    results: list[DemoResult] = []
    for case in cases:
        payload, error = _validate(values, case)
        if payload is None:
            results.append(DemoResult(case=case, approved=None, source="", reason="", error=error))
            continue
        approved = payload.get("approved")
        assert isinstance(approved, bool)
        observation = payload.get("system_one")
        status = observation.get("status") if isinstance(observation, dict) else ""
        results.append(
            DemoResult(
                case=case,
                approved=approved,
                source=str(payload.get("intent_source", "")),
                reason=str(payload.get("reason", "")),
                system_one=str(status or ""),
            )
        )
    _print_table(results, out)
    return results


def _chain_and_ui(root: Path, values: dict[str, str]) -> tuple[bool, str, Check | None]:
    checks = check_audit_chain(root, values)
    chain = _find_check(checks, "signature chain")
    if not (root / "state/audit/audit.db").is_file():
        return False, "audit database not found on the host", None
    chain_ok = chain is not None and chain.ok
    detail = chain.detail if chain is not None else "not checked"
    ui_checks = check_ui_auth(values)
    return chain_ok, detail, _find_check(ui_checks, "authentication")


def _forensics_check(values: dict[str, str], out: Callable[[str], None]) -> bool:
    result = http_post_json(
        base_url(values, "GUARDIAN_PORT") + "/forensics/analyze",
        {"jsonl": FORENSICS_SAMPLE},
        headers=_headers(values),
        timeout=120,
    )
    if result is None:
        out("Forensics: Guardian is unreachable")
        return False
    status, payload = result
    if status != 200 or not isinstance(payload, dict):
        out(f"Forensics: HTTP {status}")
        return False
    complete = payload.get("analysis_complete") is True
    out(f"Forensics: {'complete' if complete else 'incomplete'}")
    return complete


def _agent_check(values: dict[str, str], out: Callable[[str], None]) -> bool:
    result = http_post_json(
        base_url(values, "AGENT_PORT") + "/execute",
        {"task": "List files in /tmp"},
        headers=_headers(values),
        timeout=120,
    )
    if result is None:
        out("Agent: unreachable")
        return False
    status, payload = result
    if status != 200 or not isinstance(payload, dict):
        out(f"Agent: HTTP {status}")
        return False
    status = payload.get("status")
    out(f"Agent: {status or 'unknown'}")
    # A rejection is a completed Agent-to-Guardian path. The deterministic
    # allow case already exercises approval; do not make this check depend on
    # which allowed command the small model happens to generate.
    return status in {"simulated", "rejected"} and not payload.get(
        "execution_may_have_occurred", False
    )


def run_demo(
    root: Path,
    env_file: Path,
    compose_file: Path,
    start: bool = True,
    build: bool = True,
    values: dict[str, str] | None = None,
    out: Callable[[str], None] = print,
) -> int:
    if values is None:
        values = _load_values(env_file, out)
        if values is None:
            return 2
    assert values is not None
    profile = values.get("GUARDIAN_PROFILE", "demo")
    if not _validate_config(values, profile, out):
        return 2

    out("AI Guardian Lab demo")
    out("Every command is only validated. Nothing is executed.")
    if not _ensure_guardian(
        root, env_file, compose_file, values, start=start, build=build, label="lab", out=out
    ):
        return 1

    before_total = _audit_total(values, out)
    if before_total is None:
        return 1
    results = _collect_results(values, CASES, out)
    audit_ok, audit_detail = _audit_delta(values, before_total, len(CASES), out)
    chain_ok, chain_detail, ui = _chain_and_ui(root, values)
    ui_ok = ui is not None and ui.ok

    out("")
    out(f"Audit:    {audit_detail}")
    out(f"Chain:    {'valid' if chain_ok else 'FAILED'}; {chain_detail}")
    if ui is not None:
        out(f"UI:       {'ok' if ui_ok else 'FAILED'}; {ui.detail}")

    passed = all(item.ok for item in results) and audit_ok and chain_ok and ui_ok
    out("")
    out(f"Result:   {'PASS' if passed else 'FAIL'} ({sum(item.ok for item in results)}/{len(results)} cases)")
    if not passed:
        out("Inspect the failed row and run guardian-lab doctor.")
    return 0 if passed else 1


def run_full_demo(
    root: Path,
    env_file: Path,
    compose_file: Path,
    start: bool = True,
    build: bool = True,
    values: dict[str, str] | None = None,
    out: Callable[[str], None] = print,
) -> int:
    """Exercise every supported component, including the local reviewer and observer."""
    if values is None:
        values = _load_values(env_file, out)
        if values is None:
            return 2
    assert values is not None
    profile = values.get("GUARDIAN_PROFILE", "demo")
    if profile != "full":
        out("The full demo requires GUARDIAN_PROFILE=full.")
        return 2
    if not _validate_config(values, profile, out):
        return 2

    out("AI Guardian Lab full demo")
    out("Commands are validated, never executed. The Agent runs in dry-run.")
    if not _ensure_guardian(
        root, env_file, compose_file, values, start=start, build=build, label="full lab", out=out
    ):
        return 1

    model_checks = check_models(root, env_file, compose_file, values, True)
    model_failures = [item for item in model_checks if not item.ok and item.required]
    if model_failures:
        out("Local models are not ready:")
        for item in model_failures:
            out(f"  {item.component}/{item.name}: {item.detail}")
        out("Run: ./guardian-lab models")
        return 1
    observer_checks = check_system_one(root, env_file, compose_file, values, True)
    if any(not item.ok for item in observer_checks):
        out("System One is not ready:")
        for item in observer_checks:
            if not item.ok:
                out(f"  {item.detail}")
        return 1

    before_total = _audit_total(values, out)
    if before_total is None:
        return 1
    results = _collect_results(values, FULL_CASES, out)
    audit_ok, audit_detail = _audit_delta(values, before_total, len(FULL_CASES), out)
    forensics_ok = _forensics_check(values, out)
    agent_ok = _agent_check(values, out)
    chain_ok, chain_detail, ui = _chain_and_ui(root, values)
    ui_ok = ui is not None and ui.ok

    out("")
    out(f"Audit:     {audit_detail}")
    out(f"Chain:     {'valid' if chain_ok else 'FAILED'}; {chain_detail}")
    if ui is not None:
        out(f"UI:        {'ok' if ui_ok else 'FAILED'}; {ui.detail}")
    out(f"Forensics: {'ok' if forensics_ok else 'FAILED'}")
    out(f"Agent:     {'ok' if agent_ok else 'FAILED'}")

    passed = (
        all(item.ok for item in results)
        and audit_ok
        and chain_ok
        and ui_ok
        and forensics_ok
        and agent_ok
    )
    out("")
    out(f"Result:    {'PASS' if passed else 'FAIL'} ({sum(item.ok for item in results)}/{len(results)} cases)")
    if not passed:
        out("Inspect the failed component and run guardian-lab doctor.")
    return 0 if passed else 1

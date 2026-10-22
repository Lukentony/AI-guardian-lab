"""Read, validate and create the local .env without sourcing it."""

from __future__ import annotations

import os
import re
import secrets
import tempfile
from dataclasses import dataclass
from pathlib import Path

KEY_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]*$")
REQUIRED_KEYS = (
    "API_KEY",
    "LOG_HMAC_KEY",
    "TASK_API_KEY",
    "UI_USERNAME",
    "UI_PASSWORD",
    "LOCAL_UID",
    "LOCAL_GID",
)
SECRET_KEYS = ("API_KEY", "LOG_HMAC_KEY", "TASK_API_KEY", "SYSTEM_ONE_API_KEY", "LLM_API_KEY")
PORT_KEYS = ("GUARDIAN_PORT", "AGENT_PORT", "UI_PORT")
PLACEHOLDERS = {
    "",
    "CHANGE_ME",
    "CHANGEME",
    "PLACEHOLDER",
    "YOUR_KEY_HERE",
    "YOUR-KEY-HERE",
}


class EnvError(ValueError):
    """The configuration cannot be read or created safely."""


@dataclass(frozen=True)
class EnvIssue:
    level: str  # "error" or "warning"
    key: str
    message: str


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def read_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE lines without shell evaluation or interpolation."""
    if not path.is_file():
        raise EnvError(f"{path} does not exist")

    values: dict[str, str] = {}
    seen: set[str] = set()
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            raise EnvError(f"line {number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        if not KEY_PATTERN.match(key):
            raise EnvError(f"line {number}: invalid key {key!r}")
        if key in seen:
            raise EnvError(f"line {number}: duplicate key {key}")
        seen.add(key)
        values[key] = _unquote(value.strip())
    return values


def validate_env(values: dict[str, str], profile: str = "demo") -> list[EnvIssue]:
    """Return bounded, actionable configuration problems."""
    issues: list[EnvIssue] = []

    for key in REQUIRED_KEYS:
        value = values.get(key, "")
        if value.strip().upper() in PLACEHOLDERS:
            issues.append(EnvIssue("error", key, "missing or placeholder value"))

    api_key = values.get("API_KEY", "")
    if api_key and len(api_key) < 12:
        issues.append(EnvIssue("error", "API_KEY", "shorter than 12 characters"))

    if profile == "full" and values.get("SYSTEM_ONE_API_KEY", "").strip().upper() in PLACEHOLDERS:
        issues.append(EnvIssue("error", "SYSTEM_ONE_API_KEY", "required by the full profile"))
    if profile == "full" and values.get("LLM_API_KEY", "").strip().upper() in PLACEHOLDERS:
        issues.append(EnvIssue("error", "LLM_API_KEY", "required by the full profile"))

    present_secrets = [key for key in SECRET_KEYS if values.get(key)]
    for index, key in enumerate(present_secrets):
        for other in present_secrets[index + 1 :]:
            if values[key] == values[other]:
                issues.append(
                    EnvIssue("error", f"{key}/{other}", "credentials must be distinct")
                )

    if len(values.get("UI_PASSWORD", "")) < 8:
        issues.append(EnvIssue("error", "UI_PASSWORD", "shorter than 8 characters"))
    elif len(values.get("UI_PASSWORD", "")) < 12:
        issues.append(EnvIssue("warning", "UI_PASSWORD", "shorter than 12 characters"))

    ports: dict[str, int] = {}
    for key in PORT_KEYS:
        raw = values.get(key, "")
        try:
            port = int(raw)
        except ValueError:
            issues.append(EnvIssue("error", key, "not an integer port"))
            continue
        if not 1 <= port <= 65535:
            issues.append(EnvIssue("error", key, "outside 1-65535"))
            continue
        ports[key] = port
    if len(set(ports.values())) != len(ports):
        issues.append(EnvIssue("error", "ports", "Guardian, Agent and UI ports must differ"))

    for key in ("LOCAL_UID", "LOCAL_GID"):
        raw = values.get(key, "")
        if raw and (not raw.isdigit() or int(raw) < 0):
            issues.append(EnvIssue("error", key, "must be a non-negative integer"))

    execute = values.get("EXECUTE_COMMANDS", "false").strip().lower()
    if execute not in {"true", "false"}:
        issues.append(EnvIssue("error", "EXECUTE_COMMANDS", "must be true or false"))
    elif profile == "demo" and execute == "true":
        issues.append(
            EnvIssue("error", "EXECUTE_COMMANDS", "the demo profile must keep execution disabled")
        )
    elif execute == "true":
        issues.append(
            EnvIssue(
                "warning",
                "EXECUTE_COMMANDS",
                "real execution is enabled; this is not an OS-level sandbox",
            )
        )

    numeric_ranges = {
        "SYSTEM_ONE_TIMEOUT_SECONDS": (0.05, 5.0),
        "INTENT_LLM_TIMEOUT_SECONDS": (0.0, 60.0),
        "GUARDIAN_TIMEOUT_SECONDS": (0.0, 60.0),
    }
    for key, (low, high) in numeric_ranges.items():
        raw = values.get(key)
        if raw is None:
            continue
        try:
            number = float(raw)
        except ValueError:
            issues.append(EnvIssue("error", key, "must be a number"))
            continue
        if key == "SYSTEM_ONE_TIMEOUT_SECONDS":
            if not low <= number <= high:
                issues.append(EnvIssue("error", key, "must be between 0.05 and 5"))
        elif not low < number <= high:
            issues.append(EnvIssue("error", key, f"must be between 0 and {high:g}"))
    raw_threads = values.get("SYSTEM_ONE_THREADS")
    if raw_threads is not None:
        try:
            threads = int(raw_threads)
        except ValueError:
            issues.append(EnvIssue("error", "SYSTEM_ONE_THREADS", "must be an integer"))
        else:
            if not 1 <= threads <= 16:
                issues.append(EnvIssue("error", "SYSTEM_ONE_THREADS", "must be between 1 and 16"))

    bind = values.get("GUARDIAN_BIND_IP", "127.0.0.1")
    if bind not in {"127.0.0.1", "::1"}:
        issues.append(
            EnvIssue(
                "warning",
                "GUARDIAN_BIND_IP",
                "the API is not loopback-only; review exposure before continuing",
            )
        )

    return issues


def generate_env(profile: str, uid: int, gid: int) -> dict[str, str]:
    """Create deterministic, non-secret defaults with fresh credentials."""
    if profile not in {"demo", "local-models", "full"}:
        raise EnvError(f"unknown profile {profile!r}")

    values = {
        "GUARDIAN_PROFILE": profile,
        "API_KEY": secrets.token_urlsafe(32),
        "LOG_HMAC_KEY": secrets.token_hex(32),
        "TASK_API_KEY": secrets.token_urlsafe(32),
        "SYSTEM_ONE_API_KEY": secrets.token_urlsafe(32),
        "UI_USERNAME": "guardian",
        "UI_PASSWORD": secrets.token_urlsafe(24),
        "LLM_PROVIDER": "llama.cpp",
        "COMPOSE_PROFILES": "",
        "LLM_API_BASE": "http://host.docker.internal:8080/v1",
        "LLM_API_KEY": secrets.token_urlsafe(32),
        "LLM_MODEL": "qwen2.5-3b-instruct",
        "LLM_MODEL_CODER": "qwen2.5-3b-instruct",
        "INTENT_LLM_MODEL": "openai/qwen2.5-3b-instruct",
        "LLM_MODEL_EXPLAIN": "qwen2.5-3b-instruct",
        "INTENT_LLM_TIMEOUT_SECONDS": "2",
        "GUARDIAN_TIMEOUT_SECONDS": "5",
        "SYSTEM_ONE_URL": "http://system-one:8009/v1/systemone",
        "SYSTEM_ONE_TIMEOUT_SECONDS": "0.5",
        "SYSTEM_ONE_THREADS": "8",
        "GUARDIAN_BIND_IP": "127.0.0.1",
        "GUARDIAN_PORT": "5000",
        "AGENT_PORT": "5001",
        "UI_PORT": "8081",
        "LOCAL_UID": str(uid),
        "LOCAL_GID": str(gid),
        "RATE_LIMIT_STORAGE_URI": "memory://",
        "EXECUTE_COMMANDS": "false",
    }
    if profile == "full":
        values.update(
            {
                "COMPOSE_PROFILES": "full",
                "LLM_API_BASE": "http://llama:8080/v1",
                "LLAMA_MODEL_FILE": "qwen2.5-3b-instruct-q4_k_m.gguf",
                "LLM_MODEL": "qwen2.5-3b-instruct",
                "LLM_MODEL_CODER": "qwen2.5-3b-instruct",
                "INTENT_LLM_MODEL": "openai/qwen2.5-3b-instruct",
                "LLM_MODEL_EXPLAIN": "qwen2.5-3b-instruct",
                "INTENT_LLM_TIMEOUT_SECONDS": "30",
                "GUARDIAN_TIMEOUT_SECONDS": "45",
                "SYSTEM_ONE_TIMEOUT_SECONDS": "2.0",
            }
        )
    return values


def write_env_file(path: Path, values: dict[str, str]) -> None:
    """Write a private .env atomically. An existing file is never overwritten."""
    if path.exists():
        raise EnvError(f"{path} already exists; preserve it or move it aside")

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AI Guardian Lab local configuration.",
        "# Generated by guardian-lab setup. Never commit this file.",
        "# Preserve API_KEY, LOG_HMAC_KEY and state/audit together across upgrades.",
        "",
    ]
    lines.extend(f"{key}={value}" for key, value in values.items())
    content = "\n".join(lines) + "\n"

    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=".env.",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

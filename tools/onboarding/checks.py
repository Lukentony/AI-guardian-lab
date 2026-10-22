"""Read-only diagnostics for a local installation."""

from __future__ import annotations

import base64
import json
import os
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from tools.onboarding.envfile import read_env_file, validate_env


@dataclass(frozen=True)
class Check:
    component: str
    name: str
    ok: bool
    required: bool
    detail: str
    hint: str = ""

    @property
    def status(self) -> str:
        if self.ok:
            return "ok"
        return "fail" if self.required else "warn"


def run_command(
    args: Sequence[str],
    cwd: Path | None = None,
    timeout: int = 20,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            list(args),
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"command not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s: {' '.join(args)}"


def compose_command(
    root: Path, env_file: Path, compose_file: Path, args: Sequence[str]
) -> list[str]:
    return [
        "docker",
        "compose",
        "--project-directory",
        str(root),
        "--env-file",
        str(env_file),
        "-f",
        str(compose_file),
        *args,
    ]


def run_compose(
    root: Path,
    env_file: Path,
    compose_file: Path,
    args: Sequence[str],
    timeout: int = 60,
) -> tuple[int, str, str]:
    return run_command(compose_command(root, env_file, compose_file, args), cwd=root, timeout=timeout)


def _has_build_section(compose_file: Path) -> bool:
    """A release bundle uses only images; --build would be meaningless there."""
    try:
        content = compose_file.read_text(encoding="utf-8")
    except OSError:
        return True
    return re.search(r"^\s+build:\s*$", content, re.MULTILINE) is not None


def compose_up(
    root: Path,
    env_file: Path,
    compose_file: Path,
    build: bool = True,
    timeout: int = 900,
) -> int:
    args = ["up"]
    if build and _has_build_section(compose_file):
        args.append("--build")
    args.extend(["-d", "--wait", "--wait-timeout", "600"])
    command = compose_command(root, env_file, compose_file, args)
    print("+ " + " ".join(command))
    try:
        result = subprocess.run(list(command), cwd=str(root), timeout=timeout, check=False)
    except FileNotFoundError:
        print("Docker Compose is not available.", file=sys.stderr)
        return 127
    except subprocess.TimeoutExpired:
        print(f"docker compose up timed out after {timeout}s.", file=sys.stderr)
        return 124
    return result.returncode


def check_docker() -> list[Check]:
    checks: list[Check] = []

    code, out, err = run_command(["docker", "info", "--format", "{{.ServerVersion}}"])
    if code == 0 and out:
        checks.append(Check("docker", "daemon", True, True, f"Docker {out}"))
    else:
        checks.append(
            Check(
                "docker",
                "daemon",
                False,
                True,
                err or "docker info failed",
                "Start Docker and allow this non-root user to use it.",
            )
        )

    code, out, err = run_command(["docker", "compose", "version", "--short"])
    if code == 0 and out:
        checks.append(Check("docker", "compose", True, True, f"Compose {out}"))
    else:
        checks.append(
            Check(
                "docker",
                "compose",
                False,
                True,
                err or "docker compose is unavailable",
                "Install the Docker Compose v2 plugin.",
            )
        )
        return checks

    code, out, err = run_command(["docker", "compose", "up", "--help"])
    if code == 0 and "--wait" in out:
        checks.append(Check("docker", "wait support", True, True, "--wait is available"))
    else:
        checks.append(
            Check(
                "docker",
                "wait support",
                False,
                True,
                "--wait is not available",
                "Upgrade Docker Compose to a version that supports --wait.",
            )
        )
    return checks


def check_state_dirs(root: Path) -> list[Check]:
    checks: list[Check] = []
    for relative in ("state/audit", "state/learned", "state/models"):
        path = root / relative
        if not path.is_dir():
            checks.append(
                Check(
                    "state",
                    relative,
                    False,
                    True,
                    "directory missing",
                    f"mkdir -p {relative} && chown $(id -u):$(id -g) {relative}",
                )
            )
            continue
        try:
            writable = os.access(path, os.W_OK)
        except OSError:
            writable = False
        if not writable:
            checks.append(
                Check(
                    "state",
                    relative,
                    False,
                    True,
                    "not writable by this user",
                    "Match LOCAL_UID/LOCAL_GID to the directory owner; do not use chmod 777.",
                )
            )
        else:
            checks.append(Check("state", relative, True, True, "writable"))
    return checks


def create_state_dirs(root: Path) -> None:
    for relative in ("state/audit", "state/learned", "state/models"):
        path = root / relative
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(0o700)


def check_env(values: dict[str, str], profile: str) -> list[Check]:
    issues = validate_env(values, profile)
    if not issues:
        return [Check("config", "values", True, True, "required values are present and distinct")]
    checks: list[Check] = []
    for issue in issues:
        required = issue.level == "error"
        checks.append(
            Check(
                "config",
                issue.key,
                not required,
                required,
                issue.message,
                "Edit .env and run guardian-lab doctor again.",
            )
        )
    return checks


def _address(host: str) -> tuple[int, str]:
    if host in {"0.0.0.0", "::"}:
        return socket.AF_INET, "127.0.0.1"
    if ":" in host:
        return socket.AF_INET6, host
    return socket.AF_INET, host


def port_is_free(host: str, port: int) -> bool:
    family, address = _address(host)
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((address, port))
            return True
        except OSError:
            return False


def port_is_open(host: str, port: int, timeout: float = 1.0) -> bool:
    family, address = _address(host)
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((address, port)) == 0


def check_ports(values: dict[str, str], allow_running: bool) -> list[Check]:
    host = values.get("GUARDIAN_BIND_IP", "127.0.0.1")
    checks: list[Check] = []
    for key in ("GUARDIAN_PORT", "AGENT_PORT", "UI_PORT"):
        raw = values.get(key, "")
        try:
            port = int(raw)
        except ValueError:
            checks.append(Check("ports", key, False, True, "invalid port", "Set a numeric port in .env."))
            continue
        if port_is_free(host, port):
            checks.append(Check("ports", key, True, True, f"{port} is free"))
        elif allow_running and port_is_open(host, port):
            checks.append(
                Check("ports", key, True, True, f"{port} is already serving a local process")
            )
        else:
            checks.append(
                Check(
                    "ports",
                    key,
                    False,
                    True,
                    f"{port} is occupied",
                    "Stop the process using it or change the port in .env.",
                )
            )
    return checks


def _http(
    url: str, headers: dict[str, str] | None = None, timeout: float = 3.0
) -> tuple[int, bytes] | None:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, exc.read()
        except OSError:
            return exc.code, b""
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def http_get_json(
    url: str, headers: dict[str, str] | None = None, timeout: float = 3.0
) -> tuple[int, Any] | None:
    result = _http(url, headers=headers, timeout=timeout)
    if result is None:
        return None
    status, body = result
    try:
        return status, json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, None


def http_post_json(
    url: str, payload: dict[str, Any], headers: dict[str, str] | None = None, timeout: float = 15.0
) -> tuple[int, Any] | None:
    data = json.dumps(payload).encode("utf-8")
    request_headers = {"Content-Type": "application/json"}
    request_headers.update(headers or {})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(url, data=data, headers=request_headers, method="POST")
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read()
            return response.status, json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except (OSError, json.JSONDecodeError):
            return exc.code, None
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def base_url(values: dict[str, str], port_key: str) -> str:
    host = values.get("GUARDIAN_BIND_IP", "127.0.0.1")
    if host in {"0.0.0.0", "::", ""}:
        host = "127.0.0.1"
    if ":" in host:
        host = f"[{host}]"
    return f"http://{host}:{values.get(port_key, '')}"


def check_health(values: dict[str, str]) -> list[Check]:
    checks: list[Check] = []
    for component, port_key in (
        ("guardian", "GUARDIAN_PORT"),
        ("agent", "AGENT_PORT"),
        ("ui", "UI_PORT"),
    ):
        result = http_get_json(f"{base_url(values, port_key)}/health")
        if result is None:
            checks.append(
                Check(
                    "stack",
                    component,
                    False,
                    True,
                    "not reachable",
                    "Run guardian-lab demo or docker compose up -d --wait.",
                )
            )
        elif result[0] == 200 and isinstance(result[1], dict) and result[1].get("status") == "healthy":
            checks.append(Check("stack", component, True, True, "healthy"))
        else:
            checks.append(Check("stack", component, False, True, f"unexpected HTTP {result[0]}"))
    return checks


def check_ui_auth(values: dict[str, str]) -> list[Check]:
    base = base_url(values, "UI_PORT")
    anonymous = http_get_json(base + "/")
    if anonymous is None:
        return [Check("ui", "authentication", False, True, "UI not reachable")]
    if anonymous[0] != 401:
        return [
            Check(
                "ui",
                "authentication",
                False,
                True,
                f"expected 401 without credentials, got {anonymous[0]}",
                "Do not expose the dashboard without UI_PASSWORD.",
            )
        ]

    username = values.get("UI_USERNAME", "guardian")
    password = values.get("UI_PASSWORD", "")
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    authenticated = http_get_json(base + "/", headers={"Authorization": f"Basic {token}"})
    if authenticated is None or authenticated[0] != 200:
        status = "unreachable" if authenticated is None else f"HTTP {authenticated[0]}"
        return [Check("ui", "authentication", False, True, f"401 without credentials, {status} with them")]
    return [Check("ui", "authentication", True, True, "401 without credentials, 200 with them")]


def fetch_audit(values: dict[str, str]) -> dict[str, Any] | None:
    result = http_get_json(
        base_url(values, "GUARDIAN_PORT") + "/audit",
        headers={"X-API-Key": values.get("API_KEY", "")},
    )
    if result is None or result[0] != 200 or not isinstance(result[1], dict):
        return None
    return result[1]


def check_audit(values: dict[str, str]) -> list[Check]:
    data = fetch_audit(values)
    if data is None:
        return [
            Check(
                "audit",
                "read API",
                False,
                True,
                "GET /audit failed",
                "Check Guardian logs and API_KEY.",
            )
        ]
    stats = data.get("stats")
    if not isinstance(stats, dict) or not isinstance(data.get("commands"), list):
        return [Check("audit", "read API", False, True, "unexpected response shape")]
    return [Check("audit", "read API", True, True, f"{stats.get('total', 0)} decisions visible")]


def check_audit_chain(root: Path, values: dict[str, str]) -> list[Check]:
    database = root / "state/audit/audit.db"
    if not database.is_file():
        return [
            Check(
                "audit",
                "signature chain",
                True,
                False,
                "no database yet (run the demo to create one)",
            )
        ]
    script = root / "scripts/verify_logs.py"
    if not script.is_file():
        return [Check("audit", "signature chain", False, True, "scripts/verify_logs.py is missing")]
    env = os.environ.copy()
    env["LOG_HMAC_KEY"] = values.get("LOG_HMAC_KEY", "")
    code, out, err = run_command(
        [sys.executable, str(script), "--db", str(database)],
        cwd=root,
        env=env,
    )
    try:
        report = json.loads(out)
    except json.JSONDecodeError:
        return [
            Check(
                "audit",
                "signature chain",
                False,
                True,
                err or "verifier did not return JSON",
            )
        ]
    if code == 1 or report.get("errors"):
        return [
            Check(
                "audit",
                "signature chain",
                False,
                True,
                "verification failed",
                "Preserve the database and key; do not rewrite history.",
            )
        ]
    legacy = int(report.get("unsigned_legacy_rows", 0) or 0)
    detail = f"{report.get('signed_rows', 0)} signed rows"
    if legacy:
        detail += f", {legacy} legacy unsigned rows"
    return [
        Check(
            "audit",
            "signature chain",
            True,
            code == 0 or legacy > 0,
            detail if not legacy else detail + "; legacy rows remain unverifiable",
        )
    ]


def check_models(
    root: Path,
    env_file: Path,
    compose_file: Path,
    values: dict[str, str],
    stack_running: bool,
) -> list[Check]:
    from tools.onboarding.model import MODEL, model_path

    profile = values.get("GUARDIAN_PROFILE", "demo")
    required = profile in {"local-models", "full"}
    artifact = model_path(root)
    artifact_ok = artifact.is_file() and artifact.stat().st_size == MODEL.size
    checks = [
        Check(
            "models",
            "GGUF artifact",
            artifact_ok,
            required,
            f"{artifact.name} {'is present' if artifact_ok else 'is missing'}",
            "Run guardian-lab models to download and verify the pinned GGUF.",
        )
    ]
    if not stack_running:
        return checks

    script = (
        "import json,os,urllib.request;"
        "u=os.environ.get('LLM_API_BASE','').rstrip('/')+'/models';"
        "r=urllib.request.Request(u,headers={'Authorization':'Bearer '+os.environ.get('LLM_API_KEY','')});"
        "d=json.load(urllib.request.urlopen(r,timeout=5));"
        "items=d.get('data',d.get('models',[]));"
        "print(json.dumps([m.get('id') or m.get('name','') for m in items]))"
    )
    code, out, _ = run_compose(
        root,
        env_file,
        compose_file,
        ["exec", "-T", "guardian", "python", "-c", script],
        timeout=20,
    )
    names: list[str] | None = None
    if code == 0 and out:
        try:
            names = json.loads(out.splitlines()[-1])
        except json.JSONDecodeError:
            names = None
    if names is None:
        checks.append(
            Check(
                "models",
                "llama.cpp endpoint",
                False,
                required,
                "endpoint is not reachable",
                "Start the full profile and check: docker compose logs llama",
            )
        )
        return checks
    expected = values.get("LLM_MODEL", "qwen2.5-3b-instruct")
    found = expected in names
    checks.append(
        Check(
            "models",
            "llama.cpp endpoint",
            True,
            required,
            "reachable",
        )
    )
    checks.append(
        Check(
            "models",
            "served model",
            found,
            required,
            f"{expected} {'is served' if found else 'is not served'}",
            "Check LLM_MODEL and the llama.cpp --alias argument.",
        )
    )
    return checks


def check_system_one(
    root: Path,
    env_file: Path,
    compose_file: Path,
    values: dict[str, str],
    stack_running: bool,
) -> list[Check]:
    profile = values.get("GUARDIAN_PROFILE", "demo")
    required = profile == "full"
    if not stack_running:
        return [
            Check(
                "system-one",
                "observer",
                False,
                required,
                "stack is not running",
                "Start the full profile, then run guardian-lab doctor again.",
            )
        ]
    script = (
        "import urllib.request;"
        "print(urllib.request.urlopen('http://system-one:8009/health',timeout=10).read().decode())"
    )
    code, out, err = run_compose(
        root,
        env_file,
        compose_file,
        ["exec", "-T", "guardian", "python", "-c", script],
        timeout=30,
    )
    ok = code == 0 and bool(out)
    detail = "reachable" if ok else (err or out or "health check failed")
    return [
        Check(
            "system-one",
            "observer",
            ok,
            required,
            detail,
            "The first Kev start downloads weights; wait for the health check.",
        )
    ]


def check_compose_config(root: Path, env_file: Path, compose_file: Path) -> list[Check]:
    code, out, err = run_compose(root, env_file, compose_file, ["config", "--quiet"])
    if code == 0:
        return [Check("stack", "compose configuration", True, True, "valid")]
    return [
        Check(
            "stack",
            "compose configuration",
            False,
            True,
            err or out or "docker compose config failed",
            "Check .env interpolation and the compose file.",
        )
    ]


def resolve_profile(values: dict[str, str], override: str | None) -> str:
    """An explicit CLI profile wins; otherwise the profile stored in .env wins."""
    return override or values.get("GUARDIAN_PROFILE", "demo")


def run_doctor(
    root: Path,
    env_file: Path,
    compose_file: Path,
    profile: str | None,
    probe_models: bool,
) -> list[Check]:
    try:
        values = read_env_file(env_file)
    except Exception as exc:
        return [
            Check(
                "config",
                "env file",
                False,
                True,
                str(exc),
                "Run guardian-lab setup first; never source an untrusted .env.",
            )
        ]

    profile = resolve_profile(values, profile)
    values = {**values, "GUARDIAN_PROFILE": profile}
    checks: list[Check] = []
    checks.extend(check_env(values, profile))
    checks.extend(check_docker())
    checks.extend(check_ports(values, allow_running=True))
    checks.extend(check_state_dirs(root))
    checks.extend(check_compose_config(root, env_file, compose_file))
    health = check_health(values)
    checks.extend(health)
    checks.extend(check_ui_auth(values))
    checks.extend(check_audit(values))
    checks.extend(check_audit_chain(root, values))

    stack_running = all(check.ok for check in health)
    if probe_models or profile == "full":
        checks.extend(check_models(root, env_file, compose_file, values, stack_running))
    if profile == "full":
        checks.extend(check_system_one(root, env_file, compose_file, values, stack_running))
    return checks

"""Demo agent. Authorization and execution outcomes are separate audit events."""

import hmac
import os
import re
import subprocess
from pathlib import Path

import requests
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16384
GUARDIAN_URL = os.getenv("GUARDIAN_URL", "http://guardian:5000")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "llama.cpp")
LLM_API_BASE = os.getenv("LLM_API_BASE", "http://llama:8080/v1").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL_CODER = os.getenv("LLM_MODEL_CODER", "qwen2.5-3b-instruct")
API_KEY = os.getenv("API_KEY", "")
try:
    GUARDIAN_TIMEOUT = float(os.getenv("GUARDIAN_TIMEOUT_SECONDS", "5"))
except ValueError:
    GUARDIAN_TIMEOUT = 5.0
if not 0 < GUARDIAN_TIMEOUT <= 60:
    GUARDIAN_TIMEOUT = 5.0
EXECUTE_COMMANDS = os.getenv("EXECUTE_COMMANDS", "false").lower() == "true"
EXECUTION_WORKSPACE = os.getenv("EXECUTION_WORKSPACE", "/workspace")
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv("RATE_LIMIT_STORAGE_URI", "memory://"),
)


def check_auth():
    return bool(
        API_KEY
        and API_KEY != "CHANGE_ME"
        and hmac.compare_digest(request.headers.get("X-API-Key", "").encode(), API_KEY.encode())
    )


def get_auth_headers():
    return {"X-API-Key": API_KEY} if API_KEY else {}


def call_guardian(method, path, *, timeout, **kwargs):
    """Only HTTP 200 is an answer; never follow a redirect with the API key."""
    response = requests.request(
        method, f"{GUARDIAN_URL}{path}", allow_redirects=False, timeout=timeout, **kwargs
    )
    if response.status_code != 200:
        raise requests.HTTPError(
            f"Unexpected Guardian status {response.status_code}", response=response
        )
    return response


def clean_command(text):
    if not isinstance(text, str):
        raise ValueError("Command generation returned a non-string")
    match = re.fullmatch(r"\s*```(?:bash)?\s*\n?(.*?)\n?```\s*", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


# SECURITY NOTICE: This function executes LLM-generated commands directly in the
# container via /bin/bash -c. Intended for DEMO/RESEARCH only. In production, replace
# with a proper sandbox (gVisor, Firejail, nsjail, or ephemeral VM per execution).
def run_command(command):
    try:
        # Do not inherit API keys, model tokens, BASH_ENV or attacker-modified PATH.
        result = subprocess.run(
            ["/bin/bash", "--noprofile", "--norc", "-c", command],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=EXECUTION_WORKSPACE,
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": "/tmp",
                "LANG": "C.UTF-8",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
            },
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
    except subprocess.TimeoutExpired:
        # Timeout does not mean no side effect occurred; never retry execution here.
        return {"error": "Command timed out; side effects may have occurred", "exit_code": 124}
    except OSError:
        return {"error": "Execution failed", "exit_code": 1}


def generate_command(task):
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    response = requests.post(
        f"{LLM_API_BASE}/chat/completions",
        headers=headers,
        json={
            "model": LLM_MODEL_CODER,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Generate one bash command for: {task}. "
                        "Return ONLY the command, no markdown or explanation."
                    ),
                }
            ],
            "temperature": 0,
            "max_tokens": 128,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Invalid generation response") from exc
    return clean_command(content)


@app.get("/health")
def health():
    return jsonify({"status": "healthy"}), 200


@app.post("/execute")
@limiter.limit("60 per minute")
def execute():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400
    task, task_id = data.get("task"), data.get("task_id")
    if EXECUTE_COMMANDS and not task_id:
        return jsonify({"error": "Real execution requires a registered task_id"}), 400
    try:
        if task_id is not None:
            if not isinstance(task_id, str) or len(task_id) > 64:
                return jsonify({"error": "Invalid task_id"}), 400
            response = call_guardian(
                "GET", f"/tasks/{task_id}", headers=get_auth_headers(), timeout=GUARDIAN_TIMEOUT
            )
            context = response.json()
            if not isinstance(context, dict) or context.get("trust") != "registered":
                raise ValueError("Invalid trusted task context")
            if task is not None and task != context.get("task"):
                return jsonify({"error": "Task differs from registered task"}), 409
            task = context.get("task")
            if EXECUTE_COMMANDS and (
                context.get("workspace") != EXECUTION_WORKSPACE
                or not Path(EXECUTION_WORKSPACE).is_dir()
            ):
                return jsonify(
                    {"error": "Registered workspace is not the configured execution workspace"}
                ), 409
        if not isinstance(task, str) or not task.strip() or len(task) > 4096:
            return jsonify({"error": "An explicit bounded task is required"}), 400
        command = generate_command(task)
        validation_body = {"command": command, "task": task, "llm_provider": LLM_PROVIDER}
        if task_id:
            validation_body["task_id"] = task_id
        response = call_guardian(
            "POST",
            "/validate",
            json=validation_body,
            headers=get_auth_headers(),
            timeout=GUARDIAN_TIMEOUT,
        )
        validation = response.json()
        if not isinstance(validation, dict) or type(validation.get("approved")) is not bool:
            raise ValueError("Invalid Guardian authorization response")
        if validation["approved"] is False:
            return jsonify(
                {
                    "status": "rejected",
                    "command": command,
                    "reason": validation.get("reason", "Blocked"),
                }
            ), 200
        validation_id = validation.get("validation_id")
        if not isinstance(validation_id, str) or not 0 < len(validation_id) <= 64:
            raise ValueError("Missing validation identity")
        if EXECUTE_COMMANDS:
            outcome = run_command(command)
            status = "executed" if outcome["exit_code"] == 0 else "execution_error"
        else:
            status = "simulated"
            outcome = {
                "stdout": "[DRY-RUN] Approved command was not executed.",
                "stderr": "",
                "exit_code": 0,
            }
        try:
            call_guardian(
                "POST",
                "/report",
                json={"validation_id": validation_id, "command": command, "status": status},
                headers=get_auth_headers(),
                timeout=GUARDIAN_TIMEOUT,
            )
        except (requests.RequestException, ValueError):
            # An uncertain outcome must remain visible. Never repeat the command
            # automatically just because its post-execution report was lost.
            return jsonify(
                {
                    "status": "outcome_unreported",
                    "execution_may_have_occurred": EXECUTE_COMMANDS,
                    "validation_id": validation_id,
                    "reason": "Check audit and agent state; do not blindly retry",
                }
            ), 503
        return jsonify(
            {
                "status": status,
                "command": command,
                "validation_id": validation_id,
                "output": outcome.get("stdout", ""),
                "stderr": outcome.get("stderr", ""),
                "exit_code": outcome["exit_code"],
                "error": outcome.get("error", ""),
                "llm_provider": LLM_PROVIDER,
            }
        ), 200
    except (requests.RequestException, ValueError, TypeError):
        return jsonify(
            {
                "status": "error",
                "reason": "Generation or Guardian validation unavailable; command not executed",
            }
        ), 502

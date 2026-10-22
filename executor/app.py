"""Optional command executor. It runs only a token-bound approved command.

The container provides the isolation boundary: non-root, no network, read-only
root filesystem, tmpfs workspace and dropped capabilities. It is a hardened
container, not a microVM or a production sandbox.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time

from flask import Flask, jsonify, request

try:  # container layout
    from execution_token import verify_payload  # pyright: ignore[reportMissingImports]
except ImportError:  # repository and tests
    from guardian.guardian.execution_token import verify_payload

MAX_OUTPUT = 65536
TIMEOUT_SECONDS = 5
USED_TOKENS: dict[str, int] = {}
USED_LOCK = threading.Lock()


def _clean_output(value: bytes) -> str:
    return value[:MAX_OUTPUT].decode("utf-8", errors="replace")


def run_command(command: str, workspace: str = "/workspace") -> dict:
    try:
        result = subprocess.run(
            ["/bin/bash", "--noprofile", "--norc", "-c", command],
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            cwd=workspace,
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": "/tmp",
                "LANG": "C.UTF-8",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
            },
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "exit_code": 124,
            "stdout": _clean_output(exc.stdout or b""),
            "stderr": "Command timed out. Side effects may have occurred.",
        }
    except OSError:
        return {
            "status": "error",
            "exit_code": 1,
            "stdout": "",
            "stderr": "Execution failed.",
        }
    return {
        "status": "executed" if result.returncode == 0 else "execution_error",
        "exit_code": result.returncode,
        "stdout": _clean_output(result.stdout),
        "stderr": _clean_output(result.stderr),
    }


def create_app(key: str | None = None, workspace: str | None = None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16384
    secret = key if key is not None else os.getenv("EXECUTOR_HMAC_KEY", "")
    workdir = workspace or os.getenv("EXECUTOR_WORKSPACE", "/workspace")

    @app.get("/health")
    def health():
        return jsonify({"status": "healthy"})

    @app.post("/execute")
    def execute():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "JSON object required"}), 400
        command = data.get("command")
        token = data.get("token")
        if not isinstance(command, str) or not command or len(command) > 8192:
            return jsonify({"error": "Invalid command"}), 400
        if not isinstance(token, str) or len(token) > 4096:
            return jsonify({"error": "Invalid authorization"}), 401
        payload = verify_payload(token, command, secret)
        if payload is None:
            return jsonify({"error": "Authorization denied"}), 401
        nonce = payload.get("nonce")
        validation_id = payload.get("vid")
        if not isinstance(nonce, str) or not isinstance(validation_id, str):
            return jsonify({"error": "Authorization denied"}), 401
        now = int(time.time())
        with USED_LOCK:
            for old_nonce, expires in list(USED_TOKENS.items()):
                if expires < now:
                    USED_TOKENS.pop(old_nonce, None)
            if nonce in USED_TOKENS:
                return jsonify({"error": "Authorization already used"}), 409
            USED_TOKENS[nonce] = int(payload.get("exp", now))
        result = run_command(command, workdir)
        result["validation_id"] = validation_id
        return jsonify(result), 200

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002)

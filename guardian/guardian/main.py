"""Fail-closed command authorization. Models may narrow, never broaden policy."""

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
import threading
import uuid
from pathlib import Path

import regex
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from database.audit_logger import connect, database_path, init_db, log_command
from database.audit_logger import mask_secrets as mask_secrets
from guardian.guardian import intent
from guardian.guardian.auth import check_auth
from guardian.guardian.configuration import load_learned, load_policy, read_yaml, update_learned
from guardian.guardian.forensics_routes import forensics_bp
from guardian.guardian.shell_commands import UnsupportedShellError, parse_commands
from guardian.guardian.shell_commands import extract_binaries as extract_binaries
from guardian.guardian.system_one import load_config as load_system_one_config
from guardian.guardian.system_one import observe
from guardian.guardian.task_context import get_task, register_task

logger = logging.getLogger("guardian")
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day"],
    storage_uri=os.getenv("RATE_LIMIT_STORAGE_URI", "memory://"),
)
app.register_blueprint(forensics_bp)

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
DB_PATH = database_path()
POLICY_PATH = os.getenv("POLICY_PATH", str(CONFIG_DIR / "policy.yaml"))
PATTERNS_PATH = os.getenv("PATTERNS_PATH", str(CONFIG_DIR / "patterns.yaml"))
LEARNED_PATH = os.getenv("LEARNED_PATH", str(CONFIG_DIR.parent / "learned/learned_patterns.yaml"))
MAX_COMMAND_LENGTH = 1024
MAX_TASK_LENGTH = 4096
MAX_PATTERN_LENGTH = 200
REGEX_TIMEOUT = 0.05
MAX_CONCURRENT_VALIDATIONS = 10
_validation_semaphore = threading.BoundedSemaphore(MAX_CONCURRENT_VALIDATIONS)


class RegexEvaluationError(RuntimeError):
    pass


def safe_compile(pattern_str, source="static"):
    if not isinstance(pattern_str, str) or not pattern_str or len(pattern_str) > MAX_PATTERN_LENGTH:
        return None
    try:
        # Non-greedy quantifiers do NOT prevent ReDoS. Keep regex meaning intact
        # and use an engine-enforced timeout instead of an uncancellable thread.
        return regex.compile(pattern_str, regex.IGNORECASE)
    except regex.error:
        logger.warning("Invalid regex in category %s", source)
        return None


def regex_match_with_timeout(pattern, text):
    try:
        compiled = (
            pattern
            if isinstance(pattern, regex.Pattern)
            else regex.compile(pattern.pattern, pattern.flags)
        )
        return compiled.search(text, timeout=REGEX_TIMEOUT)
    except (TimeoutError, regex.error) as exc:
        raise RegexEvaluationError("Regex evaluation failed; execution denied") from exc


def normalize_command(command):
    """Heuristic inspection view only. Never parse/execute this altered string."""
    normalized = re.sub(r"\$\{IFS\}", " ", command)
    normalized = re.sub(r"\$'\\[tn]'", " ", normalized)
    for pattern, decoder in [
        (r"""echo\s+(['"]?)([0-9a-fA-F]+)\1\s*\|\s*xxd\s+-r\s+-p""", bytes.fromhex),
        (r"""echo\s+(['"]?)([A-Za-z0-9+/=]+)\1\s*\|\s*base64\s+-d""", base64.b64decode),
    ]:
        match = re.search(pattern, normalized)
        if match:
            try:
                normalized = normalized.replace(
                    match.group(0), decoder(match.group(2)).decode("utf-8", errors="strict")
                )
            except (ValueError, UnicodeError):
                pass  # The raw encoding operation is still checked by L2.
    normalized = re.sub(r"\$\((.*?)\)", r"\1", normalized)
    normalized = re.sub(r"`(.*?)`", r"\1", normalized)
    normalized = re.sub(r"""['"]""", "", normalized)
    normalized = re.sub(r"\\(.)", r"\1", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def compile_static_patterns(path):
    document = read_yaml(path)
    categories = document.get("patterns")
    if not isinstance(categories, dict):
        raise ValueError("patterns.yaml requires categories")
    compiled_patterns = []
    for category, entries in categories.items():
        if not isinstance(entries, list):
            raise ValueError("Pattern categories must contain lists")
        for entry in entries:
            compiled = safe_compile(
                entry.get("pattern") if isinstance(entry, dict) else None, category
            )
            if compiled is None:
                raise ValueError("Invalid static pattern; refusing partial protection")
            compiled_patterns.append(
                (compiled, category, category in {"subshell_execution", "encoding_bypass"})
            )
    if not compiled_patterns:
        raise ValueError("Guardian cannot start without static patterns")
    return compiled_patterns


policy = load_policy(POLICY_PATH)
patterns = compile_static_patterns(PATTERNS_PATH)
system_one_config = load_system_one_config(
    os.getenv("SYSTEM_ONE_CONFIG", str(CONFIG_DIR / "system_one.yaml"))
)
init_db(DB_PATH)


def validate_command(command, task=None, *, observer=None):
    if not _validation_semaphore.acquire(blocking=False):
        return False, "Blocked: Guardian under load", "system_load"
    try:
        if not isinstance(command, str) or not command.strip() or "\x00" in command:
            return False, "Blocked: non-empty command string required", "input"
        if len(command) > MAX_COMMAND_LENGTH:
            return False, f"Blocked: command exceeds max length ({MAX_COMMAND_LENGTH})", "input"
        if not isinstance(task, str) or not task.strip() or len(task) > MAX_TASK_LENGTH:
            return False, "Blocked: explicit bounded task string required", "input"
        try:
            commands = parse_commands(command)
        except UnsupportedShellError:
            return False, "Blocked: unsupported or malformed shell syntax", "shell"
        zones = policy["zones"]
        permitted = set(zones["green"]["binaries"]) | set(zones["yellow"]["binaries"])
        for part in commands:
            if (
                not part.trusted_executable
                or part.binary not in permitted
                or part.binary in zones["red"]["binaries"]
            ):
                return False, "Blocked: executable is not authorized by policy", "allowlist"
        try:
            learned = []
            for item in load_learned(LEARNED_PATH)["learned_patterns"]:
                compiled = safe_compile(item["pattern"], "learned")
                if compiled is None:
                    raise ValueError("Invalid persisted learned pattern")
                learned.append((compiled, "learned_pattern", False))
            normalized = normalize_command(command)
            # Dual-path structural awareness: always inspect the exact raw input;
            # normalization is only an additional non-authoritative detection view.
            for pattern, category, structural in [*patterns, *learned]:
                if regex_match_with_timeout(pattern, command) or (
                    not structural and regex_match_with_timeout(pattern, normalized)
                ):
                    return False, f"Blocked: security pattern ({category})", "regex"
        except (RegexEvaluationError, ValueError, OSError):
            return False, "Blocked: pattern protection unavailable", "regex_error"
        mapping = intent.check_intent_mapping(command, task)
        if mapping["blocked"]:
            return False, mapping["reason"], mapping["intent_source"]
        if observer is not None:
            # Observation has no authority: its returned value is never consulted.
            observer()
        if mapping["needs_llm"]:
            semantic = intent.check_intent_llm(command, task)
            return not semantic["blocked"], semantic["reason"], semantic["intent_source"]
        return True, "Approved", "mapping"
    finally:
        _validation_semaphore.release()


@app.get("/health")
def health():
    return jsonify({"status": "healthy"}), 200


@app.post("/validate")
@limiter.limit("60 per minute")
def validate():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400
    command, task = data.get("command"), data.get("task")
    task_id = data.get("task_id")
    if task_id is not None:
        try:
            context = get_task(task_id, DB_PATH)
            if context["policy_version"] != policy["version"]:
                raise ValueError("Policy changed; task must be registered again")
        except ValueError:
            return jsonify(
                {"approved": False, "error": "Invalid, expired or stale task context"}
            ), 409
        if task is not None and task != context["task"]:
            return jsonify(
                {"approved": False, "error": "Task differs from registered context"}
            ), 409
        task = context["task"]
    else:
        context = {"task": task, "trust": "caller_supplied", "policy_version": policy["version"]}
    untrusted_output = data.get("untrusted_tool_output", "")
    if not isinstance(untrusted_output, str) or len(untrusted_output) > 8192:
        return jsonify({"error": "Invalid untrusted observation"}), 400
    if not isinstance(command, str) or not isinstance(task, str):
        return jsonify({"error": "command and task must be strings"}), 400
    provider = data.get("llm_provider", "unknown")
    if not isinstance(provider, str) or len(provider) > 100:
        return jsonify({"error": "Invalid provider"}), 400
    observation = {
        "mode": system_one_config.mode,
        "status": "not_run_baseline_rejected",
        "decision_unchanged": True,
    }

    def observer():
        history = []
        if task_id:
            connection = connect(DB_PATH)
            try:
                rows = connection.execute(
                    "SELECT command,status FROM command_log WHERE json_extract(metadata,'$.task_id')=? ORDER BY id DESC LIMIT 5",
                    (task_id,),
                ).fetchall()
                history = [dict(row) for row in reversed(rows)]
            finally:
                connection.close()
        observation.update(
            observe(
                system_one_config,
                command,
                context,
                history=history,
                untrusted_output=untrusted_output,
            )
        )

    approved, reason, source = validate_command(command, task, observer=observer)
    validation_id = str(uuid.uuid4())
    try:
        # Approval is NOT execution. If audit fails, do not issue authorization.
        log_command(
            task,
            command,
            "approved" if approved else "rejected",
            provider,
            reason,
            intent_source=source,
            validation_id=validation_id,
            path=DB_PATH,
            metadata={
                "task_id": task_id,
                "policy_version": policy["version"],
                "system_one": observation,
            },
        )
    except Exception:
        logger.error("Audit append failed; authorization withheld")
        return jsonify({"approved": False, "error": "Audit unavailable"}), 503
    return jsonify(
        {
            "approved": approved,
            "reason": reason,
            "intent_source": source,
            "validation_id": validation_id,
            "system_one": observation,
        }
    ), 200


def operator_authenticated():
    key = os.getenv("TASK_API_KEY", "")
    return bool(
        key
        and key not in {"CHANGE_ME", os.getenv("API_KEY", "")}
        and hmac.compare_digest(request.headers.get("X-Task-Key", "").encode(), key.encode())
    )


@app.post("/tasks")
@limiter.limit("10 per minute")
def create_task():
    if not check_auth() or not operator_authenticated():
        return jsonify({"error": "Operator authorization required"}), 403
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400
    try:
        context = register_task(data, policy["version"], DB_PATH)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(context), 201


@app.get("/tasks/<task_id>")
def read_task(task_id):
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        context = get_task(task_id, DB_PATH)
    except ValueError:
        return jsonify({"error": "Invalid or expired task"}), 404
    return jsonify(context), 200


@app.get("/audit")
@limiter.limit("30 per minute")
def audit_view():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    connection = None
    try:
        connection = connect(DB_PATH)
        total = connection.execute(
            "SELECT COUNT(*) FROM command_log WHERE status IN ('approved','rejected') OR validation_id IS NULL"
        ).fetchone()[0]
        executed = connection.execute(
            "SELECT COUNT(*) FROM command_log WHERE status='executed'"
        ).fetchone()[0]
        rejected = connection.execute(
            "SELECT COUNT(*) FROM command_log WHERE status='rejected'"
        ).fetchone()[0]
        rows = connection.execute(
            "SELECT timestamp,task,command,status,llm_provider,guardian_reason,intent_source FROM command_log ORDER BY id DESC LIMIT 20"
        ).fetchall()
    except sqlite3.Error:
        return jsonify({"error": "Audit unavailable"}), 503
    finally:
        if connection is not None:
            connection.close()
    return jsonify(
        {
            "stats": {"total": total, "executed": executed, "rejected": rejected},
            "commands": [dict(row) for row in rows],
        }
    ), 200


@app.post("/report")
@limiter.limit("60 per minute")
def report():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400
    validation_id, command, status = (
        data.get("validation_id"),
        data.get("command"),
        data.get("status"),
    )
    if (
        not isinstance(validation_id, str)
        or len(validation_id) > 64
        or not isinstance(command, str)
        or len(command) > MAX_COMMAND_LENGTH
        or not isinstance(status, str)
        or status not in {"executed", "simulated", "execution_error"}
    ):
        return jsonify(
            {"error": "Bounded validation_id, command and terminal status required"}
        ), 400
    connection = connect(DB_PATH)
    try:
        decision = connection.execute(
            "SELECT * FROM command_log WHERE validation_id=? AND status='approved'",
            (validation_id,),
        ).fetchone()
        previous = connection.execute(
            "SELECT status FROM command_log WHERE validation_id=? AND status IN ('executed','simulated','execution_error')",
            (validation_id,),
        ).fetchone()
    finally:
        connection.close()
    if not decision or hashlib.sha256(command.encode()).hexdigest() != decision["command_hash"]:
        return jsonify({"error": "No matching approved validation"}), 409
    if previous:
        return jsonify({"status": "logged"}), 200 if previous["status"] == status else 409
    try:
        log_command(
            decision["task"],
            command,
            status,
            decision["llm_provider"],
            "Authenticated agent outcome",
            int(status == "simulated"),
            intent_source="report",
            validation_id=validation_id,
            path=DB_PATH,
            metadata={"task_id": json.loads(decision["metadata"]).get("task_id")},
        )
    except sqlite3.IntegrityError:
        return jsonify({"error": "Outcome already recorded; inspect existing result"}), 409
    except Exception:
        return jsonify({"error": "Audit unavailable"}), 503
    return jsonify({"status": "logged"}), 200


@app.post("/learn")
@limiter.limit("10 per minute")
def learn():
    if not check_auth() or not operator_authenticated():
        return jsonify({"error": "Operator authorization required"}), 403
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or safe_compile(data.get("pattern"), "reviewed") is None:
        return jsonify({"error": "Valid bounded pattern required"}), 400
    description = data.get("description", "Explicitly reviewed pattern")
    if not isinstance(description, str) or len(description) > 300:
        return jsonify({"error": "Invalid description"}), 400
    try:
        update_learned(
            LEARNED_PATH, approved={"pattern": data["pattern"], "description": description}
        )
    except (OSError, ValueError):
        return jsonify({"error": "Pattern not persisted; no in-memory change made"}), 503
    return jsonify({"status": "learned"}), 201

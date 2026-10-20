"""Single SQLite/HMAC audit authority, including non-destructive legacy migration.

Old unsigned records are preserved and explicitly reported as unverifiable. The
first new signed record anchors their full contents; it does not retroactively
prove their original authenticity. A trusted external checkpoint is still needed
to detect removal of a valid suffix or compromise of the signing key.
"""

import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "state/audit/audit.db"
SIGNED_FIELDS = (
    "id",
    "timestamp",
    "task",
    "command",
    "status",
    "llm_provider",
    "guardian_reason",
    "intent_source",
    "prev_hash",
    "simulated",
    "validation_id",
    "command_hash",
    "metadata",
    "hash_version",
)


def database_path(path=None):
    return str(path if path is not None else os.getenv("DB_PATH", str(DB_PATH)))


def signing_key():
    key = os.getenv("LOG_HMAC_KEY") or os.getenv("API_KEY")
    if not key or key == "CHANGE_ME":
        raise ValueError("An audit signing key is required")
    return key


def connect(path=None):
    connection = sqlite3.connect(database_path(path), timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def mask_secrets(text):
    text = str(text)
    patterns = [
        (
            r'(?i)(api[_-]?key|token|auth|password|secret|credential|private[_-]?key)["\s:=]+([A-Za-z0-9_.+/-]{8,})',
            r"\1=***MASKED***",
        ),
        (r"(?i)\b(sk-(?:proj-|ant-)?[A-Za-z0-9_-]{12,})", "sk-***MASKED***"),
        (r"\bgsk_[A-Za-z0-9_-]{12,}", "gsk_***MASKED***"),
        (r"\bAIza[0-9A-Za-z_-]{35}", "AIza***MASKED***"),
        (r"(?i)(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", r"\1***MASKED***"),
        (r"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}", "github_***MASKED***"),
        (r"\b[0-9a-f]{40}\b", "***MASKED_HEX40***"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def redact(value):
    if isinstance(value, str):
        return mask_secrets(value)
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


def canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _digest(record, key):
    payload = canonical({field: record[field] for field in SIGNED_FIELDS}).encode()
    return hmac.new(key.encode(), payload, hashlib.sha256).hexdigest()


def calculate_row_hash(prev_hash, timestamp, task, command, status, simulated, key=None):
    """Historical v1 verifier only; all new records use the full v2 envelope."""
    payload = f"{prev_hash}|{timestamp}|{task}|{command}|{status}|{simulated}".encode()
    return hmac.new((key or signing_key()).encode(), payload, hashlib.sha256).hexdigest()


def _legacy_anchor(rows):
    return "LEGACY:" + hashlib.sha256(canonical([dict(row) for row in rows]).encode()).hexdigest()


def _enable_wal(connection, attempts=20, delay=0.1):
    """Enable WAL with retries for concurrent Gunicorn startup.

    Changing the journal mode needs an exclusive lock and does not always honor
    the busy timeout. Workers start in parallel against a fresh file.
    """
    for attempt in range(attempts):
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            return
        except sqlite3.OperationalError as exc:
            message = str(exc).lower()
            if "locked" not in message and "busy" not in message:
                raise
            if attempt == attempts - 1:
                raise
            time.sleep(delay)


def init_db(path=None):
    target = database_path(path)
    if target != ":memory:":
        Path(target).parent.mkdir(parents=True, exist_ok=True)
    connection = connect(path)
    try:
        connection.execute("PRAGMA busy_timeout=15000")
        _enable_wal(connection)
        # BEGIN IMMEDIATE serializes migration across Gunicorn processes as well
        # as appends; never catch arbitrary migration errors as 'already exists'.
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS command_log (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, task TEXT NOT NULL, command TEXT NOT NULL, status TEXT NOT NULL, llm_provider TEXT, guardian_reason TEXT)"
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(command_log)")}
        # SQL identifiers cannot be bound parameters. These migrations are
        # literal statements, not identifiers or declarations taken from input.
        if "intent_source" not in columns:
            connection.execute("ALTER TABLE command_log ADD COLUMN intent_source TEXT")
        if "prev_hash" not in columns:
            connection.execute("ALTER TABLE command_log ADD COLUMN prev_hash TEXT")
        if "row_hash" not in columns:
            connection.execute("ALTER TABLE command_log ADD COLUMN row_hash TEXT")
        if "simulated" not in columns:
            connection.execute("ALTER TABLE command_log ADD COLUMN simulated INTEGER DEFAULT 0")
        if "validation_id" not in columns:
            connection.execute("ALTER TABLE command_log ADD COLUMN validation_id TEXT")
        if "command_hash" not in columns:
            connection.execute("ALTER TABLE command_log ADD COLUMN command_hash TEXT")
        if "metadata" not in columns:
            connection.execute(
                "ALTER TABLE command_log ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'"
            )
        if "hash_version" not in columns:
            connection.execute(
                "ALTER TABLE command_log ADD COLUMN hash_version INTEGER NOT NULL DEFAULT 0"
            )
        # Use the one canonical schema for indexes and auxiliary tables too.
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        for statement in schema.split(";"):
            if statement.strip():
                connection.execute(statement)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def log_command(
    task,
    command,
    status,
    llm_provider=None,
    guardian_reason=None,
    simulated=0,
    *,
    intent_source=None,
    metadata=None,
    validation_id=None,
    path=None,
):
    key = signing_key()
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task": mask_secrets(task),
        "command": mask_secrets(command),
        "status": status,
        "llm_provider": mask_secrets(llm_provider or "unknown"),
        "guardian_reason": mask_secrets(guardian_reason or ""),
        "simulated": int(simulated),
        "intent_source": intent_source,
        "validation_id": validation_id,
        "command_hash": hashlib.sha256(command.encode()).hexdigest(),
        "metadata": canonical(redact(metadata or {})),
        "hash_version": 2,
    }
    connection = connect(path)
    try:
        # Read-last + append + HMAC update is ONE transaction. Without this lock,
        # concurrent writers could both point at the same previous hash (a fork).
        connection.execute("BEGIN IMMEDIATE")
        last = connection.execute("SELECT * FROM command_log ORDER BY id DESC LIMIT 1").fetchone()
        record["id"] = (last["id"] + 1) if last else 1
        if last and last["row_hash"]:
            record["prev_hash"] = last["row_hash"]
        elif last:
            legacy = connection.execute("SELECT * FROM command_log ORDER BY id").fetchall()
            if any(row["row_hash"] for row in legacy):
                raise ValueError("Unsigned record after signed audit history")
            record["prev_hash"] = _legacy_anchor(legacy)
        else:
            record["prev_hash"] = "GENESIS"
        record["row_hash"] = _digest(record, key)
        connection.execute(
            "INSERT INTO command_log (id, timestamp, task, command, status, llm_provider, guardian_reason, intent_source, prev_hash, simulated, validation_id, command_hash, metadata, hash_version, row_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [record[field] for field in (*SIGNED_FIELDS, "row_hash")],
        )
        connection.commit()
        return record["id"]
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def verify_logs(path=None, key=None):
    key = key or signing_key()
    connection = connect(path)
    try:
        rows = connection.execute("SELECT * FROM command_log ORDER BY id").fetchall()
    finally:
        connection.close()
    previous, legacy, signed, errors = "GENESIS", [], 0, []
    for row in rows:
        if not row["row_hash"]:
            if signed:
                errors.append(f"Unsigned row after signed history: {row['id']}")
            legacy.append(row)
            previous = _legacy_anchor(legacy)
            continue
        version = row["hash_version"]
        calculated = (
            _digest(row, key)
            if version == 2
            else calculate_row_hash(
                row["prev_hash"],
                row["timestamp"],
                row["task"],
                row["command"],
                row["status"],
                row["simulated"],
                key,
            )
        )
        if row["prev_hash"] != previous or not hmac.compare_digest(calculated, row["row_hash"]):
            errors.append(f"Audit integrity failure at row {row['id']}")
        previous = row["row_hash"]
        signed += 1
    return {
        "valid": not errors and not legacy,
        "signed_integrity_valid": not errors,
        "signed_rows": signed,
        "unsigned_legacy_rows": len(legacy),
        "errors": errors,
    }


def get_recent_logs(limit=20, path=None):
    connection = connect(path)
    try:
        return connection.execute(
            "SELECT timestamp, task, command, status, llm_provider FROM command_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        connection.close()

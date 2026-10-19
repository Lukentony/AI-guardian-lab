"""Server-owned authorization context, separate from agent-supplied observations."""

import hashlib
import hmac
import json
import time
import uuid

from database.audit_logger import canonical, connect, mask_secrets, signing_key


def _signature(context):
    return hmac.new(signing_key().encode(), canonical(context).encode(), hashlib.sha256).hexdigest()


def register_task(data, policy_version, path):
    task = data.get("task")
    workspace = data.get("workspace", "/workspace")
    destinations = data.get("allowed_destinations", [])
    ttl = data.get("ttl_seconds", 3600)
    if (
        not isinstance(task, str)
        or not task.strip()
        or len(task) > 4096
        or mask_secrets(task) != task
    ):
        raise ValueError("A bounded task without embedded credentials is required")
    if not isinstance(workspace, str) or not workspace.startswith("/") or len(workspace) > 1024:
        raise ValueError("An absolute workspace is required")
    if (
        not isinstance(destinations, list)
        or len(destinations) > 20
        or not all(isinstance(item, str) and 0 < len(item) <= 255 for item in destinations)
    ):
        raise ValueError("Invalid destinations")
    if type(ttl) is not int or not 60 <= ttl <= 86400:
        raise ValueError("Invalid task lifetime")
    context = {
        "task_id": str(uuid.uuid4()),
        "task": task,
        "workspace": workspace,
        "allowed_destinations": destinations,
        "policy_version": policy_version,
        "expires_at": int(time.time()) + ttl,
        "trust": "registered",
    }
    connection = connect(path)
    try:
        connection.execute(
            "INSERT INTO task_context (task_id, context, signature) VALUES (?, ?, ?)",
            (context["task_id"], canonical(context), _signature(context)),
        )
        connection.commit()
    finally:
        connection.close()
    return context


def get_task(task_id, path):
    if not isinstance(task_id, str) or not 0 < len(task_id) <= 64:
        raise ValueError("Invalid task identifier")
    connection = connect(path)
    try:
        row = connection.execute(
            "SELECT context, signature FROM task_context WHERE task_id=?", (task_id,)
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError("Unknown task")
    try:
        context = json.loads(row["context"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid stored task") from exc
    if (
        not hmac.compare_digest(_signature(context), row["signature"])
        or context.get("task_id") != task_id
    ):
        raise ValueError("Task integrity check failed")
    if context.get("expires_at", 0) <= time.time():
        raise ValueError("Task has expired")
    return context

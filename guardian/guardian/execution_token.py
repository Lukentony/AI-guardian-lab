"""Short-lived authorization tokens for the optional sandbox executor.

The token binds one approved command to one validation identity and expires.
It is not a session credential and does not authorize a different command.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

TOKEN_VERSION = 1
TOKEN_TTL_SECONDS = 60


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def command_digest(command: str) -> str:
    return hashlib.sha256(command.encode("utf-8")).hexdigest()


def issue(
    validation_id: str,
    command: str,
    key: str,
    *,
    now: float | None = None,
    ttl: int = TOKEN_TTL_SECONDS,
) -> str | None:
    if not key:
        return None
    issued = int(now if now is not None else time.time())
    payload = {
        "v": TOKEN_VERSION,
        "vid": validation_id,
        "cmd": command_digest(command),
        "exp": issued + ttl,
        "nonce": secrets.token_hex(8),
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(key.encode("utf-8"), body, hashlib.sha256).digest()
    return f"{_encode(body)}.{_encode(signature)}"


def verify_payload(
    token: str,
    command: str,
    key: str,
    *,
    now: float | None = None,
) -> dict | None:
    if not key or not isinstance(token, str) or token.count(".") != 1:
        return None
    encoded_body, encoded_signature = token.split(".", 1)
    try:
        body = _decode(encoded_body)
        signature = _decode(encoded_signature)
        payload = json.loads(body)
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("v") != TOKEN_VERSION:
        return None
    expected = hmac.new(key.encode("utf-8"), body, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        expires = int(payload["exp"])
        matches = payload["cmd"] == command_digest(command)
        validation_id = payload["vid"]
        nonce = payload["nonce"]
    except (KeyError, TypeError, ValueError):
        return None
    if not isinstance(validation_id, str) or not isinstance(nonce, str):
        return None
    if not matches or expires < int(now if now is not None else time.time()):
        return None
    return payload


def verify(
    token: str,
    command: str,
    key: str,
    *,
    now: float | None = None,
) -> bool:
    return verify_payload(token, command, key, now=now) is not None

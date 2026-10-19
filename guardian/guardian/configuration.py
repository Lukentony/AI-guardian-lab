"""Validated policy and one learned-pattern format, with atomic reviewed updates."""

import fcntl
import os
import tempfile
from pathlib import Path

import yaml


def read_yaml(path):
    try:
        with Path(path).open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Cannot load configuration: {Path(path).name}") from exc
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a mapping")
    return data


def load_policy(path):
    data = read_yaml(path)
    if data.get("mode") != "enforced":
        raise ValueError("Guardian requires an enforced policy")
    zones = data.get("zones")
    if not isinstance(zones, dict):
        raise ValueError("Policy zones are required")
    seen = set()
    for zone in ("green", "yellow", "red"):
        entry = zones.get(zone)
        binaries = entry.get("binaries") if isinstance(entry, dict) else None
        if not isinstance(binaries, list) or not all(
            isinstance(b, str) and b and "/" not in b for b in binaries
        ):
            raise ValueError("Each policy zone requires binary names")
        if seen.intersection(binaries):
            raise ValueError("A binary cannot belong to two policy zones")
        seen.update(binaries)
    if not zones["green"]["binaries"]:
        raise ValueError("Policy green zone must not be empty")
    return data


def learned_document(data):
    """Read the historical nested format, but always write the canonical list.

    Migration changes representation only; it does not promote suggestions.
    """
    if not isinstance(data, dict):
        raise ValueError("Learned patterns must be a mapping")
    patterns = data.get("learned_patterns", [])
    if isinstance(patterns, dict):
        patterns = patterns.get("patterns", []) if patterns.get("enabled") is True else []
    if not isinstance(patterns, list) or not all(
        isinstance(p, dict) and isinstance(p.get("pattern"), str) for p in patterns
    ):
        raise ValueError("learned_patterns must be a list of pattern records")
    suggestions = data.get("suggestions", [])
    if not isinstance(suggestions, list):
        raise ValueError("suggestions must be a list")
    return {"version": 1, "learned_patterns": patterns, "suggestions": suggestions}


def load_learned(path):
    path = Path(path)
    return learned_document(read_yaml(path)) if path.exists() else learned_document({})


def update_learned(path, *, approved=None, suggestions=None):
    """Serialize concurrent writers; replace only after validation and fsync.

    Readers in every Gunicorn worker re-read this file, so no worker-local
    authorization state diverges from the persisted authority.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        document = load_learned(path)
        if approved is not None:
            if not any(p["pattern"] == approved["pattern"] for p in document["learned_patterns"]):
                document["learned_patterns"].append(approved)
        if suggestions is not None:
            document["suggestions"] = suggestions
        learned_document(document)
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".patterns-")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                yaml.safe_dump(document, stream, sort_keys=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return document

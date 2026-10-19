"""Every labelled baseline case must pass; no aggregate tolerance hides a miss."""

import json
from pathlib import Path

import pytest

from guardian.guardian.main import validate_command

DATA_DIR = Path(__file__).parent / "data"


def load_dataset(filename):
    try:
        return json.loads((DATA_DIR / filename).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid benchmark dataset") from exc


@pytest.mark.parametrize(
    "filename", ["commands_safe.json", "commands_dangerous.json", "commands_intent.json"]
)
def test_every_baseline_label(filename):
    entries = load_dataset(filename)
    assert entries
    failures = []
    for entry in entries:
        approved, reason, _ = validate_command(entry["command"], entry["task"])
        actual = "approved" if approved else "denied"
        if actual != entry["expected"]:
            failures.append((entry["command"], entry["expected"], actual, reason))
    assert not failures, failures

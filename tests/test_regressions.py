import json
from pathlib import Path

import pytest
import yaml

from guardian.forensics.analyzer import analyze_escalation
from guardian.forensics.annotator import annotate_session
from guardian.forensics.parser import parse_session
from guardian.guardian import main
from guardian.guardian.configuration import load_learned, load_policy, update_learned
from scripts import pattern_learner


@pytest.mark.parametrize(
    "fixture,expected",
    [("sample_openhands.jsonl", ["ls"]), ("sample_swereact.jsonl", ["ls", "cat"])],
)
def test_real_parser_annotator_pipeline(fixture, expected):
    session = parse_session(str(Path(__file__).parent / "test_forensics/fixtures" / fixture))
    annotated = annotate_session(session)
    tools = [event for event in annotated.events if event.event.type == "tool_call"]
    assert [event.annotation.binary for event in tools] == expected
    assert all(event.annotation.risk_score == 1 for event in tools)


def test_jsonl_escalation_is_visible():
    records: list[dict] = [{"role": "user", "content": "list files"}]
    for index, command in enumerate(["ls /tmp", "sudo rm -rf /tmp/placeholder"]):
        records.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": str(index),
                        "function": {"name": "bash", "arguments": json.dumps({"command": command})},
                    }
                ],
            }
        )
    session = parse_session("\n".join(json.dumps(record) for record in records), is_file=False)
    assert analyze_escalation(annotate_session(session)).triggered


@pytest.mark.parametrize("arguments", [{"command": "ls /tmp"}, '{"command":"ls /tmp"}', "ls /tmp"])
def test_argument_shapes(arguments):
    record = {
        "role": "assistant",
        "tool_calls": [{"function": {"name": "bash", "arguments": arguments}}],
    }
    session = parse_session(json.dumps(record), is_file=False)
    assert session.events[0].tool_input == {"command": "ls /tmp"}


def test_legacy_learned_format_migrates_without_losing_reviewed_entries(tmp_path):
    path = tmp_path / "patterns.yaml"
    path.write_text(
        yaml.safe_dump({"learned_patterns": {"enabled": True, "patterns": [{"pattern": "old"}]}})
    )
    update_learned(path, approved={"pattern": "new"})
    assert [item["pattern"] for item in load_learned(path)["learned_patterns"]] == ["old", "new"]
    assert isinstance(yaml.safe_load(path.read_text())["learned_patterns"], list)


def test_suggestions_never_become_active(monkeypatch, tmp_path):
    path = tmp_path / "patterns.yaml"
    monkeypatch.setattr(pattern_learner, "CONFIG_PATH", path)
    pattern_learner.save_suggestions(
        [{"pattern": "ls", "confidence": 100, "status": "pending_review"}]
    )
    assert load_learned(path)["learned_patterns"] == []


def test_reviewed_pattern_visible_to_every_request(client, headers, monkeypatch):
    monkeypatch.setenv("TASK_API_KEY", "operator-test-key")
    operator = {**headers, "X-Task-Key": "operator-test-key"}
    assert main.validate_command("echo reviewtoken", "print message")[0]
    assert (
        client.post("/learn", json={"pattern": "reviewtoken"}, headers=headers).status_code == 403
    )
    assert (
        client.post("/learn", json={"pattern": "reviewtoken"}, headers=operator).status_code == 201
    )
    assert not main.validate_command("echo reviewtoken", "print message")[0]


def test_policy_never_silently_becomes_permissive(tmp_path):
    path = tmp_path / "policy.yaml"
    with pytest.raises(ValueError):
        load_policy(path)
    path.write_text("mode: permissive\nzones: {}\n")
    with pytest.raises(ValueError):
        load_policy(path)

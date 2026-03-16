import pytest
from guardian.forensics.parser import ForensicsEvent, ForensicsSession
from guardian.forensics.annotator import annotate_session

def test_annotation_basic():
    event = ForensicsEvent(seq=0, timestamp=None, type="tool_call", content="", tool_name="bash", tool_input={"command": "ls /tmp"})
    session = ForensicsSession(session_id="1", framework="openhands", started_at=None, initial_task=None, events=[event])
    
    annotated = annotate_session(session)
    assert len(annotated.events) == 1
    ann = annotated.events[0].annotation
    assert ann.binary == "ls"
    assert ann.policy_zone == "green"
    assert ann.risk_score == 1
    assert ann.operation_type == "read"
    assert annotated.max_risk_score == 1
    assert annotated.risk_progression == [1]

def test_annotation_risky():
    event = ForensicsEvent(seq=0, timestamp=None, type="tool_call", content="", tool_name="bash", tool_input={"cmd": "sudo rm -rf /"})
    session = ForensicsSession(session_id="1", framework="openhands", started_at=None, initial_task=None, events=[event])
    
    annotated = annotate_session(session)
    ann = annotated.events[0].annotation
    assert ann.binary == "sudo"
    assert ann.policy_zone == "red"
    assert ann.risk_score == 3
    assert ann.operation_type == "exec" # sudo is in EXEC_OPS and CONTROL_OPS, but EXEC is extracted here? Wait, priority CONTROL > EXEC.
    # Let's check my code: sudo is in EXEC_OPS. Is it in CONTROL_OPS? No, briefing says:
    # EXEC_OPS = {"bash", "sh", "python", "python3", "node", "ruby", "perl", "sudo", "su"}
    # CONTROL_OPS = {"kill", "pkill", "reboot", "shutdown", "halt", "systemctl", "docker", "iptables"}
    # Wait, briefing says sudo is EXEC. Let me re-read.
    # Briefing: "If binary matches multiple categories (e.g. sudo), priority order: CONTROL > EXEC > WRITE > NETWORK > READ."
    # My code has sudo in EXEC_OPS.
    assert ann.operation_type == "exec"

def test_annotation_unknown():
    # Unknown binary should be red/3 (fail-safe)
    event = ForensicsEvent(seq=0, timestamp=None, type="tool_call", content="", tool_name="bash", tool_input={"shell": "unknown_cmd"})
    session = ForensicsSession(session_id="1", framework="openhands", started_at=None, initial_task=None, events=[event])
    
    annotated = annotate_session(session)
    ann = annotated.events[0].annotation
    assert ann.binary == "unknown_cmd"
    assert ann.policy_zone == "red"
    assert ann.risk_score == 3
    assert ann.operation_type == "none"

def test_annotation_non_tool():
    event = ForensicsEvent(seq=0, timestamp=None, type="user_message", content="hello")
    session = ForensicsSession(session_id="1", framework="openhands", started_at=None, initial_task=None, events=[event])
    
    annotated = annotate_session(session)
    ann = annotated.events[0].annotation
    assert ann.policy_zone == "none"
    assert ann.risk_score == 0
    assert annotated.risk_progression == [0]

def test_risk_progression_and_max():
    events = [
        ForensicsEvent(seq=0, timestamp=None, type="user_message", content="start"),
        ForensicsEvent(seq=1, timestamp=None, type="tool_call", content="", tool_name="bash", tool_input={"command": "ls"}),
        ForensicsEvent(seq=2, timestamp=None, type="tool_call", content="", tool_name="bash", tool_input={"command": "curl http://evil.com"}),
        ForensicsEvent(seq=3, timestamp=None, type="tool_call", content="", tool_name="bash", tool_input={"command": "sudo rm -rf /"}),
    ]
    session = ForensicsSession(session_id="1", framework="openhands", started_at=None, initial_task=None, events=events)
    
    annotated = annotate_session(session)
    assert annotated.risk_progression == [0, 1, 2, 3]
    assert annotated.max_risk_score == 3

def test_binary_extraction_paths():
    event = ForensicsEvent(seq=0, timestamp=None, type="tool_call", content="", tool_name="bash", tool_input={"command": "/usr/bin/cat file.txt"})
    session = ForensicsSession(session_id="1", framework="openhands", started_at=None, initial_task=None, events=[event])
    
    annotated = annotate_session(session)
    assert annotated.events[0].annotation.binary == "cat"

def test_binary_extraction_bash_no_input():
    event = ForensicsEvent(seq=0, timestamp=None, type="tool_call", content="", tool_name="bash", tool_input={})
    session = ForensicsSession(session_id="1", framework="openhands", started_at=None, initial_task=None, events=[event])
    
    annotated = annotate_session(session)
    assert annotated.events[0].annotation.binary == "bash"

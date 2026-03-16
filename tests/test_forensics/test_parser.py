import pytest
from guardian.forensics.parser import parse_session, detect_framework

def test_detect_framework_openhands():
    lines = ['{"role": "user", "content": "hello"}']
    assert detect_framework(lines) == "openhands"

def test_detect_framework_sweagent():
    lines = ['{"thought": "think", "action": "act", "observation": "obs"}']
    assert detect_framework(lines) == "swe-agent"

def test_detect_framework_openclaw():
    lines = ['{"agent_id": "123", "openclaw": "true"}']
    assert detect_framework(lines) == "openclaw"

def test_parse_openhands_fixture():
    fixture_path = "tests/test_forensics/fixtures/sample_openhands.jsonl"
    session = parse_session(fixture_path)
    
    assert session.framework == "openhands"
    assert session.initial_task == "List files in /tmp"
    
    # Check event sequence
    # 0: system
    # 1: user_message
    # 2: assistant_message (text)
    # 3: tool_call (ls /tmp)
    # 4: tool_result
    # 5: assistant_message (final)
    
    assert len(session.events) == 6
    assert session.events[0].type == "system"
    assert session.events[1].type == "user_message"
    assert session.events[2].type == "assistant_message"
    assert session.events[3].type == "tool_call"
    assert session.events[3].tool_name == "bash"
    assert session.events[4].type == "tool_result"
    assert session.events[4].tool_output == "file1.txt\nfile2.txt"
    assert session.events[5].type == "assistant_message"

def test_parse_swereact_fixture():
    fixture_path = "tests/test_forensics/fixtures/sample_swereact.jsonl"
    session = parse_session(fixture_path)
    
    assert session.framework == "swe-agent"
    assert session.initial_task is None
    
    # Each line becomes 2 events: tool_call + tool_result
    # 2 lines -> 4 events
    assert len(session.events) == 4
    assert session.events[0].type == "tool_call"
    assert session.events[1].type == "tool_result"
    assert session.events[2].type == "tool_call"
    assert session.events[3].type == "tool_result"
    assert session.events[0].tool_name == "bash"

def test_openclaw_stub():
    with pytest.raises(NotImplementedError) as excinfo:
        # Pass a line that detects as openclaw
        parse_session('{"openclaw": true}', is_file=False)
    assert "OpenClaw parser not yet implemented" in str(excinfo.value)

def test_parse_raw_string():
    raw_data = '{"role": "user", "content": "test"}'
    session = parse_session(raw_data, is_file=False)
    assert session.framework == "openhands"
    assert len(session.events) == 1
    assert session.events[0].content == "test"

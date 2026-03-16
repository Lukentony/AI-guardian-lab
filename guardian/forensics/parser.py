import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ForensicsEvent:
    seq: int
    timestamp: str | None
    type: str  # "user_message" | "assistant_message" | "tool_call" | "tool_result" | "system"
    content: str
    tool_name: str | None = None
    tool_input: dict | None = None
    tool_output: str | None = None
    call_id: str | None = None

@dataclass
class ForensicsSession:
    session_id: str
    framework: str  # "openclaw" | "openhands" | "swe-agent" | "unknown"
    started_at: str | None
    initial_task: str | None
    events: list[ForensicsEvent] = field(default_factory=list)

def detect_framework(lines: list[str]) -> str:
    """Detects the framework from the first 5 non-empty lines."""
    count = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if all(k in data for k in ["thought", "action", "observation"]):
                return "swe-agent"
            if "role" in data:
                return "openhands"
            if "openclaw" in data or "agent_id" in data:
                return "openclaw"
        except json.JSONDecodeError:
            continue
        count += 1
        if count >= 5:
            break
    return "unknown"

def _parse_openhands(lines: list[str]) -> list[ForensicsEvent]:
    events = []
    seq = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        role = data.get("role")
        content = data.get("content") or ""
        timestamp = data.get("timestamp") # Assuming it might be there, else None

        if role == "system":
            events.append(ForensicsEvent(seq=seq, timestamp=timestamp, type="system", content=content))
            seq += 1
        elif role == "user":
            events.append(ForensicsEvent(seq=seq, timestamp=timestamp, type="user_message", content=content))
            seq += 1
        elif role == "assistant":
            tool_calls = data.get("tool_calls")
            if content:
                events.append(ForensicsEvent(seq=seq, timestamp=timestamp, type="assistant_message", content=content))
                seq += 1
            if tool_calls:
                for tc in tool_calls:
                    f = tc.get("function", {})
                    events.append(ForensicsEvent(
                        seq=seq, timestamp=timestamp, type="tool_call",
                        content=f.get("arguments", ""),
                        tool_name=f.get("name"),
                        call_id=tc.get("id")
                    ))
                    seq += 1
        elif role == "tool":
            events.append(ForensicsEvent(
                seq=seq, timestamp=timestamp, type="tool_result",
                content="", # Not used for tool role in this schema
                tool_output=content,
                call_id=data.get("tool_call_id")
            ))
            seq += 1
    return events

def _parse_sweagent(lines: list[str]) -> list[ForensicsEvent]:
    events = []
    seq = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        timestamp = data.get("timestamp")
        
        # Action -> tool_call
        events.append(ForensicsEvent(
            seq=seq, timestamp=timestamp, type="tool_call",
            content=data.get("action", ""),
            tool_name="bash"
        ))
        seq += 1
        
        # Observation -> tool_result
        events.append(ForensicsEvent(
            seq=seq, timestamp=timestamp, type="tool_result",
            content="",
            tool_output=data.get("observation", "")
        ))
        seq += 1
    return events

def _parse_openclaw(lines: list[str]) -> list[ForensicsEvent]:
    raise NotImplementedError(
        "OpenClaw parser not yet implemented. "
        "Inspect /home/luca/.openclaw/agents/main/*.jsonl and implement mapping."
    )

def parse_session(input_data: str, is_file: bool = True) -> ForensicsSession:
    if is_file:
        with open(input_data, "r", encoding="utf-8") as f:
            lines = f.readlines()
    else:
        lines = input_data.splitlines()

    framework = detect_framework(lines)
    
    if framework == "swe-agent":
        events = _parse_sweagent(lines)
    elif framework == "openclaw":
        events = _parse_openclaw(lines)
    else: # Default to openhands for both "openhands" and "unknown"
        events = _parse_openhands(lines)
    
    # Session metadata metadata
    session_id = str(uuid.uuid4())
    started_at = None
    initial_task = None
    
    for event in events:
        if event.timestamp and not started_at:
            started_at = event.timestamp
        if event.type == "user_message" and not initial_task:
            initial_task = event.content
            
    return ForensicsSession(
        session_id=session_id,
        framework=framework,
        started_at=started_at,
        initial_task=initial_task,
        events=events
    )

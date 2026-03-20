import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from forensics.parser import ForensicsEvent, ForensicsSession

@dataclass
class EventAnnotation:
    operation_type: str   # "read" | "write" | "exec" | "network" | "control" | "none"
    policy_zone: str      # "green" | "yellow" | "red" | "none"
    risk_score: int       # 0=none, 1=green, 2=yellow, 3=red
    binary: str | None    # extracted binary name if tool_call, else None

@dataclass
class AnnotatedEvent:
    event: ForensicsEvent
    annotation: EventAnnotation

@dataclass
class AnnotatedSession:
    session: ForensicsSession
    events: list[AnnotatedEvent]
    max_risk_score: int        # max risk_score across all events
    risk_progression: list[int]  # risk_score per event in sequence order

# Operation mappings
READ_OPS = {"ls", "cat", "head", "tail", "grep", "find", "stat", "file", "wc", "diff", "pwd", "whoami", "uname", "hostname", "uptime", "ps", "top", "htop", "df", "du", "free", "md5sum", "sha256sum", "sort", "uniq", "cut", "awk", "sed", "tr"}
WRITE_OPS = {"rm", "rmdir", "mv", "chmod", "chown", "dd", "shred", "mkfs", "fdisk", "useradd", "userdel", "passwd", "mkdir", "cp", "touch", "tee"}
EXEC_OPS = {"bash", "sh", "python", "python3", "node", "ruby", "perl", "sudo", "su"}
NETWORK_OPS = {"curl", "wget", "ssh", "scp", "rsync", "ping", "traceroute", "nmap", "nc"}
CONTROL_OPS = {"kill", "pkill", "reboot", "shutdown", "halt", "systemctl", "docker", "iptables", "sudo", "su"}

def load_policy():
    """Load policy from YAML or fallback to defaults."""
    policy_path = Path(__file__).parent.parent / "config" / "policy.yaml"
    default_policy = {
        "green": ["ls", "cat", "pwd", "echo", "date"],
        "yellow": ["curl", "wget", "git"],
        "red": ["rm", "mv", "chmod", "sudo"]
    }
    
    if not policy_path.exists():
        return default_policy
        
    try:
        with open(policy_path, "r") as f:
            data = yaml.safe_load(f)
            zones = data.get("zones", {})
            return {
                "green": zones.get("green", {}).get("binaries", []),
                "yellow": zones.get("yellow", {}).get("binaries", []),
                "red": zones.get("red", {}).get("binaries", [])
            }
    except Exception:
        return default_policy

POLICY = load_policy()

def extract_binary(event: ForensicsEvent) -> str | None:
    """Extracts binary name from tool_call event."""
    if event.type != "tool_call":
        return None
        
    # Priority 1: Check tool_input keys
    if event.tool_input:
        for key in ["command", "cmd", "bash", "shell"]:
            cmd = event.tool_input.get(key)
            if cmd and isinstance(cmd, str):
                # Extract first token
                parts = cmd.strip().split()
                if parts:
                    binary = parts[0]
                    # Strip leading ./ or full paths
                    binary = binary.split("/")[-1]
                    return binary
                    
    # Priority 2: Fallback to tool_name if bash/shell
    if event.tool_name in ["bash", "shell"]:
        return "bash"
        
    return None

def classify_operation(binary: str | None) -> str:
    """Classifies operation type based on binary."""
    if not binary:
        return "none"
        
    if binary in CONTROL_OPS:
        return "control"
    if binary in EXEC_OPS:
        return "exec"
    if binary in WRITE_OPS:
        return "write"
    if binary in NETWORK_OPS:
        return "network"
    if binary in READ_OPS:
        return "read"
        
    return "none"

def classify_zone(binary: str | None) -> tuple[str, int]:
    """Classifies risk zone and score based on binary."""
    if not binary:
        return "none", 0
        
    if binary in POLICY["green"]:
        return "green", 1
    if binary in POLICY["yellow"]:
        return "yellow", 2
    if binary in POLICY["red"]:
        return "red", 3
        
    # Unknown binaries default to red/3 (fail-safe)
    return "red", 3

def annotate_session(session: ForensicsSession) -> AnnotatedSession:
    """Normalizes and annotates all events in a session."""
    annotated_events = []
    risk_progression = []
    max_risk = 0
    
    for event in session.events:
        if event.type == "tool_call":
            binary = extract_binary(event)
            op_type = classify_operation(binary)
            zone, score = classify_zone(binary)
            
            annotation = EventAnnotation(
                operation_type=op_type,
                policy_zone=zone,
                risk_score=score,
                binary=binary
            )
        else:
            annotation = EventAnnotation(
                operation_type="none",
                policy_zone="none",
                risk_score=0,
                binary=None
            )
            
        annotated_events.append(AnnotatedEvent(event=event, annotation=annotation))
        risk_progression.append(annotation.risk_score)
        if annotation.risk_score > max_risk:
            max_risk = annotation.risk_score
            
    return AnnotatedSession(
        session=session,
        events=annotated_events,
        max_risk_score=max_risk,
        risk_progression=risk_progression
    )

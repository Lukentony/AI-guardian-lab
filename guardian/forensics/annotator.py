import os
from dataclasses import dataclass
from pathlib import Path

from guardian.forensics.parser import ForensicsEvent, ForensicsSession
from guardian.guardian.configuration import load_policy as read_policy
from guardian.guardian.intent import binary_family
from guardian.guardian.shell_commands import UnsupportedShellError, parse_commands


@dataclass
class EventAnnotation:
    operation_type: str  # "read" | "write" | "exec" | "network" | "control" | "none"
    policy_zone: str  # "green" | "yellow" | "red" | "none"
    risk_score: int  # 0=none, 1=green, 2=yellow, 3=red
    binary: str | None  # extracted binary name if tool_call, else None


@dataclass
class AnnotatedEvent:
    event: ForensicsEvent
    annotation: EventAnnotation


@dataclass
class AnnotatedSession:
    session: ForensicsSession
    events: list[AnnotatedEvent]
    max_risk_score: int  # max risk_score across all events
    risk_progression: list[int]  # risk_score per event in sequence order


def load_policy():
    """Use the runtime policy authority; invalid policy must not look healthy."""
    policy_path = os.getenv("POLICY_PATH", str(Path(__file__).parent.parent / "config/policy.yaml"))
    zones = read_policy(policy_path)["zones"]
    return {zone: zones[zone]["binaries"] for zone in ("green", "yellow", "red")}


POLICY = load_policy()


def extract_binary(event: ForensicsEvent) -> str | None:
    """Extracts binary name from tool_call event."""
    if event.type != "tool_call":
        return None

    # Extract command from tool_input (standard mapping)
    if event.tool_input:
        for key in ["command", "cmd", "bash", "shell"]:
            cmd = event.tool_input.get(key)
            if cmd and isinstance(cmd, str):
                try:
                    parts = parse_commands(cmd.strip())
                except UnsupportedShellError:
                    # Unsupported shell semantics remain high risk; do not guess
                    # a green zone from a tool name that hides the real command.
                    return "<unsupported-shell>"
                return max((part.binary for part in parts), key=lambda name: classify_zone(name)[1])

    # Fallback to tool_name if command key is missing
    if event.tool_name:
        return event.tool_name.split("/")[-1]
    return None


def classify_operation(binary: str | None) -> str:
    """Classifies operation type based on binary."""
    if not binary:
        return "none"

    family = binary_family(binary)
    return {"process": "control", "delete": "write"}.get(family or "none", family or "none")


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
                operation_type=op_type, policy_zone=zone, risk_score=score, binary=binary
            )
        else:
            annotation = EventAnnotation(
                operation_type="none", policy_zone="none", risk_score=0, binary=None
            )

        annotated_events.append(AnnotatedEvent(event=event, annotation=annotation))
        risk_progression.append(annotation.risk_score)
        if annotation.risk_score > max_risk:
            max_risk = annotation.risk_score

    return AnnotatedSession(
        session=session,
        events=annotated_events,
        max_risk_score=max_risk,
        risk_progression=risk_progression,
    )

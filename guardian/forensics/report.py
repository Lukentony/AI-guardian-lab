import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from .parser import ForensicsEvent, ForensicsSession
from .annotator import AnnotatedEvent, AnnotatedSession
from .analyzer import BehaviorReport, AnalysisFlag

@dataclass
class ForensicsReport:
    report_id: str            # uuid4
    generated_at: str         # ISO8601
    session_id: str
    framework: str
    initial_task: str | None
    event_count: int
    tool_call_count: int
    anomaly_score: int
    risk_progression: list[int]
    max_risk_score: int
    flags: dict               # {"escalation": AnalysisFlag, "intent_drift": AnalysisFlag, "injection_signals": AnalysisFlag}
    summary: str              # human-readable, 3-5 sentences
    timeline: list[dict]      # one entry per tool_call event only

    def to_dict(self) -> dict:
        """Returns a full JSON-serializable dict with nested AnalysisFlag objects."""
        return asdict(self)

    def to_text(self) -> str:
        """Returns a human-readable formatted text block."""
        def format_flag(name, flag):
            status = "TRIGGERED" if flag["triggered"] else "clear"
            conf = flag["confidence"]
            reason = flag["reason"]
            return f"{name}: {status} ({conf})\n  {reason}"

        timeline_str = ""
        for entry in self.timeline:
            seq = str(entry["seq"]).ljust(3)
            binary = (entry["binary"] or "none").ljust(10)
            zone = entry["policy_zone"].ljust(8)
            risk = f"risk {entry['risk_score']}"
            preview = entry["truncated_input"]
            timeline_str += f"  [{seq}] {binary} ({zone}/{risk}) {preview}\n"

        report_text = f"""══════════════════════════════════════
FORENSICS REPORT — {self.report_id}
Generated: {self.generated_at}
══════════════════════════════════════
Session:      {self.session_id}
Framework:    {self.framework}
Events:       {self.event_count} ({self.tool_call_count} tool calls)
Anomaly Score: {self.anomaly_score}/100
──────────────────────────────────────
{format_flag("ESCALATION", self.flags["escalation"])}
{format_flag("INTENT DRIFT", self.flags["intent_drift"])}
{format_flag("INJECTION", self.flags["injection_signals"])}
──────────────────────────────────────
TIMELINE ({self.tool_call_count} tool calls):
{timeline_str}══════════════════════════════════════
SUMMARY:
{self.summary}
"""
        return report_text

def generate_report(report: BehaviorReport, session: AnnotatedSession) -> ForensicsReport:
    """Generates a structured ForensicsReport from behavior analysis and session data."""
    report_id = str(uuid.uuid4())
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    tool_calls = [ae for ae in session.events if ae.event.type == "tool_call"]
    tool_call_count = len(tool_calls)
    
    # 1. Build timeline
    timeline = []
    for ae in tool_calls:
        # Extract preview from tool_input or content
        input_preview = ""
        if ae.event.tool_input:
            # Try to get the command-like string
            for key in ["command", "cmd", "bash", "shell"]:
                if key in ae.event.tool_input:
                    input_preview = str(ae.event.tool_input[key])
                    break
            if not input_preview:
                input_preview = str(ae.event.tool_input)
        elif ae.event.content:
            input_preview = ae.event.content
            
        timeline.append({
            "seq": ae.event.seq,
            "tool_name": ae.event.tool_name,
            "binary": ae.annotation.binary,
            "operation_type": ae.annotation.operation_type,
            "policy_zone": ae.annotation.policy_zone,
            "risk_score": ae.annotation.risk_score,
            "truncated_input": input_preview[:120]
        })
        
    # 2. Build flags dict
    flags = {
        "escalation": asdict(report.escalation),
        "intent_drift": asdict(report.intent_drift),
        "injection_signals": asdict(report.injection_signals)
    }
    
    # 3. Build summary
    summary_parts = [
        f"Session {session.session.session_id} ({session.session.framework}): "
        f"{tool_call_count} tool calls, anomaly score {report.anomaly_score}/100."
    ]
    
    if session.session.initial_task:
        task_trunc = session.session.initial_task[:80]
        if len(session.session.initial_task) > 80:
            task_trunc += "..."
        summary_parts.append(f"Initial task: {task_trunc}.")
        
    triggered_flag_found = False
    for flag_obj in [report.escalation, report.intent_drift, report.injection_signals]:
        if flag_obj.triggered and flag_obj.reason:
            summary_parts.append(flag_obj.reason.strip())
            if not summary_parts[-1].endswith("."):
                summary_parts[-1] += "."
            triggered_flag_found = True
            
    if not triggered_flag_found:
        summary_parts.append("No anomalies detected.")
        
    summary = " ".join(summary_parts)
    
    return ForensicsReport(
        report_id=report_id,
        generated_at=generated_at,
        session_id=session.session.session_id,
        framework=session.session.framework,
        initial_task=session.session.initial_task,
        event_count=len(session.events),
        tool_call_count=tool_call_count,
        anomaly_score=report.anomaly_score,
        risk_progression=session.risk_progression,
        max_risk_score=session.max_risk_score,
        flags=flags,
        summary=summary,
        timeline=timeline
    )

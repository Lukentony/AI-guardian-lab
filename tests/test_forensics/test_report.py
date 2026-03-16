import json
import pytest
from guardian.forensics.parser import ForensicsEvent, ForensicsSession
from guardian.forensics.annotator import AnnotatedEvent, AnnotatedSession, EventAnnotation
from guardian.forensics.analyzer import BehaviorReport, AnalysisFlag
from guardian.forensics.report import generate_report, ForensicsReport

def create_mock_behavior_data():
    # Helper to create objects for testing
    events = [
        ForensicsEvent(seq=0, timestamp=None, type="user_message", content="Find secrets"),
        ForensicsEvent(seq=1, timestamp=None, type="tool_call", content="", tool_name="bash", tool_input={"command": "ls /root"}),
        ForensicsEvent(seq=2, timestamp=None, type="tool_result", content="", tool_output="permission denied")
    ]
    
    ann_events = [
        AnnotatedEvent(events[0], EventAnnotation("none", "none", 0, None)),
        AnnotatedEvent(events[1], EventAnnotation("read", "red", 3, "ls")),
        AnnotatedEvent(events[2], EventAnnotation("none", "none", 0, None))
    ]
    
    session = ForensicsSession(
        session_id="session_123",
        framework="openhands",
        started_at="2026-03-16T10:00:00Z",
        initial_task="List sensitive files in the root directory and report back",
        events=events
    )
    
    ann_session = AnnotatedSession(
        session=session,
        events=ann_events,
        max_risk_score=3,
        risk_progression=[0, 3, 0]
    )
    
    report = BehaviorReport(
        session_id="session_123",
        anomaly_score=75,
        escalation=AnalysisFlag(True, "high", "Risk escalated from 1 to 3."),
        intent_drift=AnalysisFlag(True, "medium", "Agent diverged from task."),
        injection_signals=AnalysisFlag(False, "none", ""),
        summary="Initial summary"
    )
    
    return ann_session, report

def test_report_generation_and_serialization():
    ann_session, behavior_report = create_mock_behavior_data()
    report = generate_report(behavior_report, ann_session)
    
    # 1. Test basic fields
    assert report.session_id == "session_123"
    assert report.anomaly_score == 75
    assert report.tool_call_count == 1
    assert report.event_count == 3
    
    # 2. Test to_dict (nested)
    d = report.to_dict()
    assert isinstance(d, dict)
    assert d["flags"]["escalation"]["triggered"] is True
    assert d["flags"]["injection_signals"]["confidence"] == "none"
    assert len(d["timeline"]) == 1
    assert d["timeline"][0]["binary"] == "ls"
    
    # 3. Test to_text (human readable)
    txt = report.to_text()
    assert "FORENSICS REPORT" in txt
    assert "Session:      session_123" in txt
    assert "ESCALATION: TRIGGERED (high)" in txt
    assert "INJECTION: clear (none)" in txt
    assert "[1  ] ls" in txt
    assert "SUMMARY:" in txt

def test_summary_assembly_with_flags():
    ann_session, behavior_report = create_mock_behavior_data()
    # Task is > 80 chars
    long_task = "A" * 100
    ann_session.session.initial_task = long_task
    
    report = generate_report(behavior_report, ann_session)
    
    # Check truncation and flag integration
    assert "Initial task: " + "A" * 80 + "..." in report.summary
    assert "Risk escalated from 1 to 3." in report.summary
    assert "Agent diverged from task." in report.summary

def test_summary_assembly_no_flags():
    ann_session, behavior_report = create_mock_behavior_data()
    behavior_report.escalation.triggered = False
    behavior_report.intent_drift.triggered = False
    behavior_report.injection_signals.triggered = False
    
    report = generate_report(behavior_report, ann_session)
    assert "No anomalies detected." in report.summary

def test_timeline_filtering():
    # Ensure only tool_call events are in the timeline
    events = [
        ForensicsEvent(seq=0, timestamp=None, type="user_message", content="hi"),
        ForensicsEvent(seq=1, timestamp=None, type="tool_call", content="ls", tool_name="bash"),
        ForensicsEvent(seq=2, timestamp=None, type="tool_result", content="ok"),
        ForensicsEvent(seq=3, timestamp=None, type="tool_call", content="cat", tool_name="bash")
    ]
    ann_events = [AnnotatedEvent(e, EventAnnotation("none", "none", 0, None)) for e in events]
    # Set binaries for tool calls
    ann_events[1].annotation.binary = "ls"
    ann_events[3].annotation.binary = "cat"
    
    session = ForensicsSession("id", "framework", None, None, events)
    ann_session = AnnotatedSession(session, ann_events, 0, [0, 0, 0, 0])
    behavior_report = BehaviorReport("id", 0, AnalysisFlag(False, "none", ""), AnalysisFlag(False, "none", ""), AnalysisFlag(False, "none", ""), "")
    
    report = generate_report(behavior_report, ann_session)
    assert len(report.timeline) == 2
    assert report.timeline[0]["binary"] == "ls"
    assert report.timeline[1]["binary"] == "cat"

from unittest.mock import patch

import pytest

from guardian.forensics.analyzer import AnalysisFlag, BehaviorReport
from guardian.guardian.main import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_analyze_success(client):
    """Test successful analysis with mocked LLM pipeline."""
    mock_report = BehaviorReport(
        session_id="test-session",
        anomaly_score=10,
        escalation=AnalysisFlag(False, "none", "No escalation"),
        intent_drift=AnalysisFlag(False, "none", "No drift"),
        injection_signals=AnalysisFlag(False, "none", "No injection"),
        summary="Analysis completed successfully."
    )

    with patch('forensics_routes.check_auth', return_value=True):
        with patch('forensics_routes.analyze_session', return_value=mock_report):
            jsonl_content = (
                '{"role": "user", "content": "analyze disk usage"}\n'
                '{"role": "assistant", "tool_calls": [{"id": "1", "function": {"name": "bash", "arguments": "df -h"}}]}'
            )
            response = client.post('/forensics/analyze', json={
                "jsonl": jsonl_content,
                "session_id": "override-id"
            })

            assert response.status_code == 200
            data = response.get_json()
            assert data["session_id"] == "override-id"
            assert data["anomaly_score"] == 10
            assert data["summary"].startswith("Session override-id")
            assert "report_id" in data
            assert "timeline" in data
            assert len(data["timeline"]) == 1  # Only the tool_call
            assert data["analysis_complete"] is True

def test_analyze_reports_incomplete_when_reviewer_fails(client):
    jsonl_content = (
        '{"role": "user", "content": "analyze disk usage"}\n'
        '{"role": "assistant", "tool_calls": [{"id": "1", "function": {"name": "bash", "arguments": "df -h"}}]}'
    )

    with patch('forensics_routes.check_auth', return_value=True):
        response = client.post('/forensics/analyze', json={"jsonl": jsonl_content})

    assert response.status_code == 200
    data = response.get_json()
    assert data["analysis_complete"] is False
    assert data["flags"]["intent_drift"]["evaluated"] is False
    assert "incomplete" in data["summary"].lower()
    assert "No anomalies detected" not in data["summary"]

def test_analyze_missing_field(client):
    """Test 400 error when jsonl field is missing."""
    with patch('forensics_routes.check_auth', return_value=True):
        response = client.post('/forensics/analyze', json={"not_jsonl": "data"})
        assert response.status_code == 400
        assert "error" in response.get_json()
        assert "Missing 'jsonl'" in response.get_json()["error"]

def test_analyze_unauthorized(client):
    """Test 401 error when auth fails."""
    with patch('forensics_routes.check_auth', return_value=False):
        response = client.post('/forensics/analyze', json={"jsonl": "some content"})
        assert response.status_code == 401
        assert response.get_json()["error"] == "Unauthorized"

def test_analyze_pipeline_failure(client):
    """Test 400 error when the pipeline raises an exception."""
    with patch('forensics_routes.check_auth', return_value=True):
        with patch('forensics_routes.parse_session', side_effect=Exception("Parsing failed")):
            response = client.post('/forensics/analyze', json={"jsonl": "corrupt data"})
            assert response.status_code == 400
            assert response.get_json()["error"] == "Parsing failed"

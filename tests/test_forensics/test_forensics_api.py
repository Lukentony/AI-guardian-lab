import pytest
import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# 1. Setup paths relative to project root
root = Path(__file__).parent.parent.parent.resolve()
guardian_guardian_path = str(root / "guardian" / "guardian")
if guardian_guardian_path not in sys.path:
    sys.path.append(guardian_guardian_path)
if str(root) not in sys.path:
    sys.path.append(str(root))

# 2. Set environment variables BEFORE importing main.py to avoid Fail-Secure exit
os.environ['PATTERNS_PATH'] = str(root / "guardian" / "config" / "patterns.yaml")
os.environ['POLICY_PATH'] = str(root / "guardian" / "config" / "policy.yaml")
os.environ['DB_PATH'] = ":memory:"
os.environ['TESTING'] = "true"
os.environ['API_KEY'] = "test-key"

# 3. Mock litellm because it's incompatible with Python 3.14 (imghdr removal)
mock_litellm = MagicMock()
sys.modules['litellm'] = mock_litellm

# Now app should be importable successfully
from guardian.guardian.main import app
from guardian.forensics.analyzer import BehaviorReport, AnalysisFlag

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_analyze_success(client):
    """Test successful analysis with mocked LLM pipeline."""
    # Mock check_auth to always pass
    with patch('guardian.guardian.main.check_auth', return_value=True):
        # Mock analyze_session to return a fixed BehaviorReport (Phase 5.5 spec)
        mock_report = BehaviorReport(
            session_id="test-session",
            anomaly_score=10,
            escalation=AnalysisFlag(False, "none", "No escalation"),
            intent_drift=AnalysisFlag(False, "none", "No drift"),
            injection_signals=AnalysisFlag(False, "none", "No injection"),
            summary="Analysis completed successfully."
        )
        
        with patch('guardian.guardian.forensics_routes.analyze_session', return_value=mock_report):
            jsonl_content = '{"role": "user", "content": "analyze disk usage"}\n{"role": "assistant", "tool_calls": [{"id": "1", "function": {"name": "bash", "arguments": "df -h"}}]}'
            
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
            assert len(data["timeline"]) == 1 # Only the tool_call

def test_analyze_missing_field(client):
    """Test 400 error when jsonl field is missing."""
    with patch('guardian.guardian.main.check_auth', return_value=True):
        response = client.post('/forensics/analyze', json={"not_jsonl": "data"})
        assert response.status_code == 400
        assert "error" in response.get_json()
        assert "Missing 'jsonl'" in response.get_json()["error"]

def test_analyze_unauthorized(client):
    """Test 401 error when auth fails."""
    with patch('guardian.guardian.main.check_auth', return_value=False):
        response = client.post('/forensics/analyze', json={"jsonl": "some content"})
        assert response.status_code == 401
        assert response.get_json()["error"] == "Unauthorized"

def test_analyze_pipeline_failure(client):
    """Test 400 error when the pipeline raises an exception."""
    with patch('guardian.guardian.main.check_auth', return_value=True):
        with patch('guardian.guardian.forensics_routes.parse_session', side_effect=Exception("Parsing failed")):
            response = client.post('/forensics/analyze', json={"jsonl": "corrupt data"})
            assert response.status_code == 400
            assert response.get_json()["error"] == "Parsing failed"

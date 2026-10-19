"""Subprocess checks bypass conftest's historical import aliases entirely."""

import subprocess
import sys
from pathlib import Path


def test_real_package_startup_and_signed_validation(tmp_path):
    root = Path(__file__).resolve().parents[1]
    config = tmp_path / "observer.yaml"
    config.write_text(
        "mode: 'off'\nendpoint: http://127.0.0.1:8009/v1/systemone\nmodel: kev-0.8b-v1.0\ntimeout_seconds: 0.5\n"
    )
    environment = {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(root),
        "API_KEY": "subprocess-test-key",
        "LOG_HMAC_KEY": "subprocess-signing-key",
        "DB_PATH": str(tmp_path / "audit.db"),
        "SYSTEM_ONE_CONFIG": str(config),
        "LEARNED_PATH": str(tmp_path / "learned.yaml"),
        "UI_PASSWORD": "subprocess-ui-key",
    }
    code = """
from guardian.guardian.main import app
from database.audit_logger import verify_logs
from agent.agent.main import app as agent
from ui.app import app as ui
with app.test_client() as client:
    response = client.post('/validate', json={'command':'ls /tmp','task':'list files'}, headers={'X-API-Key':'subprocess-test-key'})
    assert response.status_code == 200 and response.json['approved'] is True
    assert response.json['system_one']['status'] == 'off'
assert verify_logs()['valid']
assert agent.test_client().get('/health').status_code == 200
assert ui.test_client().get('/health').status_code == 200
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr

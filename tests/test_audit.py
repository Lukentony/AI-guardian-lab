"""Check transactional appends, signed metadata and honest legacy-history migration."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from database import audit_logger as audit


def test_concurrent_chain_and_idempotent_schema(tmp_path):
    path = tmp_path / "audit.db"
    audit.init_db(path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(
            pool.map(
                lambda index: audit.log_command(
                    "list files", f"ls /tmp/{index}", "approved", path=path
                ),
                range(40),
            )
        )
    audit.init_db(path)
    assert audit.verify_logs(path) == {
        "valid": True,
        "signed_integrity_valid": True,
        "signed_rows": 40,
        "unsigned_legacy_rows": 0,
        "errors": [],
    }


@pytest.mark.parametrize(
    "field", ["command", "status", "llm_provider", "guardian_reason", "intent_source", "metadata"]
)
def test_all_decision_metadata_is_signed(tmp_path, field):
    path = tmp_path / "audit.db"
    audit.init_db(path)
    audit.log_command(
        "list files", "ls", "approved", metadata={"system_one": {"mode": "shadow"}}, path=path
    )
    connection = sqlite3.connect(path)
    try:
        # All identifiers are test-controlled members of this explicit allowlist.
        statements = {
            "command": "UPDATE command_log SET command='changed'",
            "status": "UPDATE command_log SET status='changed'",
            "llm_provider": "UPDATE command_log SET llm_provider='changed'",
            "guardian_reason": "UPDATE command_log SET guardian_reason='changed'",
            "intent_source": "UPDATE command_log SET intent_source='changed'",
            "metadata": "UPDATE command_log SET metadata='changed'",
        }
        connection.execute(statements[field])
        connection.commit()
    finally:
        connection.close()
    assert audit.verify_logs(path)["errors"]


def test_legacy_migration_never_claims_original_integrity(tmp_path):
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE command_log (id INTEGER PRIMARY KEY, timestamp TEXT, task TEXT, command TEXT, status TEXT, llm_provider TEXT, guardian_reason TEXT)"
    )
    connection.execute(
        "INSERT INTO command_log VALUES (1, 'old', 'old task', 'ls', 'executed', NULL, NULL)"
    )
    connection.commit()
    connection.close()
    audit.init_db(path)
    audit.log_command("list files", "ls", "approved", path=path)
    result = audit.verify_logs(path)
    assert not result["valid"] and result["signed_integrity_valid"]
    assert result["unsigned_legacy_rows"] == 1 and result["signed_rows"] == 1
    connection = sqlite3.connect(path)
    connection.execute("UPDATE command_log SET command='tampered' WHERE id=1")
    connection.commit()
    connection.close()
    assert audit.verify_logs(path)["errors"]


def test_redacts_reason_and_nested_metadata(tmp_path):
    path = tmp_path / "audit.db"
    audit.init_db(path)
    fake = "sk-" + "A" * 32
    audit.log_command(
        fake,
        "echo " + fake,
        "rejected",
        guardian_reason=fake,
        metadata={"details": [fake]},
        path=path,
    )
    connection = sqlite3.connect(path)
    row = connection.execute(
        "SELECT task,command,guardian_reason,metadata FROM command_log"
    ).fetchone()
    connection.close()
    assert fake not in str(row)
    assert audit.verify_logs(path)["valid"]


def test_no_development_signing_key_fallback(monkeypatch):
    monkeypatch.delenv("LOG_HMAC_KEY", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    with pytest.raises(ValueError):
        audit.signing_key()

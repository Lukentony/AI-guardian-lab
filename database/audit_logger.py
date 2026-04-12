import sqlite3
import re
import hashlib
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "audit.db"

# SEC-04: Mask secrets before writing to the database
def mask_secrets(text):
    """Strip API keys, tokens, and passwords from text before logging."""
    if not isinstance(text, str):
        return str(text)
    patterns = [
        (r'(?i)(api[_-]?key|token|auth|password|secret|credential|private[_-]?key)["\s:=]+([A-Za-z0-9_-]{12,})', r'\1=***MASKED***'),
        (r'(?i)(sk-[A-Za-z0-9]{20,})', r'sk-***MASKED***'),
        (r'(?i)(gsk_[A-Za-z0-9]{20,})', r'gsk_***MASKED***'),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text

def calculate_row_hash(prev_hash, timestamp, task, command, status):
    """Senior Feature: Forensic Chain Hashing to prevent log tampering."""
    data = f"{prev_hash}|{timestamp}|{task}|{command}|{status}"
    return hashlib.sha256(data.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    with open(Path(__file__).parent / "schema.sql") as f:
        conn.executescript(f.read())
    conn.close()

def log_command(task, command, status, llm_provider=None, guardian_reason=None):
    # SEC-04: Mask secrets before persisting
    safe_task = mask_secrets(task)
    safe_command = mask_secrets(command)
    timestamp = datetime.utcnow().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    
    # Get last row hash for the chain
    cursor = conn.execute("SELECT row_hash FROM command_log ORDER BY id DESC LIMIT 1")
    last_row = cursor.fetchone()
    prev_hash = last_row[0] if last_row else "GENESIS"
    
    row_hash = calculate_row_hash(prev_hash, timestamp, safe_task, safe_command, status)
    
    conn.execute(
        "INSERT INTO command_log (timestamp, task, command, status, llm_provider, guardian_reason, prev_hash, row_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (timestamp, safe_task, safe_command, status, llm_provider, guardian_reason, prev_hash, row_hash)
    )
    conn.commit()
    conn.close()

def get_recent_logs(limit=20):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT timestamp, task, command, status, llm_provider FROM command_log ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

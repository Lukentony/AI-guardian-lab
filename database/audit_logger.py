import sqlite3
import re
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "audit.db"

# SEC-04: Mask secrets before writing to the database
def mask_secrets(text):
    """Strip API keys, tokens, and passwords from text before logging."""
    patterns = [
        (r'(api[_-]?key["\s:=]+)([A-Za-z0-9_-]{20,})', r'\1***MASKED***'),
        (r'(token["\s:=]+)([A-Za-z0-9_-]{20,})', r'\1***MASKED***'),
        (r'(password["\s:=]+)([^\s"]+)', r'\1***MASKED***'),
        (r'(sk-[A-Za-z0-9]{20,})', r'sk-***MASKED***'),       # OpenAI style
        (r'(gsk_[A-Za-z0-9]{20,})', r'gsk_***MASKED***'),     # Groq style
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def init_db():
    conn = sqlite3.connect(DB_PATH)
    with open(Path(__file__).parent / "schema.sql") as f:
        conn.executescript(f.read())
    conn.close()

def log_command(task, command, status, llm_provider=None, guardian_reason=None):
    # SEC-04: Mask secrets before persisting
    safe_task = mask_secrets(task)
    safe_command = mask_secrets(command)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO command_log (timestamp, task, command, status, llm_provider, guardian_reason) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), safe_task, safe_command, status, llm_provider, guardian_reason)
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

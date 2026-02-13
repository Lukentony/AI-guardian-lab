import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "audit.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    with open(Path(__file__).parent / "schema.sql") as f:
        conn.executescript(f.read())
    conn.close()

def log_command(task, command, status, llm_provider=None, guardian_reason=None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO command_log (timestamp, task, command, status, llm_provider, guardian_reason) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), task, command, status, llm_provider, guardian_reason)
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

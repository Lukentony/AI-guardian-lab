from flask import Flask, render_template
import sqlite3
from pathlib import Path

app = Flask(__name__)
DB_PATH = "/app/database/audit.db"
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total = cursor.execute("SELECT COUNT(*) FROM command_log").fetchone()[0]
    executed = cursor.execute("SELECT COUNT(*) FROM command_log WHERE status='executed'").fetchone()[0]
    rejected = cursor.execute("SELECT COUNT(*) FROM command_log WHERE status='rejected'").fetchone()[0]
    
    conn.close()
    return {'total': total, 'executed': executed, 'rejected': rejected}

def get_recent_commands(limit=20):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    rows = cursor.execute(
        "SELECT timestamp, task, command, status, llm_provider, guardian_reason FROM command_log ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    ).fetchall()
    
    conn.close()
    return [dict(row) for row in rows]

@app.route('/')
def dashboard():
    stats = get_stats()
    commands = get_recent_commands(20)
    return render_template('dashboard.html', stats=stats, commands=commands)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

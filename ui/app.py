import os
import requests
import json
import sqlite3
from flask import Flask, render_template, request
from pathlib import Path

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "/app/database/audit.db")
GUARDIAN_API = os.environ.get("GUARDIAN_URL", "http://lab-guardian:5000")
GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY", "")

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

@app.route('/forensics', methods=['GET', 'POST'])
def forensics():
    report = None
    error = None
    if request.method == 'POST':
        jsonl_content = request.form.get('jsonl_content', '').strip()
        if not jsonl_content:
            error = "No JSONL content provided."
        else:
            try:
                resp = requests.post(
                    f"{GUARDIAN_API}/forensics/analyze",
                    json={"jsonl": jsonl_content},
                    headers={"X-API-Key": GUARDIAN_API_KEY},
                    timeout=60
                )
                if resp.status_code == 200:
                    report = resp.json()
                else:
                    try:
                        error = resp.json().get("error", "Unknown error from Guardian API")
                    except:
                        error = f"Guardian API returned status {resp.status_code}: {resp.text}"
            except Exception as e:
                error = f"Could not reach Guardian API: {e}"
    return render_template('forensics.html', report=report, error=error)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

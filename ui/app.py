import os
import requests
import json
import sqlite3
import logging
import re
from flask import Flask, render_template, request
from pathlib import Path

app = Flask(__name__)
# Enable debug logging
app.logger.setLevel(logging.DEBUG)

DB_PATH = os.environ.get("DB_PATH", "/app/database/audit.db")
GUARDIAN_API = os.environ.get("GUARDIAN_URL", "http://lab-guardian:5000")
GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY", "")

def normalize_to_jsonl(raw_content):
    """
    Intelligently cleans and converts mangled input into valid JSONL.
    Handles: glued objects }{, JSON arrays [{},{}], and trailing commas.
    """
    raw_content = raw_content.strip()
    if not raw_content:
        return ""

    # 1. Fix glued objects: }{ or } { -> }\n{
    normalized = re.sub(r'}\s*{', '}\n{', raw_content)

    # 2. Check if it's a JSON array [...]
    if normalized.startswith('[') and normalized.endswith(']'):
        try:
            parsed = json.loads(normalized)
            if isinstance(parsed, list):
                # Convert list of dicts to JSONL string
                return "\n".join(json.dumps(item) for item in parsed)
        except:
            pass # Not a standard array, continue with line-by-line cleanup

    # 3. Clean up line by line: remove trailing commas and extra whitespace
    lines = []
    for line in normalized.split('\n'):
        line = line.strip().rstrip(',')
        if line:
            lines.append(line)

    return "\n".join(lines)

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
        raw_content = request.form.get('jsonl_content', '').strip()
        
        # Apply intelligent normalization
        jsonl_content = normalize_to_jsonl(raw_content)
        
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
                
                app.logger.debug(f"Guardian response status: {resp.status_code}")
                if resp.status_code == 200:
                    try:
                        report = resp.json()
                    except Exception as e:
                        error = f"JSON parse error: {e} — raw: {resp.text[:200]}"
                else:
                    try:
                        error = resp.json().get("error", "Unknown error from Guardian API")
                    except:
                        error = f"Guardian API returned status {resp.status_code}: {resp.text[:200]}"
            except Exception as e:
                error = f"Could not reach Guardian API: {e}"
    return render_template('forensics.html', report=report, error=error)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

from flask import Flask, request, jsonify
import yaml
import re
import os
import base64
import time
import hmac
import sqlite3
from datetime import datetime

app = Flask(__name__)

API_KEY = os.getenv('API_KEY', '')
DB_PATH = "/app/database/audit.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    # Create table if not exists (schema adapted from database/schema.sql)
    conn.execute('''
    CREATE TABLE IF NOT EXISTS command_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        task TEXT NOT NULL,
        command TEXT NOT NULL,
        status TEXT NOT NULL,
        llm_provider TEXT,
        guardian_reason TEXT
    )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON command_log(timestamp)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON command_log(status)')
    conn.commit()
    conn.close()

# Initialize DB on startup
if not os.path.exists(os.path.dirname(DB_PATH)):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
init_db()

def mask_secrets(text):
    # Regex to mask common secrets (API keys, tokens, passwords)
    patterns = [
        (r'(api[_-]?key["\s:=]+)([A-Za-z0-9_-]{20,})', r'\1***MASKED***'),
        (r'(token["\s:=]+)([A-Za-z0-9_-]{20,})', r'\1***MASKED***'),
        (r'(password["\s:=]+)([^\s"]+)', r'\1***MASKED***'),
        (r'(sk-[A-Za-z0-9]{20,})', r'sk-***MASKED***'), # OpenAI style
        (r'(gsk_[A-Za-z0-9]{20,})', r'gsk_***MASKED***') # Groq style
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def log_to_db(task, command, status, reason, provider):
    try:
        # Mask secrets in command and task before logging
        safe_command = mask_secrets(command)
        safe_task = mask_secrets(task)
        
        # Add timeout to handle concurrent writes
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.execute(
            "INSERT INTO command_log (timestamp, task, command, status, llm_provider, guardian_reason) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), safe_task, safe_command, status, provider, reason)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging to DB: {e}")

# --- In-memory rate limiter (SEC-02) ---
GUARDIAN_RATE_LIMIT = 30  # requests per minute per IP
_rate_counts = {}

def is_rate_limited(ip):
    current_time = int(time.time())
    window = current_time // 60
    key = (ip, window)
    count = _rate_counts.get(key, 0)
    if count >= GUARDIAN_RATE_LIMIT:
        return True
    _rate_counts[key] = count + 1
    # Garbage-collect old windows
    if len(_rate_counts) > 500:
        for k in list(_rate_counts.keys()):
            if k[1] < window:
                del _rate_counts[k]
    return False

def check_auth():
    if not API_KEY:
        # FAIL CLOSED: reject all requests when no API_KEY is configured
        print("WARNING: API_KEY not set — rejecting request (fail-closed)")
        return False

    auth_header = request.headers.get('X-API-Key', '')
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(auth_header, API_KEY)

def normalize_command(command):
    normalized = command
    # Strip escape characters
    normalized = re.sub(r'\\(.)', r'\1', normalized)
    # Normalize IFS variants
    normalized = re.sub(r'\$\{IFS\}', ' ', normalized)
    normalized = re.sub(r"\$'\\t'", ' ', normalized)
    normalized = re.sub(r"\$'\\n'", ' ', normalized)
    # Collapse whitespace
    normalized = re.sub(r'\s+', ' ', normalized)

    # Decode base64 payloads: echo <b64> | base64 -d
    b64_pattern = r'echo\s+([A-Za-z0-9+/=]+)\s*\|\s*base64\s+-d'
    match = re.search(b64_pattern, normalized)
    if match:
        try:
            decoded = base64.b64decode(match.group(1)).decode('utf-8')
            normalized = normalized.replace(match.group(0), decoded)
        except Exception:
            pass

    # Decode hex payloads: echo <hex> | xxd -r -p  (SEC-03)
    hex_pattern = r'echo\s+([0-9a-fA-F]+)\s*\|\s*xxd\s+-r\s+-p'
    match = re.search(hex_pattern, normalized)
    if match:
        try:
            decoded = bytes.fromhex(match.group(1)).decode('utf-8')
            normalized = normalized.replace(match.group(0), decoded)
        except Exception:
            pass

    # Expand $(...) subshells into visible markers so patterns can match inner content
    # We don't execute them, but we strip the wrapper so the inner command is visible
    normalized = re.sub(r'\$\((.+?)\)', r'\1', normalized)
    # Same for backtick subshells
    normalized = re.sub(r'`(.+?)`', r'\1', normalized)

    return normalized.strip()

patterns = []
try:
    with open('/app/config/patterns.yaml', 'r') as f:
        config = yaml.safe_load(f)
        pattern_dict = config.get('patterns', {})
        for category, pattern_list in pattern_dict.items():
            if isinstance(pattern_list, list):
                for p in pattern_list:
                    if isinstance(p, dict) and 'pattern' in p:
                        patterns.append(re.compile(p['pattern']))
except Exception as e:
    print(f"Error loading patterns: {e}")

learned_path = '/app/config/learned_patterns.yaml'
if os.path.exists(learned_path):
    try:
        with open(learned_path, 'r') as f:
            learned = yaml.safe_load(f)
            if learned and 'learned_patterns' in learned:
                for p in learned['learned_patterns']:
                    if isinstance(p, dict) and 'pattern' in p:
                        patterns.append(re.compile(p['pattern']))
    except:
        pass

def validate_command(command):
    normalized = normalize_command(command)
    for pattern in patterns:
        if pattern.search(normalized):
            return False, f"Blocked by pattern: {pattern.pattern}"
    return True, ""

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "patterns_loaded": len(patterns)}), 200

@app.route('/validate', methods=['POST'])
def validate():
    # SEC-02: Rate limiting
    client_ip = request.remote_addr
    if is_rate_limited(client_ip):
        return jsonify({"error": "Too Many Requests", "retry_after": 60}), 429

    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    command = data.get('command', '')
    task = data.get('task', 'Unknown Task')
    provider = data.get('llm_provider', 'unknown')
    
    approved, reason = validate_command(command)
    
    # Log the result
    status = 'executed' if approved else 'rejected'
    log_to_db(task, command, status, reason, provider)
    
    return jsonify({"approved": approved, "reason": reason}), 200

@app.route('/report', methods=['POST'])
def report():
    # SEC-02: Rate limiting
    client_ip = request.remote_addr
    if is_rate_limited(client_ip):
        return jsonify({"error": "Too Many Requests", "retry_after": 60}), 429

    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    return jsonify({"status": "logged"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

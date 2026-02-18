from flask import Flask, request, jsonify
import yaml
import re
import os
import base64
import time
import hmac
import sqlite3
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("guardian")

app = Flask(__name__)

# SEC-02 (Refined): Use Flask-Limiter for standard rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day"],
    storage_uri="memory://",
)


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
        logger.error(f"Error logging to DB: {e}")

# --- ReDoS-safe regex compilation and execution (SEC-04b / Phase 2) ---
MAX_COMMAND_LENGTH = 4096
MAX_PATTERN_LENGTH = 200
REGEX_TIMEOUT = 1.0  # seconds

executor = ThreadPoolExecutor(max_workers=4)

def regex_match_with_timeout(pattern, text):
    """Run regex search with a timeout to prevent DoS."""
    try:
        future = executor.submit(pattern.search, text)
        return future.result(timeout=REGEX_TIMEOUT)
    except TimeoutError:
        logger.warning(f"Regex timeout after {REGEX_TIMEOUT}s on pattern: {pattern.pattern}")
        return None
    except Exception as e:
        logger.error(f"Regex error: {e}")
        return None

def check_auth():
    if not API_KEY:
        # FAIL CLOSED: reject all requests when no API_KEY is configured
        logger.critical("CRITICAL: API_KEY not set — rejecting request (fail-closed)")
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

def safe_compile(pattern_str, source="static"):
    """Compile a regex pattern with ReDoS safety checks."""
    if len(pattern_str) > MAX_PATTERN_LENGTH:
        logger.warning(f"Pattern too long ({len(pattern_str)} chars), skipping [{source}]: {pattern_str[:50]}...")
        return None
    # Block greedy .* which causes catastrophic backtracking
    if '.*' in pattern_str:
        # Replace .* with non-greedy .*?
        safe_str = pattern_str.replace('.*', '.*?')
        logger.info(f"Replaced greedy .* with .*? in pattern [{source}]: {pattern_str}")
        pattern_str = safe_str
    try:
        return re.compile(pattern_str)
    except re.error as e:
        logger.warning(f"Invalid regex [{source}]: {pattern_str} — {e}")
        return None

# --- FAIL-SECURE pattern loading (SEC-03b / Phase 2) ---
# Store patterns as (compiled_regex, category_name) to harden audit logs (SEC-05b)
patterns = []
try:
    with open('/app/config/patterns.yaml', 'r') as f:
        config = yaml.safe_load(f)
        if not config or 'patterns' not in config:
            raise ValueError("patterns.yaml is empty or missing 'patterns' key")
        pattern_dict = config.get('patterns', {})
        for category, pattern_list in pattern_dict.items():
            if isinstance(pattern_list, list):
                for p in pattern_list:
                    if isinstance(p, dict) and 'pattern' in p:
                        compiled = safe_compile(p['pattern'], source=category)
                        if compiled:
                            patterns.append((compiled, category))
except Exception as e:
    logger.critical(f"CRITICAL: Failed to load patterns: {e}")
    # Fail-secure: stop the application if static patterns cannot be loaded
    raise RuntimeError(f"Guardian cannot start without patterns: {e}")

if not patterns:
    logger.critical("CRITICAL: Guardian loaded 0 patterns — refusing to start (fail-secure)")
    raise RuntimeError("Guardian loaded 0 patterns")

logger.info(f"Guardian initialized with {len(patterns)} patterns")

# --- Learned patterns with validation (SEC-05b) ---
learned_path = '/app/config/learned_patterns.yaml'
if os.path.exists(learned_path):
    try:
        with open(learned_path, 'r') as f:
            learned = yaml.safe_load(f)
            if learned and 'learned_patterns' in learned:
                loaded_count = 0
                for p in learned['learned_patterns']:
                    if isinstance(p, dict) and 'pattern' in p:
                        compiled = safe_compile(p['pattern'], source="learned")
                        if compiled:
                            patterns.append((compiled, "learned_pattern"))
                            loaded_count += 1
                logger.info(f"Loaded {loaded_count} learned patterns")
    except Exception as e:
        logger.warning(f"Failed to load learned patterns (non-fatal): {e}")



def validate_command(command):
    # SEC-04b (Phase 2): Reject excessively long commands
    if len(command) > MAX_COMMAND_LENGTH:
        return False, f"Command rejected: exceeds max length ({MAX_COMMAND_LENGTH} chars)"
    
    normalized = normalize_command(command)
    
    # Phase 2: Iterate over patterns and use a timeout-safe match
    for pattern, category in patterns:
        if regex_match_with_timeout(pattern, normalized):
            # Hardened Audit: Return category instead of raw regex string (SEC-05b)
            return False, f"Blocked by pattern category: {category}"
            
    return True, ""

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "patterns_loaded": len(patterns)}), 200

@app.route('/validate', methods=['POST'])
@limiter.limit("60 per minute")
def validate():
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
@limiter.limit("60 per minute")
def report():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    return jsonify({"status": "logged"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

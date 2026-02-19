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
DB_PATH = os.getenv('DB_PATH', "/app/database/audit.db")
PATTERNS_PATH = os.getenv('PATTERNS_PATH', '/app/config/patterns.yaml')
POLICY_PATH = os.getenv('POLICY_PATH', '/app/config/policy.yaml')
LEARNED_PATH = os.getenv('LEARNED_PATH', '/app/config/learned_patterns.yaml')
MAX_COMMAND_LENGTH = 1024 # SEC-04b

def init_db():
    conn = sqlite3.connect(DB_PATH)
    # Enable WAL mode for better concurrency (Phase 1 fix)
    conn.execute('PRAGMA journal_mode=WAL')
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
    logger.info("Database initialized with WAL mode enabled")

# Initialize DB on startup
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)
init_db()

def mask_secrets(text):
    # Phase 2: Refined secret masking
    secret_patterns = [
        (r'(?i)(api[_-]?key|token|auth|password|secret|credential|private[_-]?key)["\s:=]+([A-Za-z0-9_-]{12,})', r'\1=***MASKED***'),
        (r'(?i)(sk-[A-Za-z0-9]{20,})', r'sk-***MASKED***'),
        (r'(?i)(gsk_[A-Za-z0-9]{20,})', r'gsk_***MASKED***'),
        (r'(?i)(AIza[0-9A-Za-z-_]{35})', r'AIza***MASKED***'), # Google API Key
        (r'(?i)(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*', r'\1***MASKED***')
    ]
    for pattern, replacement in secret_patterns:
        text = re.sub(pattern, replacement, text)
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
    
    # 1. Normalize IFS variants (must come before general escape stripping)
    normalized = re.sub(r'\$\{IFS\}', ' ', normalized)
    normalized = re.sub(r"\$'\\[tn]'", ' ', normalized)
    
    # 2. Decode hex payloads: echo <hex> | xxd -r -p
    hex_pattern = r'echo\s+([0-9a-fA-F]+)\s*\|\s*xxd\s+-r\s+-p'
    match_hex = re.search(hex_pattern, normalized)
    if match_hex:
        try:
            decoded = bytes.fromhex(match_hex.group(1)).decode('utf-8', errors='ignore')
            normalized = normalized.replace(match_hex.group(0), decoded)
        except Exception:
            pass

    # 3. Decode base64 payloads: echo <b64> | base64 -d
    b64_pattern = r'echo\s+([A-Za-z0-9+/=]+)\s*\|\s*base64\s+-d'
    match_b64 = re.search(b64_pattern, normalized)
    if match_b64:
        try:
            decoded = base64.b64decode(match_b64.group(1)).decode('utf-8', errors='ignore')
            normalized = normalized.replace(match_b64.group(0), decoded)
        except Exception:
            pass

    # 4. Strip shell wrappers $() and ``
    normalized = re.sub(r'\$\((.*?)\)', r'\1', normalized)
    normalized = re.sub(r'`(.*?)`', r'\1', normalized)

    # 5. Bash/Shell obfuscation: $'' or "" wrapping tokens
    # e.g., c''a""t -> cat
    normalized = re.sub(r"['\"]", '', normalized)

    # 6. Strip escape characters (e.g., \l\s -> ls)
    normalized = re.sub(r'\\(.)', r'\1', normalized)
    
    # 7. Collapse whitespace
    normalized = re.sub(r'\s+', ' ', normalized)

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
        # Phase 1: Enable case-insensitivity to prevent 'SUDO' bypasses
        return re.compile(pattern_str, re.IGNORECASE)
    except re.error as e:
        logger.warning(f"Invalid regex [{source}]: {pattern_str} — {e}")
        return None

# --- FAIL-SECURE configuration loading (SEC-03b / Phase 1 & 2) ---
policy = {}
try:
    if os.path.exists(POLICY_PATH):
        with open(POLICY_PATH, 'r') as f:
            policy = yaml.safe_load(f)
            logger.info(f"Policy loaded from {POLICY_PATH} (Mode: {policy.get('mode', 'unknown')})")
except Exception as e:
    logger.warning(f"Failed to load policy.yaml (non-fatal for Phase 1): {e}")

# Store patterns as (compiled_regex, category_name) to harden audit logs (SEC-05b)
patterns = []
try:
    if os.path.exists(PATTERNS_PATH):
        with open(PATTERNS_PATH, 'r') as f:
            config = yaml.safe_load(f)
            if not config or 'patterns' not in config:
                raise ValueError("patterns.yaml is empty or missing 'patterns' key")
            pattern_dict = config.get('patterns', {})
            for category, pattern_list in pattern_dict.items():
                if isinstance(pattern_list, list):
                    for p in pattern_list:
                        if isinstance(p, dict) and 'pattern' in p:
                            is_structural = category in ['subshell_execution', 'encoding_bypass']
                            compiled = safe_compile(p['pattern'], source=category)
                            if compiled:
                                patterns.append((compiled, category, is_structural))
except Exception as e:
    logger.critical(f"CRITICAL: Failed to load patterns from {PATTERNS_PATH}: {e}")
    # Fail-secure: stop the application if static patterns cannot be loaded
    if not os.getenv('TESTING'):
        raise RuntimeError(f"Guardian cannot start without patterns: {e}")

if not patterns:
    logger.critical("CRITICAL: Guardian loaded 0 patterns — refusing to start (fail-secure)")
    raise RuntimeError("Guardian loaded 0 patterns")

logger.info(f"Guardian initialized with {len(patterns)} patterns")

# --- Learned patterns with validation (SEC-05b) ---
if os.path.exists(LEARNED_PATH):
    try:
        with open(LEARNED_PATH, 'r') as f:
            learned = yaml.safe_load(f)
            if learned and 'learned_patterns' in learned:
                loaded_count = 0
                for p in learned['learned_patterns']:
                    if isinstance(p, dict) and 'pattern' in p:
                        compiled = safe_compile(p['pattern'], source="learned")
                        if compiled:
                            patterns.append((compiled, "learned_pattern", False))
                            loaded_count += 1
                logger.info(f"Loaded {loaded_count} learned patterns")
    except Exception as e:
        logger.warning(f"Failed to load learned patterns (non-fatal): {e}")



def validate_command(command):
    # SEC-04b (Phase 2): Reject excessively long commands
    if len(command) > MAX_COMMAND_LENGTH:
        logger.warning(f"Command rejected: too long ({len(command)} chars)")
        return False, f"Blocked: Command exceeds max length ({MAX_COMMAND_LENGTH} chars)"
    
    normalized = normalize_command(command)
    
    # Phase 3 Enforcement: Strict Binary Allowlisting (SEC-03b)
    # Extract the primary binary (first word of normalized command)
    binary = normalized.split(' ')[0] if normalized else ''
    
    # 1. Get binary status from policy
    zones = policy.get('zones', {})
    green_binaries = zones.get('green', {}).get('binaries', [])
    yellow_binaries = zones.get('yellow', {}).get('binaries', [])
    red_binaries = zones.get('red', {}).get('binaries', [])
    
    # Logic:
    # - If binary in green: Approved (unless regex blocks it)
    # - If binary in yellow: Approved but logged (logged anyway by audit)
    # - If binary in red: BLOCKED immediately
    # - If binary NOT in any zone: BLOCKED (Fail-Closed) if mode is 'enforced'
    
    if binary in red_binaries:
        return False, f"Blocked: Binary '{binary}' is in the RED zone (forbidden)"

    # Mode check
    strict_mode = policy.get('mode', 'permissive') == 'enforced'
    
    is_safe = (binary in green_binaries) or (binary in yellow_binaries)
    
    if strict_mode and not is_safe:
        return False, f"Blocked: Binary '{binary}' is not in the allowlist (Fail-Closed)"

    # Phase 1 Remediation: Dual-Path Validation
    # We check both the raw command and the normalized version to prevent bypasses
    # that might occur if normalization strips malicious tokens (like $(...) wrappers).
    # Dual-Path Validation with Structural Awareness
    # Patterns like subshell detection must check the RAW command before normalization
    # potentially strips the wrappers.
    for pattern, category, is_structural in patterns:
        clean_category = category.replace('_', ' ').title()
        
        # 1. Always check the RAW command
        if regex_match_with_timeout(pattern, command):
            return False, f"Blocked (Security Policy) - Category: {clean_category}"
        
        # 2. Check NORMALIZED command only for non-structural patterns
        # (Normalization intentionally strips structural shells, so checking them 
        # against normalized text is redundant or 'dead code').
        if not is_structural:
            if regex_match_with_timeout(pattern, normalized):
                return False, f"Blocked (Heuristic) - Category: {clean_category}"
            
    return True, "Approved"

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "patterns_loaded": len(patterns)}), 200

@app.route('/validate', methods=['POST'])
@limiter.limit("60 per minute")
def validate():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    # Robust JSON validation (Phase 1 fix)
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON or missing Content-Type"}), 400
        
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
    
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400

    # Phase 1 Fix: Actually log the report to DB
    task = data.get('task', 'Reported Task')
    command = data.get('command', 'N/A')
    status = data.get('status', 'reported')
    reason = data.get('reason', 'External Report')
    provider = data.get('llm_provider', 'unknown')
    
    log_to_db(task, command, status, reason, provider)
    
    return jsonify({"status": "logged"}), 200

@app.route('/learn', methods=['POST'])
@limiter.limit("10 per minute")
def learn():
    """Authenticated endpoint to add new patterns to learned_patterns.yaml."""
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json(silent=True)
    if not data or 'pattern' not in data:
        return jsonify({"error": "Missing 'pattern' in request body"}), 400
        
    new_pattern_str = data['pattern']
    description = data.get('description', 'Dynamically learned pattern')
    
    # 1. Validate the regex
    compiled = safe_compile(new_pattern_str, source="dynamic_learn")
    if not compiled:
        return jsonify({"error": "Invalid or unsafe regex pattern"}), 400
        
    # 2. Add to in-memory patterns
    patterns.append((compiled, "learned_pattern"))
    
    # 3. Persist to file
    try:
        learned_data = {'learned_patterns': []}
        if os.path.exists(LEARNED_PATH):
            with open(LEARNED_PATH, 'r') as f:
                learned_data = yaml.safe_load(f) or {'learned_patterns': []}
        
        learned_data['learned_patterns'].append({
            'pattern': new_pattern_str,
            'description': description,
            'added_at': datetime.utcnow().isoformat()
        })
        
        with open(LEARNED_PATH, 'w') as f:
            yaml.dump(learned_data, f)
            
        logger.info(f"Successfully learned and persisted new pattern: {new_pattern_str}")
        return jsonify({"status": "learned", "pattern": new_pattern_str}), 201
        
    except Exception as e:
        logger.error(f"Failed to persist learned pattern: {e}")
        return jsonify({"error": "Pattern learned in memory but persistence failed"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

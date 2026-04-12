import sqlite3
import hmac
import hashlib
import os
import sys
from pathlib import Path

# Load keys from environment or .env if present
API_KEY = os.environ.get("API_KEY", "")
LOG_HMAC_KEY = os.environ.get("LOG_HMAC_KEY") or API_KEY
DB_PATH = Path(__file__).parent / "database" / "audit.db"

def calculate_row_hash(prev_hash, timestamp, task, command, status, simulated, key):
    payload = f"{prev_hash}|{timestamp}|{task}|{command}|{status}|{simulated}".encode('utf-8')
    return hmac.new(key.encode('utf-8'), payload, hashlib.sha256).hexdigest()

def verify_logs():
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return False

    if not LOG_HMAC_KEY:
        print("Error: LOG_HMAC_KEY or API_KEY not set. Cannot verify signatures.")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT id, timestamp, task, command, status, prev_hash, row_hash, simulated FROM command_log ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No logs to verify.")
        return True

    print(f"--- Verification Started: {len(rows)} entries ---")
    current_prev_hash = "GENESIS"
    errors = 0

    for row in rows:
        db_id, ts, task, cmd, status, db_prev_hash, db_row_hash, simulated = row
        
        # Verify Chain
        if db_prev_hash != current_prev_hash:
            print(f"[!] BREAK IN CHAIN at ID {db_id}: Expected prev_hash {current_prev_hash}, found {db_prev_hash}")
            errors += 1
            
        # Verify Signature
        calc_hash = calculate_row_hash(db_prev_hash, ts, task, cmd, status, simulated, LOG_HMAC_KEY)
        if calc_hash != db_row_hash:
            print(f"[!] INVALID SIGNATURE at ID {db_id}: Recomputed hash does not match stored hash.")
            errors += 1
            
        current_prev_hash = db_row_hash

    if errors == 0:
        print("--- Verification Result: SUCCESS (Integrity Verified) ---")
        return True
    else:
        print(f"--- Verification Result: FAILED ({errors} errors found) ---")
        return False

if __name__ == "__main__":
    verify_logs()

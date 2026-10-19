"""Generate review candidates only; observed frequency is not safety confidence."""

import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database.audit_logger import connect, database_path
from guardian.guardian.configuration import update_learned

DB_PATH = database_path()
CONFIG_PATH = Path(
    os.getenv(
        "LEARNED_PATH",
        str(Path(__file__).resolve().parents[1] / "guardian/learned/learned_patterns.yaml"),
    )
)


def analyze_blocked_commands():
    connection = connect(DB_PATH)
    try:
        blocked = connection.execute(
            "SELECT command FROM command_log WHERE status='rejected' ORDER BY id DESC LIMIT 100"
        ).fetchall()
    finally:
        connection.close()
    if len(blocked) < 5:
        return []
    # Count per-command occurrence, not repeated tokens inside one command.
    common = Counter(
        token for row in blocked for token in set(re.findall(r"\b\w+\b", row["command"]))
    )
    return [
        {
            "token": token,
            "occurrences": count,
            "frequency_percent": round(count / len(blocked) * 100, 2),
            "pattern": rf"\b{re.escape(token)}\b",
            "status": "pending_review",
        }
        for token, count in common.most_common(10)
        if count / len(blocked) >= 0.3
    ]


def save_suggestions(suggestions):
    update_learned(CONFIG_PATH, suggestions=suggestions)


if __name__ == "__main__":
    try:
        candidates = analyze_blocked_commands()
        save_suggestions(candidates)
        print(f"Saved {len(candidates)} pending candidates. No pattern was auto-approved.")
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Pattern analysis failed: {type(exc).__name__}") from exc

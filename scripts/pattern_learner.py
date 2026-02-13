import sqlite3
import re
import yaml
from collections import Counter
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "database" / "audit.db"
CONFIG_PATH = Path(__file__).parent.parent / "guardian" / "config" / "learned_patterns.yaml"

def analyze_blocked_commands():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT command, guardian_reason FROM command_log WHERE status='rejected' ORDER BY timestamp DESC LIMIT 100"
    )
    blocked = cursor.fetchall()
    conn.close()

    if len(blocked) < 5:
        print(f"Insufficient data: {len(blocked)} blocked commands (need at least 5)")
        return []

    patterns = []
    for cmd, reason in blocked:
        cmd = cmd.strip().replace('```bash', '').replace('```', '').strip()
        tokens = re.findall(r'\b\w+\b', cmd)
        patterns.extend(tokens)

    common = Counter(patterns).most_common(10)

    suggestions = []
    for token, count in common:
        confidence = (count / len(blocked)) * 100
        if confidence >= 30:
            suggestions.append({
                "token": token,
                "occurrences": count,
                "confidence": round(confidence, 2),
                "pattern": f"\\b{token}\\b",
                "status": "pending_review"
            })

    return suggestions

def save_suggestions(suggestions):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    approved_patterns = [
        {
            'pattern': s['pattern'],
            'confidence': s['confidence'],
            'token': s['token']
        }
        for s in suggestions if s['confidence'] >= 30.0
    ]

    config = {
        "learned_patterns": {
            "enabled": len(approved_patterns) > 0,
            "patterns": approved_patterns
        },
        "suggestions": suggestions
    }

    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    print(f"\nSuggestions saved to: {CONFIG_PATH}")
    print(f"Auto-approved {len(approved_patterns)} patterns (confidence >= 30%)")

if __name__ == "__main__":
    print("=== AI Guardian Pattern Learning ===\n")
    suggestions = analyze_blocked_commands()

    if suggestions:
        print(f"Found {len(suggestions)} pattern suggestions:\n")
        for s in suggestions:
            print(f"Token: {s['token']}")
            print(f"  Occurrences: {s['occurrences']}")
            print(f"  Confidence: {s['confidence']}%")
            print(f"  Pattern: {s['pattern']}\n")

        save_suggestions(suggestions)
    else:
        print("No patterns discovered yet.")

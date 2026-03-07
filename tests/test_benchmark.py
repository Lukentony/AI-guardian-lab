import json
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# Python 3.14 workaround: imghdr was removed but litellm (dependency of main) imports it
sys.modules['imghdr'] = MagicMock()
# Mock litellm entirely to avoid complex dependency chain in tests
sys.modules['litellm'] = MagicMock()

# Add project root to path (works for local and container)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../guardian/guardian')))

try:
    from main import validate_command
except ImportError:
    # If in container, it might just be 'import main'
    import main
    validate_command = main.validate_command

DATA_DIR = Path(__file__).parent / "data"

def load_dataset(filename):
    with open(DATA_DIR / filename) as f:
        return json.load(f)

def run_validation(command, task=""):
    # main.validate_command returns (bool: approved, str: reason, str: source)
    approved, reason, source = validate_command(command, task=task)
    return "approved" if approved else "denied"

class TestBenchmark:
    def test_safe_commands(self):
        dataset = load_dataset("commands_safe.json")
        results = {"tp": 0, "fp": 0}
        for entry in dataset:
            actual = run_validation(entry["command"], entry.get("task", ""))
            if actual == "approved":
                results["tp"] += 1
            else:
                results["fp"] += 1
                # print needs -s flag in pytest to show
                print(f"FALSE POSITIVE: {entry['command']} — {entry['note']}")
        print(f"\nSafe commands: {results['tp']}/{len(dataset)} approved")
        assert results["fp"] == 0, f"{results['fp']} false positives found"

    def test_dangerous_commands(self):
        dataset = load_dataset("commands_dangerous.json")
        results = {"tn": 0, "fn": 0}
        for entry in dataset:
            actual = run_validation(entry["command"], entry.get("task", ""))
            if actual == "denied":
                results["tn"] += 1
            else:
                results["fn"] += 1
                print(f"FALSE NEGATIVE: {entry['command']} — {entry['note']}")
        print(f"\nDangerous commands: {results['tn']}/{len(dataset)} blocked")
        assert results["fn"] == 0, f"{results['fn']} false negatives found"

    def test_intent_coherence(self):
        dataset = load_dataset("commands_intent.json")
        correct = 0
        for entry in dataset:
            actual = run_validation(entry["command"], entry.get("task", ""))
            if actual == entry["expected"]:
                correct += 1
            else:
                print(f"INTENT MISMATCH: cmd='{entry['command']}' task='{entry.get('task')}' expected={entry['expected']} got={actual} — {entry['note']}")
        print(f"\nIntent coherence: {correct}/{len(dataset)} correct")
        assert correct == len(dataset)

    def test_full_report(self):
        safe = load_dataset("commands_safe.json")
        dangerous = load_dataset("commands_dangerous.json")
        tp = sum(1 for e in safe if run_validation(e["command"], e.get("task", "")) == "approved")
        tn = sum(1 for e in dangerous if run_validation(e["command"], e.get("task", "")) == "denied")
        fp = len(safe) - tp
        fn = len(dangerous) - tn
        total = len(safe) + len(dangerous)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        print(f"""
========================================
BENCHMARK REPORT — AI Guardian Lab
========================================
Safe commands:      {tp}/{len(safe)} approved (FP: {fp})
Dangerous commands: {tn}/{len(dangerous)} blocked (FN: {fn})
Total:              {total} commands tested
Precision:          {precision:.2%}
Recall:             {recall:.2%}
========================================
        """)

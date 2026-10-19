"""Verify the shared audit format. Exit 0 only for fully signed valid history."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database.audit_logger import database_path, verify_logs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=database_path())
    args = parser.parse_args()
    if not Path(args.db).is_file():
        print("Audit database does not exist", file=sys.stderr)
        return 1
    try:
        report = verify_logs(args.db)
    except Exception as exc:
        print(f"Verification unavailable: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    if report["errors"]:
        return 1
    return 2 if report["unsigned_legacy_rows"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

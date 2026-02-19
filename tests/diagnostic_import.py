import sys
import os
import traceback

print("--- DIAGNOSTIC IMPORT START ---")
print(f"CWD: {os.getcwd()}")
print(f"PYTHONPATH: {sys.path}")

os.environ['TESTING'] = '1'
os.environ['DB_PATH'] = 'audit_test.db'

try:
    print("Attempting to import clean_command from agent...")
    sys.path.append(os.path.abspath('.'))
    from agent.agent.main import clean_command
    print("Agent import SUCCESS")
except Exception:
    print("Agent import FAILURE")
    traceback.print_exc()

try:
    print("\nAttempting to import normalize_command from guardian...")
    from guardian.guardian.main import normalize_command
    print("Guardian import SUCCESS")
except Exception:
    print("Guardian import FAILURE")
    traceback.print_exc()

print("--- DIAGNOSTIC IMPORT END ---")

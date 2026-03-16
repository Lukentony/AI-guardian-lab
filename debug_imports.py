import sys
import os
from pathlib import Path

# Setup paths relative to project root
root = Path(__file__).parent.resolve()
sys.path.append(str(root))
guardian_guardian = root / "guardian" / "guardian"
sys.path.append(str(guardian_guardian))

print(f"PYTHONPATH: {sys.path}")
print(f"CWD: {os.getcwd()}")

try:
    print("Attempting to import intent...")
    import intent
    print("Success!")
    
    print("Attempting to import guardian.guardian.main...")
    # We might need to handle the fact that guardian is both a folder and a package
    from guardian.guardian.main import app
    print("Success!")
    
    print("Attempting to import forensics_routes...")
    from guardian.guardian.forensics_routes import forensics_bp
    print("Success!")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

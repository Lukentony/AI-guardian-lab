import sys
import os
import pytest
import re
from unittest.mock import MagicMock, patch

# Absolute project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

# Setup environment for main.py import
os.environ['TESTING'] = '1'
os.environ['DB_PATH'] = os.path.join(PROJECT_ROOT, 'tests/data/test.db')
os.environ['PATTERNS_PATH'] = os.path.join(PROJECT_ROOT, 'tests/data/patterns.yaml')
os.environ['POLICY_PATH'] = os.path.join(PROJECT_ROOT, 'tests/data/policy.yaml')

# Mocking modules that fail on module load due to Python 3.14 or missing env
sys.modules['imghdr'] = MagicMock()
sys.modules['litellm'] = MagicMock()

# Import the functions directly
# Now that we have dummy files, the import should succeed without mocking 'open'
from guardian.guardian.main import normalize_command, validate_command

def test_normalize_command_ifs():
    assert normalize_command("ls${IFS}-la") == "ls -la"
    assert normalize_command("ls$'\\t'-la") == "ls -la"

def test_normalize_command_encoding():
    # Hex for 'id' is '6964'
    assert normalize_command("echo 6964 | xxd -r -p") == "id"

def test_normalize_command_subshells():
    # It should strip the wrappers
    assert normalize_command("$(whoami)") == "whoami"
    assert normalize_command("`id`") == "id"

def test_dual_path_validation():
    # Mock patterns for testing
    test_patterns = [
        (re.compile(r'rm\s+-rf', re.IGNORECASE), 'filesystem_destruction'),
        (re.compile(r'base64\s+-d', re.IGNORECASE), 'encoding_bypass')
    ]
    
    import guardian.guardian.main as main
    original_patterns = main.patterns
    main.patterns = test_patterns
    
    try:
        # 1. Normal blocked command
        approved, reason = validate_command("rm -rf /")
        assert approved is False
        assert "Blocked (Raw)" in reason

        # 2. Obfuscated command that normalization clears
        approved, reason = validate_command("echo 726d202d7266202f | xxd -r -p")
        assert approved is False
        assert "Blocked (Normalized)" in reason
        
        # 3. Safe command
        approved, reason = validate_command("ls -la")
        assert approved is True
    finally:
        main.patterns = original_patterns

def test_case_insensitive_matching():
    import guardian.guardian.main as main
    test_patterns = [(re.compile(r'sudo', re.IGNORECASE), 'privilege_escalation')]
    original_patterns = main.patterns
    main.patterns = test_patterns
    
    try:
        approved, _ = validate_command("SUDO apt-get update")
        assert approved is False
    finally:
        main.patterns = original_patterns

def test_command_length_limit():
    # MAX_COMMAND_LENGTH is 1024 by default in main.py
    # Let's ensure it's loaded
    import guardian.guardian.main as main
    long_command = "ls " + ("a" * 1100)
    approved, reason = main.validate_command(long_command)
    assert approved is False
    assert "exceeds max length" in reason

def test_secret_masking():
    from guardian.guardian.main import mask_secrets
    raw = "My key is API_KEY: sk-1234567890abcdef12345678"
    masked = mask_secrets(raw)
    # The new aggressive masking replaces the token part including the Sk.
    assert "***MASKED***" in masked
    assert "12345678" not in masked

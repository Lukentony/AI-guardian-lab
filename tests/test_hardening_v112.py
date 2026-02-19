import pytest
from guardian.main import normalize_command, validate_command, patterns

def test_subshell_detection():
    # Structural token that should be detected in RAW form
    cmd = "$(rm -rf /)"
    approved, reason = validate_command(cmd)
    assert not approved
    assert "Subshell Execution" in reason

def test_encoding_bypass_detection():
    # Base64 that should be detected in RAW form before normalization
    cmd = "echo 'cm0gLXJmIC8=' | base64 -d"
    approved, reason = validate_command(cmd)
    assert not approved
    assert "Encoding Bypass" in reason

def test_obfuscation_bypass():
    # Concatenated string that normalization should flatten
    cmd = "c''a\"\"t /etc/passwd"
    approved, reason = validate_command(cmd)
    assert not approved
    assert "Sensitive Files" in reason

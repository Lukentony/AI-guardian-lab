import sys
import os
import pytest
from unittest.mock import MagicMock

# Mocks are now handled by conftest.py

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from agent.agent.main import clean_command
except ModuleNotFoundError:
    pytest.skip("modulo agent non disponibile in questo container", allow_module_level=True)

@pytest.mark.skip(reason="Agent module is not available in the guardian container")
def test_clean_command_markdown():
    markdown_input = "Here is the command:\n```bash\nls -la\n```"
    assert clean_command(markdown_input) == "ls -la"
    
    simple_markdown = "```\npwd\n```"
    assert clean_command(simple_markdown) == "pwd"

@pytest.mark.skip(reason="Agent module is not available in the guardian container")
def test_clean_command_fallback():
    # User just sends text
    assert clean_command("whoami") == "whoami"
    # User sends with single backticks
    assert clean_command("`ls`") == "ls"

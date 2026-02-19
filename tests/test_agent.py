import sys
import os
import pytest
from unittest.mock import MagicMock

# Python 3.14 workaround: imghdr was removed but litellm (dependency of main) imports it
sys.modules['imghdr'] = MagicMock()
# Mock litellm entirely to avoid complex dependency chain in tests
sys.modules['litellm'] = MagicMock()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.agent.main import clean_command

def test_clean_command_markdown():
    markdown_input = "Here is the command:\n```bash\nls -la\n```"
    assert clean_command(markdown_input) == "ls -la"
    
    simple_markdown = "```\npwd\n```"
    assert clean_command(simple_markdown) == "pwd"

def test_clean_command_fallback():
    # User just sends text
    assert clean_command("whoami") == "whoami"
    # User sends with single backticks
    assert clean_command("`ls`") == "ls"

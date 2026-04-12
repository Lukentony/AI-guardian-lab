import sys
import os
from unittest.mock import MagicMock

# Force absolute paths for the entire project
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "guardian"))
sys.path.insert(0, os.path.join(ROOT_DIR, "guardian", "guardian"))
sys.path.insert(0, os.path.join(ROOT_DIR, "agent"))

# Python 3.13+ compatibility mock
if sys.version_info >= (3, 13):
    sys.modules['imghdr'] = MagicMock()

# Global mocks for CI environments without LLM/Ollama
sys.modules['litellm'] = MagicMock()

# Ensure we are in testing mode to avoid RuntimeError in main.py
os.environ['TESTING'] = '1'
os.environ['API_KEY'] = 'test-key'
os.environ['OLLAMA_URL'] = 'http://localhost:11434'

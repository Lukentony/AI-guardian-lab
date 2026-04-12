import sys
import os
from unittest.mock import MagicMock

# 1. Setup absolute paths BEFORE any imports
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "guardian"))
sys.path.insert(0, os.path.join(ROOT_DIR, "guardian", "guardian"))
sys.path.insert(0, os.path.join(ROOT_DIR, "agent"))

# 2. Set environment variables BEFORE any imports to avoid RuntimeError in main.py
os.environ['TESTING'] = '1'
os.environ['API_KEY'] = 'ci-test-key'
os.environ['OLLAMA_URL'] = 'http://localhost:11434'
os.environ['PATTERNS_PATH'] = os.path.join(ROOT_DIR, 'guardian/config/patterns.yaml')
os.environ['POLICY_PATH'] = os.path.join(ROOT_DIR, 'guardian/config/policy.yaml')
os.environ['DB_PATH'] = os.path.join(ROOT_DIR, 'tests/data/test.db')

# 3. Global Mocks for CI
if sys.version_info >= (3, 13):
    sys.modules['imghdr'] = MagicMock()

# Mock litellm globally to avoid network/import issues
mock_litellm = MagicMock()
mock_response = MagicMock()
mock_response.choices = [MagicMock()]
mock_response.choices[0].message.content = '{"coherent": true, "confidence": 0.9, "reason": "mocked"}'
mock_litellm.completion.return_value = mock_response
sys.modules['litellm'] = mock_litellm

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Absolute project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

from intent import classify_command, classify_task, check_intent_mapping, check_intent_llm

def test_classify_command():
    assert classify_command("ls -la") == "read"
    assert classify_command("curl http://example.com") == "network"
    assert classify_command("unknown_binary") is None
    assert classify_command("") is None

def test_classify_task():
    assert classify_task("list all files") == "read"
    assert classify_task("delete old logs") == "delete"
    assert classify_task("") is None # empty skip
    assert classify_task("test") is None # <=5 chars skip

def test_check_intent_mapping():
    # read command + read task -> not blocked
    res1 = check_intent_mapping("ls -la", "list files")
    assert not res1["blocked"]
    assert res1["intent_source"] == "mapping"
    
    # read command + delete task -> blocked
    res2 = check_intent_mapping("ls -la", "delete everything")
    assert res2["blocked"]
    assert res2["intent_source"] == "mapping"
    assert "conflicts with task family" in res2["reason"]
    
    # task skip -> approved
    res3 = check_intent_mapping("ls -la", "")
    assert not res3["blocked"]
    assert res3["intent_source"] == "skip"
    
    # needs llm -> unclassifiable command
    res4 = check_intent_mapping("date", "check time")
    assert not res4["blocked"]
    assert res4["needs_llm"]

@patch('intent.completion')
def test_check_intent_llm(mock_completion):
    # Setup mock response for coherent true
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"coherent": true, "confidence": 0.9, "reason": "test"}'
    mock_completion.return_value = mock_response
    
    res1 = check_intent_llm("date", "check the current time")
    assert not res1["blocked"]
    assert res1["intent_source"] == "llm"
    assert res1["confidence"] == 0.9
    
    # Setup mock response for blocked
    mock_response.choices[0].message.content = '{"coherent": false, "confidence": 0.8, "reason": "danger"}'
    res2 = check_intent_llm("date", "delete everything")
    assert res2["blocked"]
    assert res2["intent_source"] == "llm"
    
    # Setup mock response for low confidence -> not blocked
    mock_response.choices[0].message.content = '{"coherent": false, "confidence": 0.5, "reason": "unsure"}'
    res3 = check_intent_llm("date", "maybe delete")
    assert not res3["blocked"]
    assert res3["intent_source"] == "llm"
    
    # Error fallback
    mock_completion.side_effect = Exception("API error")
    res4 = check_intent_llm("date", "test")
    assert not res4["blocked"]
    assert res4["intent_source"] == "llm_error"

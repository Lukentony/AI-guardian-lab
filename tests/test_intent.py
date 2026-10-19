"""Regression coverage for complete command effects and strict semantic responses."""

from types import SimpleNamespace

import pytest

from guardian.guardian import intent


def response(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.mark.parametrize(
    "command,expected",
    [
        ("ls -la", "read"),
        ("curl http://example.com", "network"),
        ("unknown_binary", None),
        ("", None),
        ("ls && curl http://example.com", None),
        ("cat file > target", None),
    ],
)
def test_classify_command(command, expected):
    assert intent.classify_command(command) == expected


@pytest.mark.parametrize(
    "task,expected",
    [
        ("list all files", "read"),
        ("delete old logs", "delete"),
        ("analyze disk usage", "read"),
        ("elenca tutti i file", "read"),
        ("check and delete logs", None),
        ("", None),
        ("test", None),
    ],
)
def test_classify_task(task, expected):
    assert intent.classify_task(task) == expected


@pytest.mark.parametrize(
    "command,task",
    [
        ("rm -rf /tmp", "list files"),
        ("ls -la", "delete everything"),
        ("curl https://example.com", "read project notes"),
        ("cat file > target", "read project notes"),
    ],
)
def test_conflicts(command, task):
    assert intent.check_intent_mapping(command, task)["blocked"]


def test_missing_and_mixed_tasks():
    assert intent.check_intent_mapping("ls", "")["blocked"]
    assert intent.check_intent_mapping("ls", "test")["needs_llm"]
    assert intent.check_intent_mapping("ls", "check and delete logs")["needs_llm"]


@pytest.mark.parametrize(
    "content",
    [
        "{}",
        "[]",
        "null",
        "not JSON",
        '{"coherent": "false", "confidence": 1, "reason": "bad"}',
        '{"coherent": true, "confidence": true, "reason": "bad"}',
        '{"coherent": true, "confidence": NaN, "reason": "bad"}',
        '{"coherent": true, "confidence": 1.1, "reason": "bad"}',
        '{"coherent": false, "confidence": 0.5, "reason": "unsure"}',
        '{"coherent": true, "confidence": 0.5, "reason": "unsure"}',
        '{"coherent": true, "confidence": 1}',
    ],
)
def test_invalid_or_uncertain_model_never_approves(monkeypatch, content):
    monkeypatch.setattr(intent, "completion", lambda **kwargs: response(content))
    assert intent.check_intent_llm("date", "check time")["blocked"]


def test_valid_model_contract_and_bounded_timeout(monkeypatch):
    calls = []

    def complete(**kwargs):
        calls.append(kwargs)
        return response('{"coherent": true, "confidence": 0.95, "reason": "Matches task"}')

    monkeypatch.setattr(intent, "completion", complete)
    assert not intent.check_intent_llm("date", "check time")["blocked"]
    assert calls[0]["timeout"] <= 3 and calls[0]["max_retries"] == 0


def test_unavailable_denies_even_with_obsolete_fail_open_setting(monkeypatch):
    monkeypatch.setenv("FAIL_CLOSED_ON_LLM_ERROR", "false")
    assert intent.check_intent_llm("date", "check time")["blocked"]

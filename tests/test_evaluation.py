from pathlib import Path

import pytest

from guardian.guardian import main
from scripts.evaluate_system_one import check_splits, evaluate, load_cases, summarize

DATA = Path(__file__).parent / "data"


def test_splits_are_group_disjoint():
    calibration = load_cases(DATA / "system_one_calibration.jsonl")
    test = load_cases(DATA / "system_one_test.jsonl")
    check_splits(calibration, test)
    assert len(calibration) == len(test) == 8
    with pytest.raises(ValueError):
        check_splits(calibration, calibration)


def test_summary_distinguishes_unavailable_from_correct_detection():
    cases = load_cases(DATA / "system_one_calibration.jsonl")

    def offline(*args, **kwargs):
        return {"status": "unavailable", "latency_ms": 0}

    result = evaluate(cases, main.system_one_config, main.validate_command, offline)
    report = summarize(result)
    assert report["observed"] == 0 and report["unavailable"] == 8
    assert report["question_brier_mean"] is None
    assert report["enforcement_enabled"] is False


def test_long_measurement_does_not_change_production_budget():
    cases = load_cases(DATA / "system_one_calibration.jsonl")[:1]

    def slow(config, *args, **kwargs):
        assert config.timeout_seconds == 10
        return {
            "status": "observed",
            "latency_ms": 2600,
            "probabilities": {
                "coherence": 1,
                "unauthorized_transfer": 0,
                "untrusted_instruction": 0,
                "insufficient_context": 0,
            },
        }

    report = summarize(
        evaluate(cases, main.system_one_config, main.validate_command, slow, measurement_timeout=10)
    )
    assert report["within_production_budget"] == 0
    assert main.system_one_config.timeout_seconds == 0.5
    assert report["question_brier_mean"] == 0

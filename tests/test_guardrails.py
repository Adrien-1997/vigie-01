import json

import pytest

import backend.guardrails as guardrails


def test_calls_under_limit_are_allowed_and_counted(tmp_path, monkeypatch):
    monkeypatch.setattr(guardrails, "_BUDGET_FILE", tmp_path / "budget.json")
    monkeypatch.setattr(guardrails, "MAX_LLM_CALLS_PER_DAY", 2)

    guardrails.check_and_increment_llm_call()
    guardrails.check_and_increment_llm_call()

    assert guardrails.remaining_calls_today() == 0


def test_call_beyond_limit_raises_budget_exceeded(tmp_path, monkeypatch):
    monkeypatch.setattr(guardrails, "_BUDGET_FILE", tmp_path / "budget.json")
    monkeypatch.setattr(guardrails, "MAX_LLM_CALLS_PER_DAY", 1)

    guardrails.check_and_increment_llm_call()
    with pytest.raises(guardrails.BudgetExceeded):
        guardrails.check_and_increment_llm_call()


def test_counter_resets_on_new_day(tmp_path, monkeypatch):
    budget_file = tmp_path / "budget.json"
    budget_file.write_text(json.dumps({"date": "2000-01-01", "calls": 1}), encoding="utf-8")
    monkeypatch.setattr(guardrails, "_BUDGET_FILE", budget_file)
    monkeypatch.setattr(guardrails, "MAX_LLM_CALLS_PER_DAY", 1)

    assert guardrails.remaining_calls_today() == 1
    guardrails.check_and_increment_llm_call()  # stale date must be treated as a fresh day, not raise

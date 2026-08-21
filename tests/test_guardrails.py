import json

import pytest

import backend.guardrails as guardrails


def test_calls_under_limit_are_allowed_and_counted(monkeypatch):
    monkeypatch.setattr(guardrails, "MAX_LLM_CALLS_PER_DAY", 2)

    guardrails.check_and_increment_llm_call()
    guardrails.check_and_increment_llm_call()

    assert guardrails.remaining_calls_today() == 0


def test_call_beyond_limit_raises_budget_exceeded(monkeypatch):
    monkeypatch.setattr(guardrails, "MAX_LLM_CALLS_PER_DAY", 1)

    guardrails.check_and_increment_llm_call()
    with pytest.raises(guardrails.BudgetExceeded):
        guardrails.check_and_increment_llm_call()


def test_counter_resets_on_new_day(persistence, monkeypatch):
    persistence._budget_file.write_text(json.dumps({"date": "2000-01-01", "calls": 1}), encoding="utf-8")
    monkeypatch.setattr(guardrails, "MAX_LLM_CALLS_PER_DAY", 1)

    assert guardrails.remaining_calls_today() == 1
    guardrails.check_and_increment_llm_call()  # stale date must be treated as a fresh day, not raise


def test_budget_survives_a_new_persistence_instance_on_the_same_storage(persistence, monkeypatch):
    """Le compteur est dans le stockage, pas en mémoire de processus : un redémarrage ne doit pas
    remettre le plafond à zéro. C'est ce que le disque éphémère de Cloud Run cassait."""
    from backend.memory.persistence import LocalFilePersistence, set_persistence

    monkeypatch.setattr(guardrails, "MAX_LLM_CALLS_PER_DAY", 1)
    guardrails.check_and_increment_llm_call()

    set_persistence(
        LocalFilePersistence(
            budget_file=persistence._budget_file,
            seen_file=persistence._seen_file,
            analyzed_file=persistence._analyzed_file,
        )
    )

    with pytest.raises(guardrails.BudgetExceeded):
        guardrails.check_and_increment_llm_call()


def test_calls_are_attributed_to_the_node_that_spent_them(monkeypatch):
    """Le prérequis de tout arbitrage du partage de budget (docs/cadrage.md §11) : savoir lequel des
    nœuds a consommé quoi. Un compteur global seul dit qu'un run a été tronqué, pas par qui."""
    monkeypatch.setattr(guardrails, "MAX_LLM_CALLS_PER_DAY", 5)

    guardrails.check_and_increment_llm_call("analyze")
    guardrails.check_and_increment_llm_call("analyze")
    guardrails.check_and_increment_llm_call("verify")
    guardrails.check_and_increment_llm_call("thread")

    assert guardrails.calls_by_node() == {"analyze": 2, "verify": 1, "thread": 1}


def test_a_refused_call_is_not_charged_to_its_node(monkeypatch):
    """Le refus de réservation précède l'appel au modèle : il n'a rien coûté. L'imputer ferait porter
    au nœud une dépense qu'il n'a pas obtenue, et gonflerait sa part dans l'arbitrage."""
    monkeypatch.setattr(guardrails, "MAX_LLM_CALLS_PER_DAY", 1)

    guardrails.check_and_increment_llm_call("verify")
    with pytest.raises(guardrails.BudgetExceeded):
        guardrails.check_and_increment_llm_call("thread")

    assert guardrails.calls_by_node() == {"verify": 1}


def test_tally_is_per_run_while_the_daily_ceiling_is_not(monkeypatch):
    """reset_call_tally() borne une mesure de run ; il ne doit surtout pas rouvrir le plafond du
    jour, qui est persistant — sinon un second run le contournerait en se réinitialisant."""
    monkeypatch.setattr(guardrails, "MAX_LLM_CALLS_PER_DAY", 1)

    guardrails.check_and_increment_llm_call("analyze")
    guardrails.reset_call_tally()

    assert guardrails.calls_by_node() == {}
    with pytest.raises(guardrails.BudgetExceeded):
        guardrails.check_and_increment_llm_call("analyze")

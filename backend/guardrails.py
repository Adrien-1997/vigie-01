"""Garde-fou de budget LLM quotidien (cf. docs/cadrage.md §6 et §8 — non négociable).

Persistance par fichier local pour V1 : pas encore de backend Firestore (stack "à valider"
dans le README), donc pas de compteur partagé entre exécutions distribuées. Suffisant pour
un run planifié unique par jour (Cloud Scheduler) ; à remplacer si plusieurs instances
tournent en parallèle (limite connue, cf. section correspondante du cadrage).
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path

from backend.config import MAX_LLM_CALLS_PER_DAY

_BUDGET_FILE = Path(__file__).parent / ".llm_budget.json"


class BudgetExceeded(RuntimeError):
    pass


def _load() -> dict:
    if not _BUDGET_FILE.exists():
        return {"date": "", "calls": 0}
    return json.loads(_BUDGET_FILE.read_text(encoding="utf-8"))


def _save(data: dict) -> None:
    _BUDGET_FILE.write_text(json.dumps(data), encoding="utf-8")


def check_and_increment_llm_call() -> None:
    """À appeler avant chaque appel LLM. Lève BudgetExceeded si le plafond quotidien est atteint."""
    today = date.today().isoformat()
    data = _load()
    if data["date"] != today:
        data = {"date": today, "calls": 0}

    if data["calls"] >= MAX_LLM_CALLS_PER_DAY:
        raise BudgetExceeded(
            f"Plafond quotidien d'appels LLM atteint ({MAX_LLM_CALLS_PER_DAY}/jour). "
            f"Run interrompu à {datetime.now(timezone.utc).isoformat()} "
            "(garde-fou non négociable, cf. docs/cadrage.md §6)."
        )

    data["calls"] += 1
    _save(data)


def remaining_calls_today() -> int:
    today = date.today().isoformat()
    data = _load()
    used = data["calls"] if data["date"] == today else 0
    return MAX_LLM_CALLS_PER_DAY - used

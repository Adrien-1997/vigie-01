"""Garde-fou de budget LLM quotidien (cf. docs/cadrage.md §6 et §8 — non négociable).

Le compteur est porté par la couche de persistance (backend/memory/persistence.py) : fichier local
en dev, Firestore en production. La réservation est déléguée au backend plutôt que faite ici en
lecture-modification-écriture, parce que l'atomicité dépend du stockage — avec un disque local elle
est acquise (un seul processus), avec plusieurs instances Cloud Run elle demande une transaction.
Un compteur en mémoire ou en fichier sur Cloud Run se réinitialiserait à chaque cold start, ce qui
rendrait ce plafond contournable par un simple redémarrage.
"""

from datetime import UTC, date, datetime

from backend.config import MAX_LLM_CALLS_PER_DAY
from backend.memory.persistence import get_persistence


class BudgetExceeded(RuntimeError):
    pass


def check_and_increment_llm_call() -> None:
    """À appeler avant chaque appel LLM. Lève BudgetExceeded si le plafond quotidien est atteint.

    L'appel n'a pas lieu quand cette exception est levée : elle est déclenchée par le refus de
    réservation, en amont du modèle. L'item sur lequel elle tombe n'a donc rien coûté et reste
    entièrement à traiter — c'est ce qui permet aux nœuds appelants de le rendre à une collecte
    ultérieure plutôt que de le marquer comme vu (cf. backend/agents/analyst.py).
    """
    today = date.today().isoformat()
    if not get_persistence().reserve_llm_call(today, MAX_LLM_CALLS_PER_DAY):
        raise BudgetExceeded(
            f"Plafond quotidien d'appels LLM atteint ({MAX_LLM_CALLS_PER_DAY}/jour) "
            f"à {datetime.now(UTC).isoformat()} : appel refusé, run tronqué "
            "(garde-fou non négociable, cf. docs/cadrage.md §6)."
        )


def remaining_calls_today() -> int:
    return MAX_LLM_CALLS_PER_DAY - get_persistence().calls_used(date.today().isoformat())

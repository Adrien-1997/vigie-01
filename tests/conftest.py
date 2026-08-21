import os

# backend/config.py requires these at import time, with no defaults (fail-fast by design).
# Tests must not depend on a local .env, so set safe defaults before backend.* is imported.
os.environ.setdefault("MAX_STEPS_PER_RUN", "20")
os.environ.setdefault("MAX_LLM_CALLS_PER_DAY", "200")

import pytest  # noqa: E402  (must follow the env defaults above)


@pytest.fixture(autouse=True)
def persistence(tmp_path):
    """Isole l'état persistant de chaque test dans un répertoire temporaire.

    Autouse et non optionnel : le budget LLM, les liens vus et l'historique analysé sont des
    fichiers réels du dépôt. Un test qui oublierait de les rediriger corromprait le compteur de
    budget du jour ou l'historique de recoupement — le genre d'effet de bord qu'on ne remarque
    qu'en production de digest.
    """
    from backend.guardrails import reset_call_tally
    from backend.memory.persistence import LocalFilePersistence, set_persistence

    # Même raison que ci-dessus, pour l'autre état qui survit à un test : la répartition des appels
    # par nœud vit en mémoire de module, donc elle fuit d'un test au suivant si on ne la vide pas.
    reset_call_tally()

    instance = LocalFilePersistence(
        budget_file=tmp_path / "budget.json",
        seen_file=tmp_path / "seen.json",
        analyzed_file=tmp_path / "history.json",
    )
    set_persistence(instance)
    yield instance
    set_persistence(None)

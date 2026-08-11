"""Nœud mémoire : dédoublonnage court terme (README architecture, docs/cadrage.md §10 V1).

Stockage local fichier pour V1 : c'est une mémoire "courte" (fenêtre glissante), pas l'historique
interrogeable prévu en V3. Placeholder documenté, comme backend/guardrails.py : à remplacer par
Firestore si plusieurs instances doivent un jour partager cet état (déploiement Cloud Run, cf.
NOTES.private.md sur le séquencement GCP).
"""

import json
from datetime import date, timedelta
from pathlib import Path

from backend.state import RawItem, VeilleState

_STORE_FILE = Path(__file__).parent / ".seen_items.json"
DEDUP_WINDOW_DAYS = 7


def _load() -> dict[str, str]:
    if not _STORE_FILE.exists():
        return {}
    return json.loads(_STORE_FILE.read_text(encoding="utf-8"))


def _save(seen: dict[str, str]) -> None:
    _STORE_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")


def _prune(seen: dict[str, str]) -> dict[str, str]:
    cutoff = date.today() - timedelta(days=DEDUP_WINDOW_DAYS)
    return {link: seen_date for link, seen_date in seen.items() if date.fromisoformat(seen_date) >= cutoff}


def deduplicate(state: VeilleState) -> VeilleState:
    """Nœud LangGraph : retire les raw_items déjà vus (clé = link), avant l'appel LLM de l'analyste.

    Placé entre collect et analyze plutôt qu'après analyze : un item déjà vu ne doit pas seulement
    être exclu du digest, il ne doit même pas être ré-analysé — sinon le budget LLM (§8) est
    consommé chaque jour sur des items déjà traités la veille.
    """
    seen = _prune(_load())
    today = date.today().isoformat()

    new_items: list[RawItem] = []
    for item in state["raw_items"]:
        if item["link"] in seen:
            continue
        new_items.append(item)
        seen[item["link"]] = today

    _save(seen)
    return {"raw_items": new_items}

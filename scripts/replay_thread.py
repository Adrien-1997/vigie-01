"""Rejoue le seul nœud `thread` sur des items déjà analysés, sans repasser par la chaîne complète.

**Raison d'être.** Le budget LLM est un compteur global unique (backend/guardrails.py) et `thread`
est le dernier nœud du graphe : quand le plafond quotidien tombe, c'est lui qui absorbe tout le
déficit. Vécu le 2026-08-21, premier run à atteindre les 200 appels — 17 items franchissaient le
portillon du threader, 3 seulement ont été rattachés, les 14 autres n'ayant jamais été soumis au
modèle. Relancer le pipeline entier pour les rattraper est le mauvais outil : le dédoublonnage
écarte les items déjà vus, donc la collecte ne les ramène pas, et un run complet coûte la totalité
du budget. Ce script reprend le lot là où il a été coupé, pour le coût du threading seul (62 appels
pour 36 items le 2026-08-21, contre 200 pour un run complet).

**Ce qu'il n'est pas.** Un outil d'opérateur, comme scripts/daily_run.py : importé par aucun nœud,
absent de la production (où un run non tronqué rend ce rattrapage inutile), et sans état propre —
il écrit dans l'historique par le même `record_analyzed` que le nœud en production, jamais en
direct. Il ne rejoue pas non plus l'analyse : les items doivent déjà porter category/summary/
citation/location, donc être passés par `analyze` et `verify`.

**Pourquoi il saute les items déjà instrumentés.** Réescalader un item dont `has_thread_candidate`
est déjà écrit repaierait des appels pour réécrire des champs justes. La fenêtre d'historique reste
entière côté threader : un item sauté ici demeure candidat au rattachement pour les autres.

Usage :
    python -m scripts.replay_thread                # les items du jour non encore instrumentés
    python -m scripts.replay_thread --dry-run      # sonde du portillon seule, aucun appel LLM
    python -m scripts.replay_thread --day 2026-08-21 --all
"""

import argparse
import json
from datetime import date

from backend.agents.threader import thread_events
from backend.config import (
    MAX_THREAD_ESCALATIONS_PER_RUN,
    MAX_THREAD_STEPS_PER_ITEM,
    THREAD_GATE_MIN_SCORE,
)
from backend.guardrails import remaining_calls_today
from backend.memory.store import analyzed_window, search_thread_candidates


def items_for(day: str, skip_instrumented: bool = True) -> list[dict]:
    """Les items analysés d'un jour donné, moins ceux qu'un run a déjà instrumentés."""
    batch = [r for r in analyzed_window().values() if (r.get("date") or "")[:10] == day]
    if skip_instrumented:
        batch = [r for r in batch if "has_thread_candidate" not in r]
    return batch


def main(day: str, dry_run: bool, include_all: bool) -> int:
    batch = items_for(day, skip_instrumented=not include_all)
    print(f"Jour {day} : {len(batch)} item(s) à traiter.")
    print(f"Budget : {remaining_calls_today()} appel(s) restant(s) aujourd'hui.")
    if not batch:
        print("Rien à rejouer — tous les items du jour portent déjà l'instrumentation du threader.")
        return 0

    # Même sonde que le nœud, au même seuil : ce que le portillon retiendra, sans rien dépenser.
    eligible = [
        item
        for item in batch
        if search_thread_candidates(
            f"{item['title_fr']} {item['summary']}",
            exclude_link=item["link"],
            limit=1,
            min_score=THREAD_GATE_MIN_SCORE,
        )
    ]
    escalations = min(len(eligible), MAX_THREAD_ESCALATIONS_PER_RUN)
    print(f"Portillon (>= {THREAD_GATE_MIN_SCORE}) franchi par {len(eligible)}/{len(batch)} item(s).")
    print(f"Escalades : {escalations} (plafond {MAX_THREAD_ESCALATIONS_PER_RUN}).")
    print(f"Coût : {escalations * 2} appel(s) au mieux, {escalations * (MAX_THREAD_STEPS_PER_ITEM + 1)} au pire.")

    if dry_run:
        print("\n--dry-run : nœud non exécuté, aucun appel LLM.")
        return 0

    if escalations * 2 > remaining_calls_today():
        # Le nœud saurait s'arrêter (BudgetExceeded est rattrapé et laisse thread_checked à False),
        # mais un rejeu qui se sait tronqué d'avance n'a pas d'intérêt : il faudrait le relancer.
        print("\nBudget insuffisant même pour le plancher d'escalade : rejeu non lancé.")
        return 1

    result = thread_events({"raw_items": [], "analyzed_items": batch, "truncated": False})
    out = result["analyzed_items"]

    threads: dict[str, list[str]] = {}
    for item in out:
        if item.get("thread_id"):
            threads.setdefault(item["thread_id"], []).append(item["title_fr"])

    print("\n-- résultat --")
    print(f"Portillon franchi : {sum(1 for i in out if i.get('has_thread_candidate'))}")
    print(f"Examinés par le modèle : {sum(1 for i in out if i.get('thread_checked'))}")
    print(f"Rattachés : {sum(1 for i in out if i.get('thread_id'))}/{len(out)}")
    print(f"Tronqué : {result['truncated']} — budget restant : {remaining_calls_today()}")
    print(json.dumps(threads, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--day", default=date.today().isoformat(), help="jour ciblé (défaut : aujourd'hui)")
    parser.add_argument("--dry-run", action="store_true", help="sonde du portillon seule, aucun appel LLM")
    parser.add_argument("--all", action="store_true", help="inclure les items déjà instrumentés")
    args = parser.parse_args()
    raise SystemExit(main(args.day, args.dry_run, args.all))

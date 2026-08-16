"""Construit un échantillon pour mesurer la précision de classification (cf. docs/cadrage.md §7).

Usage : python -m backend.eval.build_sample [--per-source N]
Puis  : python -m backend.eval.annotate
Puis  : python -m backend.eval.score

Dimensionnement : le coût est d'un appel LLM par item retenu, et il s'ajoute à celui du run
quotidien (~148 appels, cf. scripts/daily_run.py) sur le même plafond journalier. Le script refuse
donc de démarrer un échantillon qu'il ne pourrait pas terminer, en indiquant le `--per-source` qui
tient dans le budget restant : mieux vaut choisir la taille de l'échantillon délibérément que la
subir. Un échantillon plus petit élargit la marge d'erreur d'un KPI qui l'a déjà large (§7).
"""

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from backend.agents.analyst import _clean_text, classify_item
from backend.agents.collector import collect
from backend.guardrails import BudgetExceeded, remaining_calls_today

SAMPLE_FILE = Path(__file__).parent / "sample.json"


def _archive_existing() -> None:
    """Met de côté un échantillon déjà annoté avant de le remplacer.

    `sample.json` n'est pas versionné : l'écraser détruirait sans recours le travail d'annotation
    qui fonde la précision mesurée, et l'entrée des retests de frontière qui rejouent le prompt sur
    les items disputés. Une mesure ne se rejoue pas si son échantillon a disparu.
    """
    if not SAMPLE_FILE.exists():
        return
    rows = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    annotated = sum(1 for r in rows if r.get("category_gold"))
    if not annotated:
        return
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    archive = SAMPLE_FILE.with_name(f"sample-{stamp}.json")
    archive.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Échantillon existant ({annotated} items annotés) archivé dans {archive.name}.\n")


def main(per_source: int) -> None:
    raw = collect({})["raw_items"]

    by_source: dict[str, list] = defaultdict(list)
    for item in raw:
        by_source[item["source"]].append(item)

    selected = [item for items in by_source.values() for item in items[:per_source]]
    print(f"Échantillon : {len(selected)} items ({per_source} max par source, {len(by_source)} sources)")

    remaining = remaining_calls_today()
    print(f"Budget : {remaining} appels restants, {len(selected)} nécessaires.")
    if len(selected) > remaining:
        fits = remaining // max(len(by_source), 1)
        if fits < 1:
            print(
                f"Budget insuffisant — échantillon non construit. Il reste moins d'un appel par "
                f"source ({remaining} pour {len(by_source)} sources) : aucun échantillon stratifié "
                "n'est constructible aujourd'hui, attendre le plafond du lendemain."
            )
        else:
            print(
                f"Budget insuffisant — échantillon non construit. Relancer avec --per-source {fits} "
                f"(~{fits * len(by_source)} items), ou attendre le plafond du lendemain."
            )
        return

    rows = []
    try:
        for item in selected:
            try:
                result = classify_item(item)
            except ValidationError:
                # Même traitement que le nœud analyze (backend/agents/analyst.py) : le modèle peut
                # renvoyer une catégorie hors énumération sur une source non francophone. L'item est
                # écarté comme non classable. Le faire remonter perdrait tout l'échantillon déjà
                # payé — c'est exactement ce qui est arrivé ici avant ce correctif.
                print(f"  [--] {item['source']} — réponse non validable, écarté — {item['title'][:60]}")
                continue
            rows.append(
                {
                    "id": len(rows),
                    "source": item["source"],
                    "title": item["title"],
                    "text_excerpt": _clean_text(item["raw_text"])[:500],
                    "link": item["link"],
                    "category_system": result.category,
                    "citation": result.citation,
                    "category_gold": None,
                }
            )
            print(f"  [{len(rows) - 1}] {item['source']} — {result.category} — {item['title'][:70]}")
    except BudgetExceeded:
        # Même règle que dans le pipeline (docs/cadrage.md §8) : un plafond tronque le travail, il
        # ne le détruit pas. Les items déjà classés ont coûté leur appel et restent annotables.
        print(f"\nPlafond atteint après {len(rows)} items : échantillon tronqué, pas perdu.")

    if not rows:
        print("Aucun item classé — rien à écrire.")
        return

    # Archivage ici et non avant la boucle : un run qui échoue en cours de route ne doit pas laisser
    # d'archive orpheline, puisqu'il n'a rien écrit à remplacer.
    _archive_existing()
    SAMPLE_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nÉcrit dans {SAMPLE_FILE} ({len(rows)} items).")
    print("Prochaine étape (dans un terminal interactif) : python -m backend.eval.annotate")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-source", type=int, default=6)
    args = parser.parse_args()
    main(args.per_source)

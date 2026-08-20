"""Gèle un échantillon de paires d'items à annoter à la main (cf. docs/cadrage.md §7, §10 V3).

Deux mesures restaient en attente. Elles portent sur la même question — ces deux items traitent-ils
du même dossier ? — et se répondent donc sur un seul échantillon :

1. **Critère d'acceptation de la V3 tranche 1** (§10) : « un thread ne rassemble que des items
   portant sur le même dossier (mêmes parties, même opération) ». Toutes les paires effectivement
   regroupées par le modèle sont incluses, sans échantillonnage : elles sont peu nombreuses et ce
   sont exactement celles que le critère juge. C'est une mesure de précision du threading, pas de
   rappel — un dossier que le modèle n'a pas su rapprocher n'apparaît pas ici.
2. **Calibration du seuil d'escalade** (§10, arbitrage sur l'extension du vérificateur) : les paires
   sont échantillonnées par bande de score IDF, pour qu'on lise à quel score le taux de vrais
   appariements s'effondre. Sans annotation répartie sur toute l'échelle, un seuil resterait un
   choix au jugé — ce que la campagne d'accumulation devait précisément éviter. La mesure du
   2026-08-18 avait établi que le portillon actuel (au moins un token partagé) laisse passer 100 %
   des items : il ne filtre rien, et seul `MAX_THREAD_ESCALATIONS_PER_RUN` borne le coût.

**Pourquoi geler l'échantillon.** Depuis le 2026-08-20, la rétention est de 7 jours
(`RELATED_ITEMS_WINDOW_DAYS`) : l'historique sur lequel porte cette mesure est purgé au fil de
l'eau, le jour le plus ancien disparaissant à chaque run. Un échantillon reconstruit plus tard ne
porterait pas sur le même corpus et ne serait pas comparable ; reconstruit une semaine plus tard, il
ne trouverait plus aucun des items d'aujourd'hui. Le fichier produit est donc une copie autonome —
il porte tout ce qu'il faut pour annoter et scorer sans relire l'historique, exactement comme
`sample.json` pour la précision de classification.

Aucun appel LLM : le score de chevauchement est déterministe, et le jugement est humain.

Usage : python -m backend.eval.build_pairs [--per-band N] [--days N]
Puis  : python -m backend.eval.annotate_pairs
Puis  : python -m backend.eval.score_pairs
"""

import argparse
import json
import random
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from itertools import combinations
from pathlib import Path

from backend.memory.persistence import get_persistence
from backend.memory.store import RELATED_ITEMS_WINDOW_DAYS

from .candidates import weighted_pairs

PAIRS_FILE = Path(__file__).parent / "pairs.json"

# Bandes de score IDF. Bornes reprises du rapport de `candidates.py` pour que l'annotation se lise
# en regard de ses taux d'escalade, et resserrées entre 15 et 30 où le rapport situe la bascule
# (67 % des items à 15, 12 % à 30) : c'est là que le seuil se jouera, donc là qu'il faut du signal.
BANDS = ((0, 10), (10, 15), (15, 20), (20, 25), (25, 30), (30, 40), (40, float("inf")))

# Tirage reproductible : l'échantillon doit pouvoir être rejoué à l'identique pour départager une
# annotation contestée. Un tirage aléatoire non graine ferait dépendre la mesure de l'exécution.
SEED = 20260820


def _side(record: dict) -> dict:
    """Copie autonome d'un item, côté d'une paire — l'annotation ne doit pas relire l'historique."""
    return {
        "title_fr": record.get("title_fr", ""),
        "summary": record.get("summary", ""),
        "source": record.get("source", ""),
        "date": record.get("date", ""),
        "category": record.get("category", ""),
        "country": record.get("country", ""),
        "link": record.get("link", ""),
    }


def _archive_existing() -> None:
    """Met de côté un échantillon déjà annoté avant de le remplacer.

    Même règle que `build_sample.py` : le travail d'annotation fonde la mesure, l'écraser la rendrait
    irrejouable. Le motif est plus fort ici — l'historique d'origine étant purgé sous 7 jours,
    l'échantillon perdu ne serait pas reconstructible, même à l'identique.
    """
    if not PAIRS_FILE.exists():
        return
    rows = json.loads(PAIRS_FILE.read_text(encoding="utf-8"))
    annotated = sum(1 for r in rows if r.get("same_dossier") is not None)
    if not annotated:
        return
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    archive = PAIRS_FILE.with_name(f"pairs-{stamp}.json")
    archive.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Échantillon existant ({annotated} paires annotées) archivé dans {archive.name}.\n")


def _thread_rows(history: list[dict], weight_by_link: dict[frozenset, float]) -> list[dict]:
    """Toutes les paires intra-thread, sans échantillonnage.

    Sans filtre de date, à la différence des paires de portillon : le threader ne masque pas le lot
    courant (divergence volontaire documentée dans CLAUDE.md), donc deux items du même jour peuvent
    légitimement partager un thread — les exclure retirerait de la mesure le cas le plus fréquent.
    """
    by_thread: dict[str, list[dict]] = defaultdict(list)
    for record in history:
        if record.get("thread_id"):
            by_thread[record["thread_id"]].append(record)

    rows = []
    for thread_id, items in sorted(by_thread.items()):
        for a, b in combinations(sorted(items, key=lambda r: (r.get("date", ""), r.get("link", ""))), 2):
            key = frozenset((a.get("link", ""), b.get("link", "")))
            rows.append(
                {
                    "kind": "thread",
                    "thread_id": thread_id,
                    "thread_size": len(items),
                    # None (et non 0) quand la paire est absente du calcul de portillon : les paires
                    # de même date n'y figurent pas, et leur donner 0 les ferait passer pour des
                    # paires sans aucun token commun, ce qui est faux.
                    "idf_weight": weight_by_link.get(key),
                    "shared_tokens": [],
                    "a": _side(a),
                    "b": _side(b),
                    "same_dossier": None,
                }
            )
    return rows


def _gate_rows(history: list[dict], pairs: list[tuple], per_band: int) -> list[dict]:
    """Paires échantillonnées par bande de score, pour lire où le seuil doit tomber."""
    by_band: dict[tuple, list[tuple]] = defaultdict(list)
    for pair in pairs:
        for band in BANDS:
            if band[0] <= pair[0] < band[1]:
                by_band[band].append(pair)
                break

    rng = random.Random(SEED)
    rows = []
    for band in BANDS:
        bucket = by_band.get(band, [])
        # Bandes hautes souvent moins peuplées que `per_band` : on prend tout plutôt que de laisser
        # un trou d'annotation là où le seuil se décide.
        chosen = bucket if len(bucket) <= per_band else rng.sample(bucket, per_band)
        for weight, i, j, shared in sorted(chosen, key=lambda p: -p[0]):
            rows.append(
                {
                    "kind": "gate",
                    "band": f"{band[0]}-{'inf' if band[1] == float('inf') else band[1]}",
                    "band_population": len(bucket),
                    "idf_weight": round(weight, 2),
                    "shared_tokens": sorted(shared)[:12],
                    "a": _side(history[i]),
                    "b": _side(history[j]),
                    "same_dossier": None,
                }
            )
    return rows


def main(per_band: int, days: int) -> None:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    history = get_persistence().analyzed_since(cutoff)
    if len(history) < 2:
        print(f"Historique trop court ({len(history)} item(s)) : rien à échantillonner.")
        return

    _, pairs = weighted_pairs(history)
    weight_by_link = {
        frozenset((history[i].get("link", ""), history[j].get("link", ""))): weight for weight, i, j, _ in pairs
    }

    rows = _thread_rows(history, weight_by_link) + _gate_rows(history, pairs, per_band)
    for index, row in enumerate(rows):
        row["id"] = index

    threads = sum(1 for r in rows if r["kind"] == "thread")
    print(f"Historique : {len(history)} items, {len(pairs)} paires de dates distinctes.")
    print(f"Échantillon : {len(rows)} paires — {threads} intra-thread, {len(rows) - threads} par bande de score.\n")
    for band in BANDS:
        label = f"{band[0]}-{'inf' if band[1] == float('inf') else band[1]}"
        chosen = sum(1 for r in rows if r.get("band") == label)
        population = next((r["band_population"] for r in rows if r.get("band") == label), 0)
        print(f"  bande {label:>8} : {chosen:3d} annotées sur {population} paires")

    _archive_existing()
    PAIRS_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nÉcrit dans {PAIRS_FILE} ({len(rows)} paires).")
    print("Prochaine étape (terminal interactif) : python -m backend.eval.annotate_pairs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-band", type=int, default=8, help="paires tirées par bande de score")
    parser.add_argument("--days", type=int, default=RELATED_ITEMS_WINDOW_DAYS, help="fenêtre d'historique")
    args = parser.parse_args()
    main(args.per_band, args.days)

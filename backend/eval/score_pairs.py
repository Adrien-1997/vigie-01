"""Métriques sur les paires annotées : qualité du threading, et calibration du seuil (§7, §10 V3).

Usage : python -m backend.eval.score_pairs

Deux lectures distinctes, à ne pas confondre :

- **Précision du threading** — sur les paires que le modèle a effectivement regroupées, quelle part
  porte réellement sur le même dossier. C'est le critère d'acceptation de §10 V3 tranche 1, et c'est
  une précision seule : le rappel (les dossiers que le modèle n'a pas rapprochés) n'est pas mesurable
  sur cet échantillon, qui ne contient que ce qu'il a rapproché. Le dire, plutôt que de laisser lire
  une précision élevée comme « le threading marche ».
- **Calibration du seuil** — parmi les paires candidates, à quel score IDF le taux de vrais
  appariements s'effondre. L'échantillon étant stratifié par bande (et non tiré uniformément), les
  taux sont repondérés par la population réelle de chaque bande : sans cela, les bandes hautes,
  volontairement sur-échantillonnées, écraseraient la mesure.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

PAIRS_FILE = Path(__file__).parent / "pairs.json"

# Même correctif d'encodage que score.py : console Windows en cp1252.
sys.stdout.reconfigure(encoding="utf-8")

# En dessous de ce nombre de paires annotées dans une bande, le taux est affiché mais marqué : à
# deux ou trois paires, un seul jugement le fait basculer de 0 à 1. Le masquer laisserait croire que
# la bande n'a pas été évaluée, alors que le problème est le volume.
MIN_SUPPORT = 5

THRESHOLDS = (10, 15, 20, 25, 30, 40)


def _rate(yes: int, total: int) -> str:
    return f"{100 * yes / total:5.1f} %" if total else "    — "


def _print_threading(rows: list[dict]) -> None:
    threads = [r for r in rows if r["kind"] == "thread" and r["same_dossier"] is not None]
    if not threads:
        print("Aucune paire intra-thread annotée — critère d'acceptation V3 tranche 1 non mesuré.\n")
        return

    yes = sum(1 for r in threads if r["same_dossier"] is True)
    no = sum(1 for r in threads if r["same_dossier"] is False)
    unsure = sum(1 for r in threads if r["same_dossier"] == "incertain")

    print("=== Critère d'acceptation V3 tranche 1 — précision du threading ===")
    print(f"  paires intra-thread annotées : {len(threads)}")
    print(f"  même dossier : {yes}   dossiers différents : {no}   incertain : {unsure}")
    print(f"  précision : {_rate(yes, yes + no)}")
    print("  Les « incertain » sortent du dénominateur, jamais comptés comme succès.")
    print("  Précision seule : le rappel n'est pas mesurable ici — un dossier que le modèle n'a pas")
    print("  rapproché ne produit aucune paire à annoter.\n")

    faulty = [r for r in threads if r["same_dossier"] is not True]
    if faulty:
        print("  Paires contestées, par thread :")
        for r in faulty:
            verdict = "incertain" if r["same_dossier"] == "incertain" else "dossiers différents"
            print(f"    [{r['id']}] thread {r['thread_id'][:8]} — {verdict}")
            print(f"        A : {r['a']['title_fr'][:78]}")
            print(f"        B : {r['b']['title_fr'][:78]}")
        print()


def _print_calibration(rows: list[dict]) -> None:
    gate = [r for r in rows if r["kind"] == "gate" and r["same_dossier"] is not None]
    if not gate:
        print("Aucune paire de portillon annotée — seuil non calibrable.\n")
        return

    by_band: dict[str, list[dict]] = defaultdict(list)
    for row in gate:
        by_band[row["band"]].append(row)

    def band_low(label: str) -> float:
        return float(label.split("-")[0])

    print("=== Calibration du seuil d'escalade — taux de vrais appariements par bande ===")
    print(f"  {'bande':>10} {'annotées':>9} {'même dossier':>13} {'taux':>8} {'population':>11}")
    stats = {}
    for label in sorted(by_band, key=band_low):
        bucket = by_band[label]
        yes = sum(1 for r in bucket if r["same_dossier"] is True)
        decided = sum(1 for r in bucket if r["same_dossier"] is not True and r["same_dossier"] != "incertain") + yes
        population = bucket[0]["band_population"]
        flag = " *" if decided < MIN_SUPPORT else ""
        print(f"  {label:>10} {len(bucket):>9} {yes:>13} {_rate(yes, decided):>8} {population:>11}{flag}")
        stats[label] = (yes, decided, population)
    print(f"  (* moins de {MIN_SUPPORT} paires tranchées dans la bande — taux non concluant)\n")

    print("=== Effet d'un seuil, extrapolé à la population réelle des bandes ===")
    print("  Le taux mesuré par bande est appliqué à sa population : l'échantillon est stratifié,")
    print("  donc un comptage brut sur-pondérerait les bandes hautes, tirées à taux plus élevé.")
    print(f"\n  {'seuil':>6} {'paires escaladées':>18} {'vrais appariements estimés':>28} {'précision estimée':>19}")
    for threshold in THRESHOLDS:
        kept = [(label, s) for label, s in stats.items() if band_low(label) >= threshold]
        population = sum(s[2] for _, s in kept)
        estimated = sum(s[2] * (s[0] / s[1]) for _, s in kept if s[1])
        precision = f"{100 * estimated / population:5.1f} %" if population else "    — "
        print(f"  {'≥ ' + str(threshold):>6} {population:>18} {estimated:>28.0f} {precision:>19}")
    print()


def main() -> None:
    if not PAIRS_FILE.exists():
        print("Aucun échantillon. Lance d'abord : python -m backend.eval.build_pairs")
        return

    rows = json.loads(PAIRS_FILE.read_text(encoding="utf-8"))
    annotated = [r for r in rows if r["same_dossier"] is not None]

    if not annotated:
        print("Aucune paire annotée. Lance d'abord : python -m backend.eval.annotate_pairs")
        return
    if len(annotated) < len(rows):
        print(f"Attention : {len(rows) - len(annotated)} paires non annotées, ignorées dans le calcul.\n")

    _print_threading(rows)
    _print_calibration(rows)


if __name__ == "__main__":
    main()

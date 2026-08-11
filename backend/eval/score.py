"""Calcule la précision de classification mesurée sur l'échantillon annoté (cf. docs/cadrage.md §7).

Usage : python -m backend.eval.score
"""

import json
from pathlib import Path

SAMPLE_FILE = Path(__file__).parent / "sample.json"


def main() -> None:
    rows = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    annotated = [r for r in rows if r["category_gold"] is not None]

    if not annotated:
        print("Aucun item annoté. Lance d'abord : python -m backend.eval.annotate")
        return
    if len(annotated) < len(rows):
        print(f"Attention : {len(rows) - len(annotated)} items non annotés, ignorés dans le calcul.\n")

    correct = sum(1 for r in annotated if r["category_system"] == r["category_gold"])
    precision = correct / len(annotated)

    print(f"Précision mesurée : {correct}/{len(annotated)} = {precision:.0%}")
    print(f"(cible cadrage §7 : ≥ 85 % — échantillon de {len(annotated)} items, marge d'erreur large à ce volume)\n")

    disagreements = [r for r in annotated if r["category_system"] != r["category_gold"]]
    if disagreements:
        print("Désaccords (système → réel) :")
        for r in disagreements:
            print(f"  [{r['id']}] système={r['category_system']!r} réel={r['category_gold']!r} — {r['title'][:60]}")
    else:
        print("Aucun désaccord sur cet échantillon.")


if __name__ == "__main__":
    main()

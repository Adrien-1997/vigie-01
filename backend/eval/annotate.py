"""Annotation manuelle de l'échantillon pour mesurer la précision de classification (§7).

Usage (terminal interactif) : python -m backend.eval.annotate
Sauvegarde après chaque item — interruptible et reprenable.
"""

import json
from pathlib import Path

SAMPLE_FILE = Path(__file__).parent / "sample.json"

CATEGORIES = [
    "export_control",
    "contrat_armement",
    "mouvement_militaire",
    "diplomatie_defense",
    "programme_industriel",
    "hors_perimetre",
]


def main() -> None:
    rows = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    todo = [r for r in rows if r["category_gold"] is None]

    if not todo:
        print("Tout est déjà annoté. Lance : python -m backend.eval.score")
        return

    print(f"{len(todo)} items à annoter sur {len(rows)}. Ctrl+C pour arrêter, reprise automatique ensuite.\n")
    print("Catégories :")
    for i, cat in enumerate(CATEGORIES, 1):
        print(f"  {i}. {cat}")
    print()

    for row in todo:
        print("=" * 80)
        print(f"[{row['id']}] {row['source']} — {row['title']}")
        print(f"\n{row['text_excerpt']}\n")
        print(f"(le système a classé : {row['category_system']})")
        while True:
            choice = input("Catégorie réelle (1-6, ou 'lien' pour lire l'article en entier) : ").strip()
            if choice.lower() == "lien":
                print(row["link"])
                continue
            if choice.isdigit() and 1 <= int(choice) <= len(CATEGORIES):
                row["category_gold"] = CATEGORIES[int(choice) - 1]
                break
            print("Entrée invalide.")

        SAMPLE_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nAnnotation terminée. Lance : python -m backend.eval.score")


if __name__ == "__main__":
    main()

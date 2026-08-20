"""Annotation manuelle des paires : ces deux items traitent-ils du même dossier ? (§7, §10 V3)

Usage (terminal interactif) : python -m backend.eval.annotate_pairs
Sauvegarde après chaque paire — interruptible et reprenable.

Règle de jugement, à tenir constante sur tout l'échantillon : « même dossier » veut dire mêmes
parties et même opération (le critère d'acceptation de §10 V3 tranche 1), pas même thème. Deux
frappes distinctes dans la même guerre, deux contrats distincts avec le même industriel, deux
exercices distincts de la même marine : thème commun, dossiers différents — donc « non ». C'est
cette frontière que le seuil doit apprendre à placer ; l'élargir au thème rendrait la mesure
inutile, puisque presque tout le corpus partage un thème.
"""

import json
import sys
from pathlib import Path

PAIRS_FILE = Path(__file__).parent / "pairs.json"

# Même correctif que dans score.py : la console Windows est en cp1252 et ne peut pas écrire les
# titres accentués ni les caractères de cadre, ce qui interrompait l'affichage en cours de paire.
sys.stdout.reconfigure(encoding="utf-8")


def _show_side(label: str, side: dict) -> None:
    print(f"  {label} ({side['source']}, {side['date']}, {side['category']})")
    print(f"     {side['title_fr']}")
    summary = side.get("summary", "")
    if summary:
        print(f"     {summary[:300]}")


def main() -> None:
    rows = json.loads(PAIRS_FILE.read_text(encoding="utf-8"))
    todo = [r for r in rows if r["same_dossier"] is None]

    if not todo:
        print("Tout est déjà annoté. Lance : python -m backend.eval.score_pairs")
        return

    print(f"{len(todo)} paires à annoter sur {len(rows)}. Ctrl+C pour arrêter, reprise automatique ensuite.\n")
    print("Question : les deux items portent-ils sur le MÊME DOSSIER (mêmes parties, même opération) ?")
    print("  o = oui   n = non   ? = incertain (compté à part, jamais comme un succès)")
    print("  lien = afficher les deux URL\n")

    for row in todo:
        print("=" * 88)
        if row["kind"] == "thread":
            origin = f"thread {row['thread_id'][:8]} (taille {row['thread_size']})"
        else:
            origin = f"bande IDF {row['band']}"
        weight = "—" if row["idf_weight"] is None else f"{row['idf_weight']:.1f}"
        print(f"[{row['id']}] {origin} — score IDF {weight}")
        if row["shared_tokens"]:
            print(f"  tokens partagés : {', '.join(row['shared_tokens'])}")
        print()
        _show_side("A", row["a"])
        print()
        _show_side("B", row["b"])
        print()
        while True:
            choice = input("Même dossier ? (o/n/?/lien) : ").strip().lower()
            if choice == "lien":
                print(f"  A : {row['a']['link']}")
                print(f"  B : {row['b']['link']}")
                continue
            if choice in ("o", "n", "?"):
                row["same_dossier"] = {"o": True, "n": False, "?": "incertain"}[choice]
                break
            print("Entrée invalide.")

        PAIRS_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nAnnotation terminée. Lance : python -m backend.eval.score_pairs")


if __name__ == "__main__":
    main()

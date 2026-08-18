"""Calcule les métriques de classification sur l'échantillon annoté (cf. docs/cadrage.md §7).

Usage : python -m backend.eval.score

La précision globale seule est trompeuse sur cet échantillon : près de la moitié des items de
référence sont `hors_perimetre`, donc elle mesure surtout le portillon de périmètre et noie trois
erreurs de natures très différentes — laisser entrer un item hors périmètre (qui pollue le digest),
écarter un item du périmètre (perte silencieuse, invisible à l'écran), et ranger un item du
périmètre dans la mauvaise catégorie (visible et rattrapable par l'analyste). Elle reste affichée
telle quelle pour rester comparable au chiffre suivi dans le cadrage, mais les trois vues qui
suivent sont celles qui disent quoi corriger.
"""

import json
import sys
from collections import Counter
from pathlib import Path

SAMPLE_FILE = Path(__file__).parent / "sample.json"

# Sortie forcée en UTF-8 : la console Windows est en cp1252, où « ≥ » et les caractères de la
# matrice n'existent pas — le script plantait après sa première ligne. Même mode d'échec que celui
# déjà corrigé sur les lectures/écritures de fichiers, mais côté stdout, que la convention
# `encoding="utf-8"` ne couvrait pas.
sys.stdout.reconfigure(encoding="utf-8")

OUT_OF_SCOPE = "hors_perimetre"

# Codes courts pour la matrice de confusion : les libellés complets rendraient les colonnes
# illisibles à six catégories.
SHORT = {
    "hors_perimetre": "HP",
    "contrat_armement": "CA",
    "export_control": "EC",
    "programme_industriel": "PI",
    "mouvement_militaire": "MM",
    "diplomatie_defense": "DD",
}

# En dessous de ce nombre d'items de référence, une précision ou un rappel par catégorie se
# rapporte avec un avertissement : à un ou deux items, un seul jugement d'annotation fait passer le
# F1 de 0 à 1. Le chiffre est affiché quand même — le masquer donnerait à croire que la catégorie
# n'a pas été évaluée, alors que le problème est le volume.
MIN_SUPPORT = 5


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def _print_scope_gate(annotated: list[dict]) -> None:
    """Le périmètre vu comme une décision binaire « retenir ou non », qui est ce que le produit
    engage réellement : un item hors périmètre classé dans la mauvaise catégorie du périmètre reste
    une entrée indue au digest, quelle que soit la catégorie."""
    tp = sum(1 for r in annotated if r["category_system"] != OUT_OF_SCOPE and r["category_gold"] != OUT_OF_SCOPE)
    fp = sum(1 for r in annotated if r["category_system"] != OUT_OF_SCOPE and r["category_gold"] == OUT_OF_SCOPE)
    fn = sum(1 for r in annotated if r["category_system"] == OUT_OF_SCOPE and r["category_gold"] != OUT_OF_SCOPE)
    precision, recall, f1 = _prf(tp, fp, fn)

    print("Portillon de périmètre (retenu au digest vs écarté)")
    print(f"  précision : {precision:.0%}  — sur ce que le système retient, part qui relève bien du périmètre")
    print(f"  rappel    : {recall:.0%}  — sur ce qui relève du périmètre, part que le système retient")
    print(f"  F1        : {f1:.2f}")
    print(f"  {fp} item(s) hors périmètre retenus à tort, {fn} item(s) du périmètre écartés à tort.\n")


def _print_per_category(annotated: list[dict]) -> None:
    gold = Counter(r["category_gold"] for r in annotated)
    system = Counter(r["category_system"] for r in annotated)
    correct = Counter(r["category_gold"] for r in annotated if r["category_system"] == r["category_gold"])

    print(f"Par catégorie ({'*'} = moins de {MIN_SUPPORT} items de référence, chiffre non concluant)")
    print(f"  {'catégorie':22} {'réf.':>5} {'préc.':>6} {'rappel':>7} {'F1':>5}")
    for category in sorted(gold | system, key=lambda c: -gold[c]):
        tp = correct[category]
        precision, recall, f1 = _prf(tp, system[category] - tp, gold[category] - tp)
        flag = " *" if gold[category] < MIN_SUPPORT else ""
        print(f"  {category:22} {gold[category]:>5} {precision:>5.0%} {recall:>6.0%} {f1:>5.2f}{flag}")
    print()


def _print_confusion(annotated: list[dict]) -> None:
    """Matrice complète plutôt que le seul décompte des désaccords : c'est la *direction* de
    l'erreur qui oriente le correctif de prompt — confondre deux catégories du périmètre entre
    elles et laisser entrer du hors-périmètre ne se corrigent pas au même endroit."""
    labels = sorted(SHORT, key=lambda c: c != OUT_OF_SCOPE)
    matrix = Counter((r["category_gold"], r["category_system"]) for r in annotated)

    print("Matrice de confusion (lignes = référence, colonnes = système)")
    print(f"  {'':6}" + "".join(f"{SHORT[c]:>5}" for c in labels))
    for row in labels:
        cells = "".join(f"{matrix[(row, col)] or '·':>5}" for col in labels)
        print(f"  {SHORT[row]:6}{cells}")
    print("  " + ", ".join(f"{SHORT[c]}={c}" for c in labels) + "\n")


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

    print(f"Précision globale : {correct}/{len(annotated)} = {precision:.0%}")
    print(f"(cible cadrage §7 : ≥ 85 % — échantillon de {len(annotated)} items, marge d'erreur large à ce volume)")
    print("Exactitude toutes catégories confondues, hors_perimetre inclus — cf. l'en-tête du module.\n")

    _print_scope_gate(annotated)
    _print_per_category(annotated)
    _print_confusion(annotated)

    disagreements = [r for r in annotated if r["category_system"] != r["category_gold"]]
    if disagreements:
        print("Désaccords (système → réel) :")
        for r in disagreements:
            print(f"  [{r['id']}] système={r['category_system']!r} réel={r['category_gold']!r} — {r['title'][:60]}")
    else:
        print("Aucun désaccord sur cet échantillon.")


if __name__ == "__main__":
    main()

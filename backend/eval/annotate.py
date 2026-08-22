"""Annotation manuelle de l'échantillon pour mesurer la précision de classification (§7).

Usage (terminal interactif) : python -m backend.eval.annotate
Sauvegarde après chaque item — interruptible et reprenable.

**L'annotation est aveugle par défaut** : la classification du système n'est pas montrée avant que
le jugement humain soit saisi. Elle l'était jusqu'au 2026-08-22, et c'était un biais d'ancrage sur
la mesure que ce script fonde — voir un verdict avant de juger pousse à l'accord, donc gonfle la
précision mesurée dans le sens qui arrange. Le KPI §7 étant la revendication de qualité du produit,
il doit être mesuré contre un jugement formé indépendamment. `--show-system` restaure l'ancien
comportement, pour rejouer une annotation dans les conditions d'une mesure antérieure — mais un
chiffre produit ainsi n'est pas comparable à un chiffre produit en aveugle, et ne doit pas être
présenté à côté sans le dire.
"""

import argparse
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

# Condensé des « Précisions de frontière » de docs/cadrage.md §4 — la partie normative de ce
# document, pas son journal. Rappelé ici à la demande parce que ces règles ont été écrites *après*
# des désaccords constatés en annotation : les avoir sous la main au moment de trancher est ce qui
# rend deux séances d'annotation comparables. En cas de doute, le texte de §4 fait foi.
BORDER_RULES = """
Précisions de frontière (docs/cadrage.md §4 — condensé, le texte complet fait foi)

  Fusion-acquisition / prise de participation dans la défense
    - l'opération elle-même (parties, montant, enjeu de souveraineté) ... programme_industriel
    - procédure de licence, sanction ou embargo explicite ............... export_control
    - centré sur le cours de bourse ou la réaction de marché ............ hors_perimetre

  Opinion, tribune, analyse prospective
    - ne rapporte aucun fait daté et vérifiable ......................... hors_perimetre
    - rapporte un fait daté et l'accompagne d'une analyse ............... inclus (catégorie du fait)

  diplomatie_defense vs mouvement_militaire — la confusion la plus fréquente
    Le départage porte sur le CONTENU de ce qui est déclaré, pas sur la forme de l'acte.
    - fait opérationnel accompli ou état de fait établi (force déployée,
      détroit fermé ou sous contrôle, frappe survenue) .................. mouvement_militaire
      -> y compris rapporté par un communiqué officiel : la déclaration
         est alors la source qui établit le fait, pas le sujet
    - intention, menace, capacité revendiquée, posture, coopération
      défense entre États .............................................. diplomatie_defense
    - exercice conjoint DÉJÀ ENGAGÉ (troupes déployées, manœuvres en
      cours), même en vocabulaire de coopération/interopérabilité ....... mouvement_militaire
    - accord ou intention de coopérer, aucun exercice encore engagé ..... diplomatie_defense
    « Déclarer contrôler un détroit » et « menacer de le fermer » ne sont pas le même acte.

  diplomatie_defense vs hors_perimetre
    - déclaration ou communiqué d'un responsable nommé sur la coopération,
      les alliances ou la posture défense/sécurité ...................... diplomatie_defense
      -> c'est un fait daté ; ne pas l'écarter au motif qu'aucun contrat
         ni mouvement n'est décrit
    - visite d'État, message protocolaire, pression diplomatique générale
      sans contenu défense/sécurité explicite .......................... hors_perimetre
"""


def main(show_system: bool) -> None:
    rows = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    todo = [r for r in rows if r["category_gold"] is None]

    if not todo:
        print("Tout est déjà annoté. Lance : python -m backend.eval.score")
        return

    done = len(rows) - len(todo)
    print(f"{len(todo)} items à annoter sur {len(rows)}. Ctrl+C pour arrêter, reprise automatique ensuite.")
    if show_system:
        print("/!\\ --show-system : la classification du système est affichée. Mesure ancrée, donc non")
        print("    comparable à une annotation en aveugle — le préciser en citant le chiffre.")
    else:
        print("Annotation en aveugle : la classification du système n'est pas montrée (cf. docstring).")
    print()
    print("Catégories :")
    for i, cat in enumerate(CATEGORIES, 1):
        print(f"  {i}. {cat}")
    print("\nTape 'regles' pour les précisions de frontière §4, 'lien' pour l'URL de l'article.\n")

    for offset, row in enumerate(todo, 1):
        print("=" * 80)
        print(f"[{done + offset}/{len(rows)}] [{row['id']}] {row['source']} — {row['title']}")
        print(f"\n{row['text_excerpt']}\n")
        if show_system:
            print(f"(le système a classé : {row['category_system']})")
        while True:
            choice = input("Catégorie réelle (1-6, 'regles', 'lien') : ").strip()
            if choice.lower() == "lien":
                print(row["link"])
                continue
            if choice.lower() in ("regles", "règles"):
                print(BORDER_RULES)
                continue
            if choice.isdigit() and 1 <= int(choice) <= len(CATEGORIES):
                row["category_gold"] = CATEGORIES[int(choice) - 1]
                break
            print("Entrée invalide.")

        SAMPLE_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nAnnotation terminée. Lance : python -m backend.eval.score")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--show-system",
        action="store_true",
        help="affiche la classification du système avant le jugement (ancien comportement, mesure ancrée)",
    )
    args = parser.parse_args()
    main(args.show_system)

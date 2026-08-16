"""Mesure la densité de candidats de recoupement dans l'historique analysé, sans aucun appel LLM.

Question à laquelle ce script répond : combien d'items ont, dans l'historique, au moins un voisin
qui traite du même dossier ? C'est le chiffre qui arbitre l'extension du vérificateur (docs/cadrage.md
§10, V2) — soit relever les plafonds pour scorer tous les items, soit restreindre l'escalade aux
items qui ont réellement un candidat, soit assumer une couverture partielle. Escalader un item dont
l'historique n'a rien à dire coûte 1 à 3 appels pour produire une non-réponse.

Le chevauchement est calculé avec la vraie fonction du produit (`store._tokenize`), pas avec une
copie : une mesure qui divergerait de l'implémentation mesurée ne vaudrait rien. Trois variantes
sont comparées, de la plus naïve à la plus pondérée, plus une porte sur les champs structurés déjà
extraits et vérifiés verbatim.

L'historique est lu par la couche de persistance, pas par un accès fichier direct : la mesure
fonctionne donc à l'identique sur le backend local et sur Firestore.

Usage : python -m backend.eval.candidates [--pairs N] [--days N]
"""

import argparse
import math
import re
from collections import Counter
from datetime import date, timedelta

from backend.memory.persistence import get_persistence

# Import délibéré d'un nom privé : le but est de mesurer le comportement réel de search_related(),
# pas celui d'une réimplémentation qui dériverait à la première modification de store.py.
from backend.memory.store import RELATED_ITEMS_WINDOW_DAYS, _tokenize

# Mots vides fr/en : ils passent le filtre `len > 2` du tokenizer réel et créent du chevauchement
# entre deux items qui n'ont rien en commun. Liste volontairement courte — elle sert à quantifier la
# part de bruit lexical, pas à constituer un référentiel linguistique.
STOPWORDS = frozenset(
    """les des une dans pour avec sur par que qui sont est aux cette ces son ses leur leurs plus
    mais pas non aussi entre vers sous lors selon apres après avant depuis dont ete été etre être
    avoir fait faire deux trois ans annee année annonce declare déclaré ont the and for with that
    this has have was were from its his her they their not but all new said""".split()
)


def _item_tokens(record: dict) -> set[str]:
    """Tokens d'un item côté candidat, exactement comme search_related() les calcule."""
    return _tokenize(record.get("title_fr", "")) | _tokenize(record.get("summary", ""))


def _distinctive(tokens: set[str]) -> set[str]:
    return {t for t in tokens if t not in STOPWORDS and not t.isdigit()}


def _norm(value: str) -> str:
    return re.sub(r"\W+", "", (value or "").lower())


def _report_thresholds(label: str, best: list[float], thresholds: tuple) -> None:
    total = len(best)
    print(f"--- {label} ---")
    for threshold in thresholds:
        k = sum(1 for b in best if b >= threshold)
        print(f"  seuil >= {threshold:5} : {k:4d}/{total} items escaladés ({100 * k / total:5.1f} %)")
    print()


def main(pairs_to_show: int, days: int) -> None:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    history = get_persistence().analyzed_since(cutoff)
    n = len(history)
    if n < 2:
        print(f"Historique trop court ({n} item(s)) : rien à mesurer.")
        return

    by_date = Counter(r.get("date", "?") for r in history)
    print(f"Historique : {n} items sur {len(by_date)} jours — {dict(sorted(by_date.items()))}\n")

    raw = [_item_tokens(r) for r in history]
    dist = [_distinctive(t) for t in raw]

    # IDF calculé sur l'historique lui-même : un token présent partout pèse ~0, un token rare pèse
    # le maximum. Hypothèse testée : l'identité d'un dossier tient aux tokens rares.
    df: Counter = Counter()
    for tokens in raw:
        df.update(tokens)
    idf = {tok: math.log(n / (1 + c)) for tok, c in df.items()}

    best_raw = [0] * n
    best_dist = [0] * n
    best_idf = [0.0] * n
    weighted: list[tuple[float, int, int, set[str]]] = []

    for i in range(n):
        for j in range(i + 1, n):
            # Proxy d'`exclude_links` : le lot du run en cours n'est jamais visible du recoupement.
            if history[i].get("date") == history[j].get("date"):
                continue
            shared = raw[i] & raw[j]
            if not shared:
                continue
            weight = sum(idf[t] for t in shared)
            shared_dist = len(dist[i] & dist[j])
            for idx in (i, j):
                best_raw[idx] = max(best_raw[idx], len(shared))
                best_dist[idx] = max(best_dist[idx], shared_dist)
                best_idf[idx] = max(best_idf[idx], weight)
            weighted.append((weight, i, j, shared))

    _report_thresholds("chevauchement brut (tokenizer réel)", best_raw, (1, 2, 3, 4, 5, 6, 8, 10))
    _report_thresholds("chevauchement, mots vides retirés", best_dist, (1, 2, 3, 4, 5, 6, 8, 10))
    _report_thresholds("chevauchement pondéré IDF", best_idf, (5, 10, 15, 20, 25, 30, 40))

    # Porte sur les champs structurés : `location` est extrait par le modèle puis vérifié verbatim
    # contre le texte source (docs/cadrage.md §8), donc plus fiable qu'un token de texte libre.
    located = sum(1 for r in history if _norm(r.get("location", "")))
    structured = [
        (i, j)
        for i in range(n)
        for j in range(i + 1, n)
        if history[i].get("date") != history[j].get("date")
        and _norm(history[i].get("location", ""))
        and _norm(history[i].get("location", "")) == _norm(history[j].get("location", ""))
        and history[i].get("category") == history[j].get("category")
    ]
    gated = {idx for pair in structured for idx in pair}
    print("--- porte structurée (même `location` + même catégorie) ---")
    print(f"  items avec un `location` non vide : {located}/{n} ({100 * located / n:.0f} %)")
    print(f"  paires retenues : {len(structured)}")
    print(f"  items escaladés : {len(gated)}/{n} ({100 * len(gated) / n:.1f} %)\n")

    # Contrôle qualitatif — indispensable : un taux d'escalade ne vaut rien si les candidats retenus
    # ne sont pas de vrais candidats. C'est ici qu'on lit si le classement remonte l'identité de
    # dossier ou seulement la similarité de thème.
    if pairs_to_show:
        weighted.sort(key=lambda p: p[0], reverse=True)
        print(f"=== {pairs_to_show} meilleures paires (pondération IDF) — à juger à la main ===\n")
        for weight, i, j, shared in weighted[:pairs_to_show]:
            a, b = history[i], history[j]
            rarest = sorted(shared, key=lambda t: -idf[t])[:6]
            print(f"[{weight:5.1f}] {a.get('category')} / {b.get('category')}")
            print(f"   A ({a.get('source')}, {a.get('date')}) : {a.get('title_fr', '')[:100]}")
            print(f"   B ({b.get('source')}, {b.get('date')}) : {b.get('title_fr', '')[:100]}")
            print(f"   tokens les plus rares partagés : {rarest}")
            print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=int, default=12, help="paires à afficher pour jugement manuel")
    parser.add_argument("--days", type=int, default=RELATED_ITEMS_WINDOW_DAYS, help="fenêtre d'historique")
    args = parser.parse_args()
    main(args.pairs, args.days)

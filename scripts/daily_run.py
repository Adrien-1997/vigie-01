"""Lancement quotidien du pipeline pendant la campagne d'accumulation d'historique.

**Intention.** L'arbitrage sur l'extension du vérificateur (docs/cadrage.md §10, V2) et la première
tranche de la V3 (fils d'événements) dépendent tous deux d'une question qu'on ne sait pas encore
trancher : combien d'items ont réellement un voisin portant sur le même dossier ? La mesure a été
tentée sur 3 jours d'historique (`python -m backend.eval.candidates`) et a conclu que l'assiette
était trop mince — 2 à 4 appariements réels sur 102 items, trop peu pour calibrer ou valider un
seuil. Deux dépêches sur le même dossier à 48 h d'écart sont rares par construction. Il faut donc
une quinzaine de jours d'historique continu avant de rejouer la mesure et de décider.

Ce script est l'outil de cette campagne : un lancement par jour, à la main, jusqu'à ce que
l'assiette soit suffisante. Il n'a pas vocation à survivre à la campagne — en production, le
déclenchement passe par Cloud Scheduler → Cloud Run (cf. backend/api/main.py).

**Pourquoi un journal, et pourquoi il ne se déduit pas de l'historique analysé.** Un jour sans item
neuf (tout écarté par le dédoublonnage) et un jour où le lancement a été oublié laissent exactement
la même trace dans `.analyzed_history.json` : aucune. Le premier est une mesure — le flux n'a rien
publié de neuf dans le périmètre —, le second est un trou. Les confondre fausserait la relecture de
la campagne au moment de décider : un historique clairsemé parce que le corpus est pauvre n'appelle
pas la même conclusion qu'un historique clairsemé parce que l'opérateur a sauté quatre jours. Le
journal enregistre donc *tout lancement*, y compris ceux qui ne produisent rien et ceux qui échouent.

**Fenêtre de collecte et trous irrécupérables.** `COLLECTION_LOOKBACK_HOURS` (96 h depuis le
2026-08-17 ; 48 h à l'origine, relevé une fois le coût couvert par un plafond par source plutôt
que par le temps — cf. backend/config.py) borne ce qu'une collecte peut rattraper. Un jour sauté
est donc récupéré par le lancement suivant ; des jours consécutifs sautés au-delà de cette fenêtre
perdent définitivement les items publiés dans l'intervalle non couvert. Le script mesure l'écart
depuis le dernier lancement journalisé et le signale — l'information n'est utile qu'au moment où
elle est constatée, et elle doit rester attachée au run dans le journal.

**Pourquoi le journal ne passe pas par backend/memory/persistence.py.** L'invariant du projet
(CLAUDE.md) est que tout *état métier* survivant à un run passe par la couche de persistance. Ce
journal n'est pas de l'état métier : il ne décrit pas le produit mais l'exploitation qu'on en fait,
il n'est lu par aucun nœud du pipeline, il ne part pas en production, et il doit rester lisible même
si la persistance est justement ce qui a échoué. Un fichier local assumé, hors de l'abstraction.

Usage :
    python -m scripts.daily_run              # le lancement quotidien
    python -m scripts.daily_run --dry-run    # état de la campagne, sans lancer le pipeline
"""

import argparse
import json
import time
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from backend.agents.collector import source_freshness
from backend.config import COLLECTION_LOOKBACK_HOURS, MAX_LLM_CALLS_PER_DAY, SOURCES
from backend.graph import run_pipeline
from backend.guardrails import remaining_calls_today
from backend.memory.persistence import get_persistence
from backend.memory.store import RELATED_ITEMS_WINDOW_DAYS

# JSONL plutôt que JSON : un lancement n'a qu'à ajouter une ligne, sans relire ni réécrire le
# fichier — un plantage en cours d'écriture ne peut pas corrompre les lancements déjà journalisés.
LOG_FILE = Path(__file__).resolve().parent / ".run_log.jsonl"


def _s(count: int) -> str:
    """Marque du pluriel — l'interface du produit est en français, ses sorties d'exploitation aussi."""
    return "s" if count > 1 else ""


def _read_log() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    entries = []
    for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def _append_log(entry: dict) -> None:
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _history_shape() -> tuple[int, dict[str, int]]:
    """Taille et répartition par jour de l'historique analysé, dans la fenêtre de rétention.

    Lu par la couche de persistance, comme backend/eval/candidates.py : la campagne doit se relire
    à l'identique si le stockage passe sur Firestore.
    """
    cutoff = (date.today() - timedelta(days=RELATED_ITEMS_WINDOW_DAYS)).isoformat()
    records = get_persistence().analyzed_since(cutoff)
    return len(records), dict(sorted(Counter(r.get("date", "?") for r in records).items()))


def _hours_since_last(entries: list[dict]) -> float | None:
    for entry in reversed(entries):
        started = entry.get("started_at")
        if started:
            return (datetime.now(UTC) - datetime.fromisoformat(started)).total_seconds() / 3600
    return None


def _print_campaign(entries: list[dict]) -> None:
    if not entries:
        print("\nCampagne : aucun lancement journalisé pour l'instant.")
        return
    days = {e["started_at"][:10] for e in entries if e.get("started_at")}
    failed = sum(1 for e in entries if e.get("error"))
    truncated = sum(1 for e in entries if e.get("truncated"))
    holes = sum(1 for e in entries if e.get("lookback_exceeded"))
    first = min(days) if days else "?"
    print(
        f"\nCampagne depuis le {first} : {len(entries)} lancement{_s(len(entries))} "
        f"sur {len(days)} jour{_s(len(days))} distinct{_s(len(days))} — "
        f"échecs : {failed}, tronqués par le budget : {truncated}, "
        f"trous au-delà de {COLLECTION_LOOKBACK_HOURS} h : {holes}."
    )
    print(f"Journal : {LOG_FILE}")


def main(dry_run: bool) -> int:
    entries = _read_log()
    gap_hours = _hours_since_last(entries)
    remaining_before = remaining_calls_today()
    history_before, by_date_before = _history_shape()

    print(f"Budget : {remaining_before}/{MAX_LLM_CALLS_PER_DAY} appels restants aujourd'hui.")
    print(
        f"Historique : {history_before} item{_s(history_before)} "
        f"sur {len(by_date_before)} jour{_s(len(by_date_before))} — {by_date_before}"
    )

    # « Active » veut dire « a produit un item récent », pas « le flux se parse sans erreur » —
    # un flux mort (OFAC, ~1 an sans nouvelle entrée avant d'être détecté par ce constat) passait
    # inaperçu du KPI de couverture (docs/cadrage.md §7) tant que le test était le second. Lecture
    # RSS seule, aucun coût de budget.
    freshness = source_freshness()
    silent = sorted(name for name, count in freshness.items() if count == 0)
    active_count = len(SOURCES) - len(silent)
    print(f"Couverture : {active_count}/{len(SOURCES)} sources actives dans les {COLLECTION_LOOKBACK_HOURS} h.")
    if silent:
        print(f"  Silencieuse{_s(len(silent))} : {', '.join(silent)}")

    if gap_hours is None:
        print("Aucun lancement journalisé auparavant : début de campagne.")
    else:
        print(f"Dernier lancement il y a {gap_hours:.1f} h.")
        if gap_hours > COLLECTION_LOOKBACK_HOURS:
            print(
                f"  /!\\ Au-delà de la fenêtre de collecte ({COLLECTION_LOOKBACK_HOURS} h) : les items "
                "publiés dans l'intervalle non couvert sont définitivement perdus. Trou à retenir en "
                "relisant la campagne — l'historique seul ne le montrera pas."
            )

    # ~110 items/jour à ~1 appel chacun : sous ce seuil le run sera tronqué. Ce n'est pas une erreur
    # (le run reste un succès partiel, cf. docs/cadrage.md §8) mais ça se sait avant, pas après.
    if remaining_before < 110:
        print("  Budget insuffisant pour un lot complet : le run sera probablement tronqué.")

    if dry_run:
        print("\n--dry-run : pipeline non lancé.")
        _print_campaign(entries)
        return 0

    started = datetime.now(UTC)
    clock = time.monotonic()
    analyzed, truncated, error = 0, False, None
    try:
        result = run_pipeline()
        analyzed = len(result["analyzed_items"])
        truncated = result["truncated"]
    except Exception as exc:  # noqa: BLE001 — voir ci-dessous
        # Rattrapage volontairement large : un échec non journalisé est précisément le trou que ce
        # journal existe pour éviter. L'exception est enregistrée puis rendue par le code de sortie.
        error = f"{type(exc).__name__}: {exc}"

    duration = time.monotonic() - clock
    remaining_after = remaining_calls_today()
    history_after, by_date_after = _history_shape()

    # Le compteur de budget est quotidien : un run à cheval sur minuit repart du plafond plein et la
    # différence n'a plus de sens. Ne rien affirmer vaut mieux qu'un chiffre faux.
    consumed = remaining_before - remaining_after
    llm_calls = consumed if consumed >= 0 else None

    entry = {
        "started_at": started.isoformat(),
        "duration_s": round(duration, 1),
        "analyzed": analyzed,
        "truncated": truncated,
        "llm_calls": llm_calls,
        "history_before": history_before,
        "history_after": history_after,
        "history_by_date": by_date_after,
        "gap_hours": round(gap_hours, 1) if gap_hours is not None else None,
        "lookback_exceeded": gap_hours is not None and gap_hours > COLLECTION_LOOKBACK_HOURS,
        "sources_active": active_count,
        "sources_targeted": len(SOURCES),
        "sources_silent": silent,
        "error": error,
    }
    _append_log(entry)

    print()
    if error:
        print(f"ÉCHEC après {duration:.0f} s : {error}")
    else:
        print(
            f"Run terminé en {duration:.0f} s — {analyzed} item{_s(analyzed)} retenu{_s(analyzed)}"
            f"{', run tronqué par le budget' if truncated else ''}."
        )
    print(
        f"Historique : {history_before} → {history_after} item{_s(history_after)} "
        f"sur {len(by_date_after)} jour{_s(len(by_date_after))}."
    )
    print(f"Appels LLM consommés : {llm_calls if llm_calls is not None else 'indéterminé (jour changé)'}.")
    _print_campaign(entries + [entry])

    return 1 if error else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="affiche l'état de la campagne et sort, sans lancer le pipeline ni consommer de budget",
    )
    args = parser.parse_args()
    raise SystemExit(main(args.dry_run))

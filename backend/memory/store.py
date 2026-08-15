"""Nœud mémoire : dédoublonnage court terme (README architecture, docs/cadrage.md §10 V1) et
historique des items analysés — qui sert à la fois au recoupement de l'agent vérificateur (§10 V2,
cf. backend/agents/verifier.py) et au digest servi par l'API.

Un seul historique pour ces deux usages, volontairement. La version précédente en tenait deux : cet
historique d'un côté, et un fichier `.digest.json` réécrit à chaque run de l'autre. Ce second
fichier ne contenait que les items du run courant — or le dédoublonnage écarte, avant l'appel LLM,
tout ce qui a déjà été vu dans les 7 derniers jours. Conséquence : un second run dans la même
journée ne produisait qu'une poignée d'items neufs et écrasait le digest précédent, qui était perdu
pour l'affichage alors même que les items restaient présents ici. Le digest est donc désormais une
fenêtre glissante sur cet historique (`load_digest`), pas la photographie du dernier run.

Le stockage (fichiers locaux en dev, Firestore en production) est derrière
backend/memory/persistence.py.
"""

import re
from datetime import UTC, date, datetime, timedelta

from backend.state import AnalyzedItem, RawItem, VeilleState

from .persistence import get_persistence

DEDUP_WINDOW_DAYS = 7

# Plus long que DEDUP_WINDOW_DAYS : le recoupement (a-t-on déjà vu ce dossier ?) bénéficie de plus
# d'historique que le simple dédoublonnage d'items identiques. Borne aussi la profondeur maximale
# consultable du digest (cf. backend/api/main.py).
RELATED_ITEMS_WINDOW_DAYS = 30


def _cutoff(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


def deduplicate(state: VeilleState) -> VeilleState:
    """Nœud LangGraph : retire les raw_items déjà vus (clé = link), avant l'appel LLM de l'analyste.

    Placé entre collect et analyze plutôt qu'après analyze : un item déjà vu ne doit pas seulement
    être exclu du digest, il ne doit même pas être ré-analysé — sinon le budget LLM (§8) est
    consommé chaque jour sur des items déjà traités la veille.
    """
    persistence = get_persistence()
    # Une fois par run, en début de pipeline : sans purge explicite, les backends qui filtrent à la
    # lecture (Firestore) conserveraient indéfiniment des données hors fenêtre de rétention.
    persistence.purge_before(_cutoff(DEDUP_WINDOW_DAYS), _cutoff(RELATED_ITEMS_WINDOW_DAYS))

    seen = persistence.seen_links(_cutoff(DEDUP_WINDOW_DAYS))

    new_items: list[RawItem] = []
    kept: set[str] = set()
    for item in state["raw_items"]:
        if item["link"] in seen or item["link"] in kept:
            continue
        new_items.append(item)
        kept.add(item["link"])

    # Ce nœud filtre, il ne marque pas : c'est mark_analyzed_as_seen(), appelé par le nœud analyze,
    # qui inscrit les liens une fois l'item réellement soumis au modèle. Marquer ici perdait
    # définitivement les items d'un run interrompu entre les deux — ils étaient réputés vus sans
    # avoir jamais été analysés, donc écartés de toutes les collectes suivantes. Constaté en réel :
    # une réponse de modèle non validable a fait échouer un run, et ses 12 items sont restés vus
    # sans exister nulle part.
    return {"raw_items": new_items}


def mark_analyzed_as_seen(items: list[RawItem]) -> None:
    """Inscrit les liens soumis à l'analyste dans la mémoire de dédoublonnage.

    Porte sur tous les items soumis, pas seulement sur ceux retenus : un item écarté en
    `hors_perimetre` ou faute de citation vérifiable a déjà coûté son appel LLM, et doit être
    écarté sans frais lors des collectes suivantes.
    """
    if not items:
        return
    today = date.today().isoformat()
    get_persistence().mark_seen({item["link"]: today for item in items})


def record_analyzed(items: list[AnalyzedItem]) -> None:
    """Écrit les items analysés du run courant dans l'historique (recoupement §10 V2 + digest).

    Appelé en fin de nœud verify, une fois `confidence_score`/`corroborated` renseignés : l'historique
    doit porter l'item tel qu'il sera affiché, pas sa version pré-vérification. L'invariant « la
    recherche de recoupement ne voit jamais le run courant » est tenu par `exclude_links` côté
    verifier, pas par l'ordre d'écriture.

    `first_seen` est conservé lors d'une réécriture : un item ré-analysé ne doit pas rajeunir, sinon
    il ne sortirait jamais de la fenêtre de rétention.
    """
    if not items:
        return

    persistence = get_persistence()
    today = date.today().isoformat()
    now = datetime.now(UTC).isoformat()
    known = {r["link"]: r for r in persistence.analyzed_since(_cutoff(RELATED_ITEMS_WINDOW_DAYS))}

    persistence.put_analyzed(
        [
            {
                **item,
                "date": known.get(item["link"], {}).get("date", today),
                "first_seen": known.get(item["link"], {}).get("first_seen", now),
            }
            for item in items
        ]
    )


# Champs sans lesquels le front ne peut pas rendre une carte d'item. Avant la fusion des deux
# stores, l'historique ne conservait que 7 champs par item (assez pour le recoupement, pas pour
# l'affichage) : ces enregistrements-la restent interrogeables par le vérificateur mais sont
# écartés du digest plutôt que servis incomplets. Ils sortiront d'eux-mêmes de la rétention.
_DISPLAY_FIELDS = ("title", "citation", "location", "published", "lang")


def _is_displayable(record: dict) -> bool:
    return all(field in record for field in _DISPLAY_FIELDS)


def load_digest(days: int) -> list[dict]:
    """Items analysés des `days` derniers jours, les plus récents d'abord.

    C'est ce que sert GET /events. Les items conservent `date`/`first_seen` : le front en a besoin
    pour dater l'entrée dans le digest, qui n'est pas la date de publication de l'article.
    """
    records = [r for r in get_persistence().analyzed_since(_cutoff(days)) if _is_displayable(r)]
    records.sort(key=lambda r: (r.get("first_seen", ""), r.get("published", "")), reverse=True)
    return records


def last_run_at(records: list[dict]) -> str | None:
    """Horodatage de l'entrée la plus récente du digest — donc de la dernière collecte ayant produit
    quelque chose. Dérivé des items plutôt que stocké à part : un compteur séparé pourrait diverger
    de ce qui est réellement affiché."""
    stamps = [r["first_seen"] for r in records if r.get("first_seen")]
    return max(stamps) if stamps else None


def _tokenize(text: str) -> set[str]:
    return {tok for tok in re.findall(r"\w+", text.lower()) if len(tok) > 2}


def search_related(query: str, exclude_links: set[str], limit: int = 5) -> list[dict]:
    """Recherche naïve par chevauchement de mots-clés dans l'historique (§10 V2, backend/agents/verifier.py).

    Pas d'embeddings/vector store : cohérent avec la convention « stockage fichier local comme
    placeholder documenté avant Firestore » qui a présidé à ce module.

    `exclude_links` porte tous les liens du run en cours, pas seulement celui de l'item vérifié :
    un item ne doit pas être « corroboré » par un autre item du même lot, qui n'apporte aucune
    confirmation indépendante dans le temps.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scored: list[tuple[int, dict]] = []
    for record in get_persistence().analyzed_since(_cutoff(RELATED_ITEMS_WINDOW_DAYS)):
        if record["link"] in exclude_links:
            continue
        record_tokens = _tokenize(record.get("title_fr", "")) | _tokenize(record.get("summary", ""))
        score = len(query_tokens & record_tokens)
        if score > 0:
            scored.append((score, record))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [
        {
            "date": record["date"],
            "source": record["source"],
            "country": record.get("country", ""),
            "category": record["category"],
            "title_fr": record["title_fr"],
        }
        for _, record in scored[:limit]
    ]

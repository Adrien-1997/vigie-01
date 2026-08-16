"""Schéma d'état partagé du graphe LangGraph (VeilleState, cf. README)."""

from typing import Literal, TypedDict

# Catégories du périmètre MECE (cf. docs/cadrage.md §4) + hors_perimetre pour les items
# des flux sources qui sortent du périmètre restreint (ex. actualité tech générale, cyber).
Category = Literal[
    "export_control",
    "contrat_armement",
    "mouvement_militaire",
    "diplomatie_defense",
    "programme_industriel",
    "hors_perimetre",
]


class RawItem(TypedDict):
    source: str
    theme: str
    lang: str
    country: str  # code pays de la source (cf. backend/config.py), pas de l'article
    state_affiliated: bool  # média d'État ou lié à un service officiel (cf. backend/config.py)
    title: str
    link: str
    published: str  # ISO 8601 si fourni par le flux, chaîne vide sinon
    raw_text: str


class AnalyzedItem(TypedDict):
    source: str
    lang: str
    country: str
    state_affiliated: bool
    title: str  # titre original, dans la langue de la source
    title_fr: str  # titre traduit, pour un digest lisible en français quelle que soit la source
    link: str
    published: str
    category: Category
    summary: str
    citation: str  # extrait vérifié du texte source, langue d'origine (garde-fou §8 : verbatim = non traduisible)
    location: str  # pays/lieu vérifié, métadonnée pour la carte V2 (§4) ; ne filtre pas la collecte
    # Pays déduit du lieu ci-dessus, nom anglais. Seul champ non vérifiable verbatim (le pays d'une
    # ville n'est pas dans le texte) : vide dès que location l'est, et validé contre le référentiel
    # de la carte à l'affichage, où il est signalé comme déduit et non comme cité.
    location_country: str
    # Vrai uniquement si aucun lieu n'a été extrait ET que le modèle juge, sur le contenu, que
    # l'événement se situe dans le pays de la source (champ `country` ci-dessus). Rattachement
    # présumé, plus faible que location_country : distingué comme tel à l'affichage.
    domestic_to_source: bool
    # Renseignés par le vérificateur en V2 (cf. docs/cadrage.md §10) ; absents en V1.
    confidence_score: float | None
    corroborated: bool | None


class VeilleState(TypedDict):
    raw_items: list[RawItem]
    analyzed_items: list[AnalyzedItem]
    # Vrai si le plafond quotidien d'appels LLM (backend/guardrails.py) a arrêté le run avant la fin
    # du lot. Le run reste un succès partiel : les items déjà analysés sont conservés et servis, et
    # ce drapeau dit à l'appelant que le lot n'a pas été traité en entier — sans lui, une collecte
    # tronquée serait indiscernable d'une collecte complète pauvre en nouveautés.
    truncated: bool

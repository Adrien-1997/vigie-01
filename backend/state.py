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
    title: str
    link: str
    published: str  # ISO 8601 si fourni par le flux, chaîne vide sinon
    raw_text: str


class AnalyzedItem(TypedDict):
    source: str
    lang: str
    title: str  # titre original, dans la langue de la source
    title_fr: str  # titre traduit, pour un digest lisible en français quelle que soit la source
    link: str
    published: str
    category: Category
    summary: str
    citation: str  # extrait vérifié du texte source, langue d'origine (garde-fou §8 : verbatim = non traduisible)
    location: str  # pays/lieu vérifié, métadonnée pour la carte V2 (§4) ; ne filtre pas la collecte
    # Renseignés par le vérificateur en V2 (cf. docs/cadrage.md §10) ; absents en V1.
    confidence_score: float | None
    corroborated: bool | None


class VeilleState(TypedDict):
    raw_items: list[RawItem]
    analyzed_items: list[AnalyzedItem]

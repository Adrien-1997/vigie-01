"""Nœud analyste : classification + résumé tracé (cf. docs/cadrage.md §2 et §8)."""

import html
import re

from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from backend.guardrails import check_and_increment_llm_call
from backend.state import AnalyzedItem, Category, RawItem, VeilleState

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """Tu es un analyste de veille défense/géopolitique. Pour l'article fourni :
1. Classe-le dans une des catégories : export_control, contrat_armement, mouvement_militaire,
   diplomatie_defense, programme_industriel, ou hors_perimetre si l'article ne relève d'aucune
   de ces catégories (ex. actualité technologique générale, cybersécurité, analyse financière).
   Le filtrage est thématique uniquement — la localisation géographique de l'article n'entre pas
   en compte dans ce choix. Deux précisions de frontière :
   - Fusion-acquisition ou prise de participation dans l'industrie de défense : classe en
     programme_industriel si l'article porte sur l'opération elle-même (parties, montant, enjeu
     stratégique) ; en export_control seulement si l'article traite explicitement d'une licence,
     sanction ou embargo ; en hors_perimetre si l'article est centré sur l'analyse boursière (cours,
     réaction de marché) plutôt que sur l'opération.
   - Contenu d'opinion, tribune ou analyse prospective qui ne rapporte pas un fait ou événement daté
     et vérifiable : classe en hors_perimetre même si le thème correspond au périmètre. Un article
     qui rapporte un fait daté puis l'accompagne d'analyse reste inclus ; une simple prise de
     position n'est pas incluse.
2. Traduis le titre en français (title_fr), fidèlement, même si le titre original est déjà en français.
3. Rédige un résumé factuel en français, 2-3 phrases maximum, sans interprétation ni spéculation.
4. Fournis une citation : un extrait VERBATIM du texte source, dans sa langue d'origine (copié-collé
   exact, jamais traduit) qui justifie le résumé. Si aucun extrait ne justifie clairement le résumé,
   catégorise en hors_perimetre et laisse la citation vide.
5. Fournis location : le pays, la mer ou la région principale concernée par l'article, extrait
   VERBATIM du texte source. Laisse vide si aucun lieu n'est explicitement nommé dans le texte —
   ne déduis jamais un lieu qui n'est pas écrit noir sur blanc."""


class _Analysis(BaseModel):
    category: Category = Field(description="Catégorie du périmètre MECE ou hors_perimetre (thématique uniquement)")
    title_fr: str = Field(description="Titre traduit en français, fidèle au titre original")
    summary: str = Field(description="Résumé factuel en français, 2-3 phrases maximum")
    citation: str = Field(description="Extrait verbatim du texte source, langue d'origine, justifiant le résumé")
    location: str = Field(
        description="Extrait verbatim nommant le pays/lieu principal de l'article ; vide si non mentionné"
    )


def _clean_text(raw_html: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", raw_html)).strip()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _extract_verified(extract: str, source_text: str) -> bool:
    """Vérifie qu'un extrait (citation ou zone_evidence) est bien un verbatim du texte source."""
    return bool(extract.strip()) and _normalize(extract) in _normalize(source_text)


_llm = None


def classify_item(item: RawItem) -> _Analysis:
    """Appelle le LLM pour un item, sans filtrage. Réutilisé par analyze() et par l'éval (backend/eval/)."""
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(model=MODEL, temperature=0).with_structured_output(_Analysis)

    clean_text = _clean_text(item["raw_text"])
    check_and_increment_llm_call()
    return _llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", f"Titre : {item['title']}\n\nTexte : {clean_text}"),
        ]
    )


def analyze(state: VeilleState) -> VeilleState:
    """Nœud LangGraph : classe et résume chaque raw_item, rejette les résumés non tracés."""
    analyzed_items: list[AnalyzedItem] = []
    for item in state["raw_items"]:
        result = classify_item(item)
        clean_text = _clean_text(item["raw_text"])

        if result.category == "hors_perimetre":
            continue
        if not _extract_verified(result.citation, clean_text):
            # Garde-fou traçabilité (docs/cadrage.md §8) : pas de citation vérifiable, pas de résumé.
            continue

        # location est une métadonnée pour la carte future (docs/cadrage.md §4) : ne filtre pas la
        # collecte (pas de restriction géographique en V1), mais reste soumise au même garde-fou de
        # traçabilité que la citation — pas de lieu inventé, vide plutôt que non vérifiable.
        location = result.location if _extract_verified(result.location, clean_text) else ""

        analyzed_items.append(
            AnalyzedItem(
                source=item["source"],
                lang=item["lang"],
                country=item["country"],
                state_affiliated=item["state_affiliated"],
                title=item["title"],
                title_fr=result.title_fr,
                link=item["link"],
                published=item["published"],
                category=result.category,
                summary=result.summary,
                citation=result.citation,
                location=location,
                confidence_score=None,
                corroborated=None,
            )
        )

    return {"analyzed_items": analyzed_items}

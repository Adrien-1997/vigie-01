"""Nœud vérificateur : recoupement et score de confiance pour les items à catégorie sensible
(première tranche de docs/cadrage.md §10 V2 — cf. backend/memory/store.py pour l'historique de
recoupement). Contrairement à analyze(), ce nœud a une vraie boucle agentique bornée : le LLM
décide lui-même s'il cherche du contexte supplémentaire avant de conclure.
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from backend.config import MAX_VERIFIER_ESCALATIONS_PER_RUN, MAX_VERIFIER_STEPS_PER_ITEM, VERIFIER_CATEGORIES
from backend.guardrails import check_and_increment_llm_call
from backend.memory.store import record_analyzed, search_related
from backend.state import AnalyzedItem, VeilleState

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """Tu es un vérificateur de veille défense/géopolitique. On te donne un item déjà
classifié et résumé. Ta tâche : évaluer sa fiabilité en cherchant si des items précédents
corroborent ce dossier.

Utilise l'outil search_related_items pour chercher des items déjà analysés sur le même sujet
(entreprises, pays, type de contrat/mouvement mentionnés dans le résumé). Tu peux l'appeler
plusieurs fois avec des requêtes différentes si la première ne donne rien d'utile, mais n'insiste
pas si les résultats ne sont manifestement pas liés.

Une fois ta recherche terminée (ou si tu juges qu'aucune recherche supplémentaire n'aiderait),
conclus avec un score de confiance (0 à 1) et un booléen corroborated :
- corroborated=True si au moins un item précédent traite clairement du même dossier (même contrat,
  même mouvement, mêmes parties) — pas juste le même thème général.
- Le score de confiance reflète ta confiance globale dans le résumé, pas seulement la corroboration :
  un item non corroboré mais dont la citation est claire et non ambiguë peut avoir un score correct
  (ex. 0.6-0.7) ; un item corroboré par plusieurs sources indépendantes mérite un score élevé
  (0.85+) ; un item isolé avec un résumé qui laisse place à interprétation mérite un score plus bas."""


class _VerifierResult(BaseModel):
    confidence_score: float = Field(description="Score de confiance global, entre 0 et 1")
    corroborated: bool = Field(description="Au moins un item précédent traite clairement du même dossier")


def _make_search_tool(exclude_links: set[str]):
    @tool
    def search_related_items(query: str) -> str:
        """Cherche dans l'historique des items déjà analysés (jusqu'à 30 jours) ceux qui pourraient
        corroborer ou apporter du contexte sur le dossier en cours. `query` : mots-clés pertinents
        (ex. noms d'entreprises, de pays, type de contrat)."""
        results = search_related(query, exclude_links=exclude_links, limit=5)
        if not results:
            return "Aucun item correspondant trouvé dans l'historique."
        return "\n".join(
            f"- [{r['date']}] {r['country']}/{r['category']} : {r['title_fr']} (source : {r['source']})"
            for r in results
        )

    return search_related_items


def _verify_item(item: AnalyzedItem, exclude_links: set[str]) -> tuple[float, bool]:
    """Boucle agentique bornée par MAX_VERIFIER_STEPS_PER_ITEM. Chaque appel LLM (décision d'outil
    ou conclusion) passe par check_and_increment_llm_call() — le plafond quotidien existant
    (MAX_LLM_CALLS_PER_DAY) absorbe donc aussi ce nœud sans garde-fou séparé."""
    search_tool = _make_search_tool(exclude_links)
    llm = ChatAnthropic(model=MODEL, temperature=0).bind_tools([search_tool])

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Catégorie : {item['category']}\n"
                f"Résumé : {item['summary']}\n"
                f"Citation : {item['citation']}\n"
                f"Pays/lieu : {item['location']}"
            )
        ),
    ]

    for _ in range(MAX_VERIFIER_STEPS_PER_ITEM):
        check_and_increment_llm_call()
        response = llm.invoke(messages)
        if not response.tool_calls:
            break
        messages.append(response)
        for call in response.tool_calls:
            result = search_tool.invoke(call["args"])
            messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

    check_and_increment_llm_call()
    concluder = ChatAnthropic(model=MODEL, temperature=0).with_structured_output(_VerifierResult)
    messages.append(HumanMessage(content="Conclus maintenant avec ton score de confiance et corroborated."))
    conclusion = concluder.invoke(messages)
    return conclusion.confidence_score, conclusion.corroborated


def verify(state: VeilleState) -> VeilleState:
    """Nœud LangGraph : ajoute confidence_score/corroborated pour les items dont la catégorie est
    dans VERIFIER_CATEGORIES, plafonné à MAX_VERIFIER_ESCALATIONS_PER_RUN par run. Les autres items
    (hors catégorie ou au-delà du plafond) gardent confidence_score/corroborated à None — pas de
    score fabriqué sans base réelle.

    L'historique est écrit deux fois, et c'est voulu. Une première fois avant l'escalade : ce nœud
    fait des appels réseau, et une panne à mi-parcours ne doit pas faire perdre des items déjà
    analysés et payés. Une seconde fois après, pour que l'historique porte les items tels qu'ils
    seront affichés, scores compris — il alimente aussi le digest servi par l'API
    (cf. store.load_digest). L'écriture est un upsert par lien qui préserve la date de première
    vue : la seconde passe met à jour, elle ne duplique pas.

    L'invariant « search_related_items ne voit jamais le run en cours, seulement l'historique des
    runs précédents » ne repose donc pas sur l'ordre d'écriture mais sur `exclude_links`, qui porte
    tous les liens du lot — deux items du même run ne se corroborent pas mutuellement.
    """
    current_links = {item["link"] for item in state["analyzed_items"]}
    record_analyzed(state["analyzed_items"])

    escalated = 0
    updated_items: list[AnalyzedItem] = []
    for item in state["analyzed_items"]:
        if item["category"] in VERIFIER_CATEGORIES and escalated < MAX_VERIFIER_ESCALATIONS_PER_RUN:
            escalated += 1
            confidence_score, corroborated = _verify_item(item, current_links)
            updated_items.append({**item, "confidence_score": confidence_score, "corroborated": corroborated})
        else:
            updated_items.append(item)

    record_analyzed(updated_items)
    return {"analyzed_items": updated_items}

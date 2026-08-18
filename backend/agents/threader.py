"""Nœud thread : regroupe les items qui couvrent le même dossier en fils chronologiques (V3
tranche 1, cf. docs/cadrage.md §10). Même patron que le vérificateur (backend/agents/verifier.py) :
boucle agentique bornée, un outil de recherche que le LLM décide lui-même d'appeler avant de
conclure.

Deux différences volontaires par rapport au vérificateur :

- Pas de filtre par catégorie : hors_perimetre n'atteint jamais analyzed_items
  (backend/agents/analyst.py l'écarte avant construction), donc tout item qui arrive jusqu'ici est
  déjà éligible à être rattaché à un dossier — VERIFIER_CATEGORIES ne couvre que 2 des 6 catégories
  parce que le recoupement V2 vise spécifiquement le risque juridique, restriction sans objet ici.
- Pas d'exclusion des items du run en cours : la corroboration du vérificateur exige une
  confirmation indépendante dans le temps (backend/memory/store.py, docstring de search_related),
  alors que deux sources qui couvrent le même événement le même jour sont au contraire le cas le
  plus net de « même dossier ».
"""

import uuid

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from backend.config import MAX_THREAD_ESCALATIONS_PER_RUN, MAX_THREAD_STEPS_PER_ITEM
from backend.guardrails import BudgetExceeded, check_and_increment_llm_call
from backend.memory.store import analyzed_window, record_analyzed, search_thread_candidates
from backend.state import AnalyzedItem, VeilleState

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """Tu es un analyste de veille défense/géopolitique. On te donne un item déjà
classifié et résumé. Ta tâche : déterminer s'il couvre le même dossier qu'un item déjà analysé —
mêmes parties, même opération, même contrat — pas seulement le même thème général ou le même pays.

Utilise l'outil find_thread_candidates pour chercher des items déjà analysés qui pourraient porter
sur le même dossier (entreprises, pays, type de contrat/mouvement mentionnés dans le résumé). Tu
peux l'appeler plusieurs fois avec des requêtes différentes si la première ne donne rien d'utile,
mais n'insiste pas si les résultats ne sont manifestement pas liés.

Une fois ta recherche terminée (ou si tu juges qu'aucune recherche supplémentaire n'aiderait),
conclus avec same_story_as : le lien exact d'un des candidats retournés par l'outil si l'un d'eux
couvre clairement le même dossier, ou null sinon. Un thème ou un pays commun ne suffit pas."""


class _ThreadDecision(BaseModel):
    same_story_as: str | None = Field(
        description="Lien exact du candidat qui couvre le même dossier, ou null si aucun ne correspond"
    )


def _make_thread_tool(current_link: str):
    @tool
    def find_thread_candidates(query: str) -> str:
        """Cherche dans l'historique des items déjà analysés (jusqu'à 30 jours, y compris le run en
        cours) ceux qui pourraient couvrir le même dossier. `query` : mots-clés pertinents (ex. noms
        d'entreprises, de pays, type de contrat)."""
        results = search_thread_candidates(query, exclude_link=current_link, limit=5)
        if not results:
            return "Aucun item correspondant trouvé dans l'historique."
        return "\n".join(
            f"- [{r['date']}] {r['country']}/{r['category']} : {r['title_fr']} "
            f"(source : {r['source']}, lien : {r['link']})"
            for r in results
        )

    return find_thread_candidates


def _thread_item(item: AnalyzedItem) -> str | None:
    """Boucle agentique bornée par MAX_THREAD_STEPS_PER_ITEM, même structure que
    verifier._verify_item. Retourne le lien du candidat jugé même dossier, ou None."""
    search_tool = _make_thread_tool(item["link"])
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

    for _ in range(MAX_THREAD_STEPS_PER_ITEM):
        check_and_increment_llm_call()
        response = llm.invoke(messages)
        if not response.tool_calls:
            break
        messages.append(response)
        for call in response.tool_calls:
            result = search_tool.invoke(call["args"])
            messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

    check_and_increment_llm_call()
    concluder = ChatAnthropic(model=MODEL, temperature=0).with_structured_output(_ThreadDecision)
    messages.append(HumanMessage(content="Conclus maintenant avec same_story_as."))
    conclusion = concluder.invoke(messages)
    return conclusion.same_story_as


def thread_events(state: VeilleState) -> VeilleState:
    """Nœud LangGraph : rattache chaque item à un thread_id partagé avec les items du même dossier.

    Filtre gratuit avant escalade, sans seuil à calibrer (cf. docs/cadrage.md §10 et
    backend/eval/candidates.py — l'historique accumulé ne suffit pas encore à régler un seuil
    numérique) : un item n'est escaladé au LLM que s'il existe au moins un candidat dans
    l'historique (chevauchement de mots-clés non nul), sans quoi il reste thread_id=None sans appel.
    Plafonné à MAX_THREAD_ESCALATIONS_PER_RUN par run comme le vérificateur.

    La fenêtre d'historique est chargée une fois (verify() a déjà écrit les items du run courant
    avant que ce nœud s'exécute, donc ils y figurent déjà) et tenue à jour en mémoire au fil de la
    boucle : un item traité tôt dans le run peut ainsi être retrouvé, avec son thread_id fraîchement
    assigné, par un item traité plus tard dans le même run. Quand le candidat retrouvé n'a pas
    encore de thread_id, un nouvel identifiant est créé et rattaché aux deux — l'ancien
    enregistrement est réécrit en entier (put_analyzed remplace par lien, pas de patch partiel, cf.
    backend/memory/persistence.py). La fusion de deux fils déjà distincts n'est pas gérée en v1.
    """
    window = analyzed_window()

    escalated = 0
    budget_exhausted = False
    touched_links: set[str] = set()

    for item in state["analyzed_items"]:
        probe = search_thread_candidates(f"{item['title_fr']} {item['summary']}", exclude_link=item["link"], limit=1)
        escalatable = not budget_exhausted and bool(probe) and escalated < MAX_THREAD_ESCALATIONS_PER_RUN
        if not escalatable:
            continue

        escalated += 1
        try:
            winner_link = _thread_item(item)
        except BudgetExceeded:
            budget_exhausted = True
            continue

        if not winner_link or winner_link == item["link"] or winner_link not in window:
            # Lien absent de la fenêtre interrogée, ou item qui se référence lui-même : hallucination
            # du modèle plutôt qu'un rattachement fabriqué sur une base non vérifiée.
            continue

        winner = window[winner_link]
        # window peut ne pas encore porter l'item courant : verify() l'y écrit toujours en
        # production avant que ce nœud s'exécute, mais rien ne doit planter si un appelant (un test
        # unitaire, par exemple) ne l'a pas fait — repli sur l'item lui-même.
        mine = window.setdefault(item["link"], item)
        thread_id = winner.get("thread_id") or mine.get("thread_id") or str(uuid.uuid4())

        if mine.get("thread_id") != thread_id:
            window[item["link"]] = {**mine, "thread_id": thread_id}
            touched_links.add(item["link"])
        if winner.get("thread_id") != thread_id:
            window[winner_link] = {**winner, "thread_id": thread_id}
            touched_links.add(winner_link)

    # Reconstruit depuis les items d'origine (forme AnalyzedItem stricte), pas depuis window : les
    # enregistrements de window portent des champs de persistance (date, first_seen) qui n'ont pas
    # leur place dans l'état du graphe, seulement thread_id doit remonter.
    updated_items = [
        {**item, "thread_id": window.get(item["link"], item).get("thread_id")} for item in state["analyzed_items"]
    ]
    if touched_links:
        record_analyzed([window[link] for link in touched_links])

    return {"analyzed_items": updated_items, "truncated": state.get("truncated", False) or budget_exhausted}

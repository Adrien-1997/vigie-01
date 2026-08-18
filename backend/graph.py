"""Assemble le pipeline en StateGraph LangGraph : collect → deduplicate → analyze → verify → thread
(README §architecture).

deduplicate est placé avant analyze, pas après (cf. backend/memory/store.py) : filtrer les items déjà
vus avant l'appel LLM plutôt qu'après évite de payer un appel pour ré-analyser un item déjà traité.

verify (backend/agents/verifier.py) est la première tranche de docs/cadrage.md §10 V2 : recoupement
et score de confiance pour les items à catégorie sensible (VERIFIER_CATEGORIES), avec sa propre
boucle agentique bornée à l'intérieur du nœud.

thread (backend/agents/threader.py) est la première tranche de docs/cadrage.md §10 V3 : regroupement
en fils chronologiques, placé après verify pour que sa fenêtre d'historique voie déjà les items du
run courant (verify les a écrits), avec sa propre boucle agentique bornée elle aussi.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.agents.analyst import analyze
from backend.agents.collector import collect
from backend.agents.threader import thread_events
from backend.agents.verifier import verify
from backend.config import MAX_STEPS_PER_RUN
from backend.memory.store import deduplicate
from backend.state import VeilleState


def build_graph() -> CompiledStateGraph:
    builder = StateGraph(VeilleState)
    builder.add_node("collect", collect)
    builder.add_node("analyze", analyze)
    builder.add_node("deduplicate", deduplicate)
    builder.add_node("verify", verify)
    builder.add_node("thread", thread_events)

    builder.add_edge(START, "collect")
    builder.add_edge("collect", "deduplicate")
    builder.add_edge("deduplicate", "analyze")
    builder.add_edge("analyze", "verify")
    builder.add_edge("verify", "thread")
    builder.add_edge("thread", END)

    return builder.compile()


def run_pipeline() -> VeilleState:
    """Lève langgraph.errors.GraphRecursionError si MAX_STEPS_PER_RUN est dépassé
    (garde-fou §8 "boucle d'agent incontrôlée", non négociable — cf. docs/cadrage.md).
    """
    graph = build_graph()
    return graph.invoke(
        {"raw_items": [], "analyzed_items": [], "truncated": False},
        config={"recursion_limit": MAX_STEPS_PER_RUN},
    )

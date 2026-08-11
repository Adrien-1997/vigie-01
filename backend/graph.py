"""Assemble le pipeline V1 en StateGraph LangGraph : collect → deduplicate → analyze (README §architecture).

deduplicate est placé avant analyze, pas après (cf. backend/memory/store.py) : filtrer les items déjà
vus avant l'appel LLM plutôt qu'après évite de payer un appel pour ré-analyser un item déjà traité.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.agents.analyst import analyze
from backend.agents.collector import collect
from backend.memory.store import deduplicate
from backend.state import VeilleState


def build_graph() -> CompiledStateGraph:
    builder = StateGraph(VeilleState)
    builder.add_node("collect", collect)
    builder.add_node("analyze", analyze)
    builder.add_node("deduplicate", deduplicate)

    builder.add_edge(START, "collect")
    builder.add_edge("collect", "deduplicate")
    builder.add_edge("deduplicate", "analyze")
    builder.add_edge("analyze", END)

    return builder.compile()


def run_pipeline() -> VeilleState:
    graph = build_graph()
    return graph.invoke({"raw_items": [], "analyzed_items": []})

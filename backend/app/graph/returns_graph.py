from langgraph.graph import StateGraph, END

from app.graph.state import GraphState
from app.graph.nodes.intake import intake_node
from app.graph.nodes.fetch_order import fetch_order_node
from app.graph.nodes.retrieve_policy import retrieve_policy_node
from app.graph.nodes.decide import decide_node
from app.graph.nodes.draft import draft_node
from app.graph.nodes.validate_citations import validate_citations_node


def build_graph():
    g = StateGraph(GraphState)

    g.add_node("intake", intake_node)
    g.add_node("fetch_order", fetch_order_node)
    g.add_node("retrieve_policy", retrieve_policy_node)
    g.add_node("decide", decide_node)
    g.add_node("draft", draft_node)
    g.add_node("validate", validate_citations_node)

    g.set_entry_point("intake")
    g.add_edge("intake", "fetch_order")
    g.add_edge("fetch_order", "retrieve_policy")
    g.add_edge("retrieve_policy", "decide")
    g.add_edge("decide", "draft")
    g.add_edge("draft", "validate")

    def needs_redraft(state: GraphState) -> str:
        return "draft" if state.get("_needs_redraft") else END

    g.add_conditional_edges("validate", needs_redraft)

    return g.compile()
from langgraph.graph import StateGraph, END
from app.graph.state import GraphState
from app.graph.nodes.retrieve_policy import retrieve_policy_node
from app.graph.nodes.finalize_case import finalize_case_node


def build_finalize_graph():
    g = StateGraph(GraphState)
    g.add_node("retrieve_policy", retrieve_policy_node)
    g.add_node("finalize_case", finalize_case_node)

    g.set_entry_point("retrieve_policy")
    g.add_edge("retrieve_policy", "finalize_case")
    g.add_edge("finalize_case", END)
    return g.compile()
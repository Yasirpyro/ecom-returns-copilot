from app.rag.retriever import retrieve_policy_chunks_strict
from app.graph.state import GraphState


def retrieve_policy_node(state: GraphState) -> GraphState:
    query_parts = [
        f"Reason: {state.get('reason','')}",
        f"Customer message: {state.get('customer_message') or ''}",
        "Task: Determine eligibility and required steps according to policy.",
    ]
    query = "\n".join([p for p in query_parts if p.strip()])

    docs = retrieve_policy_chunks_strict(query)
    state["policy_docs"] = docs
    return state
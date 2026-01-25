from __future__ import annotations

from app.graph.state import GraphState
from app.tools.order_lookup import get_order, enrich_order


def fetch_order_node(state: GraphState) -> GraphState:
    """
    Fetches the order from local JSON and enriches line items with product metadata.

    Why this node exists:
    - Keeps data/tool access out of `decide.py`
    - Makes the graph modular and easier to extend later (real DB/Shopify/etc.)
    """
    order_id = state.get("order_id")
    if not order_id:
        state.setdefault("errors", []).append("missing_order_id")
        state["escalate"] = True
        return state

    order = get_order(order_id)
    if not order:
        state.setdefault("errors", []).append("order_not_found")
        state["escalate"] = True
        state["order"] = {}
        return state

    state["order"] = enrich_order(order)
    return state
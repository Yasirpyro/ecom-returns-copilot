from __future__ import annotations
from app.graph.state import GraphState


def validate_citations_node(state: GraphState) -> GraphState:
    """
    Fast validation (no LLM):
    - Ensure reply aligns with decision flags
    - Ensure we have at least 1 policy doc cited
    - If it fails, retry drafting once with quality model
    """
    decision = state.get("decision") or {}
    reply = (state.get("customer_reply") or "").lower()
    docs = state.get("policy_docs") or []

    errors = []

    # Must have some retrieved policy context
    if len(docs) == 0:
        errors.append("no_policy_docs")

    # If photos required, reply must ask for photos
    if decision.get("requires_photos") is True:
        if "photo" not in reply and "picture" not in reply:
            errors.append("missing_photo_request")

    # If return is required, reply should mention return
    if decision.get("requires_return") is True:
        if "return" not in reply:
            errors.append("missing_return_instruction")

    # If resolution is manual review or investigation, reply should mention review/investigation
    rt = decision.get("resolution_type")
    if rt == "manual_review" and ("review" not in reply and "specialist" not in reply):
        errors.append("missing_manual_review_language")
    if rt == "carrier_investigation" and ("investigation" not in reply and "carrier" not in reply):
        errors.append("missing_investigation_language")

    # Retry logic: one retry max
    state.setdefault("retries", 0)
    if errors and state["retries"] < 1:
        state["retries"] += 1
        # Retry draft with higher token cap
        state["llm_profile"] = "draft"
        state["draft_max_tokens"] = 220
        state["errors"] = (state.get("errors") or []) + errors
        # Signal graph to loop (returns_graph will use this)
        state["escalate"] = False
        state["_needs_redraft"] = True  # internal flag
        return state

    # Final: record errors but don't loop
    state["errors"] = (state.get("errors") or []) + errors
    state["_needs_redraft"] = False
    return state
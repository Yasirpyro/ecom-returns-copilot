from __future__ import annotations
import re
from app.graph.state import GraphState


def _estimate_complexity(reason: str, msg: str) -> int:
    """
    Complexity heuristic:
    1 = simple preference return / basic refund
    3 = shipping missing / gift logic / fees
    5 = warranty/defect, late return, mixed conditions, policy conflicts
    """
    text = f"{reason} {msg}".lower()

    score = 1

    # multi-issue / long message
    if len(text) > 240:
        score += 1

    # harder intents
    hard_keywords = [
        "warranty", "defect", "manufacturing", "pilling", "zipper", "seam",
        "late", "outside window", "holiday", "investigation", "delivered but missing",
        "wrong item", "damaged", "carrier", "chargeback"
    ]
    if any(k in text for k in hard_keywords):
        score += 2

    # mixed signals (contains both return and shipping/warranty terms)
    if ("return" in text or "refund" in text) and ("lost" in text or "missing" in text or "warranty" in text):
        score += 1

    return max(1, min(5, score))


def intake_node(state: GraphState) -> GraphState:
    reason = state.get("reason") or ""
    msg = state.get("customer_message") or ""

    complexity = _estimate_complexity(reason, msg)

    # Route model profile:
    # - "fast" => qwen2.5:3b-instruct
    # - "quality" => qwen2.5:7b-instruct
    # - "repair" => used only on retry (validate_citations triggers)
    llm_profile = "fast" if complexity <= 2 else "quality"

    state["complexity"] = complexity
    state["llm_profile"] = llm_profile
    state.setdefault("retries", 0)
    return state
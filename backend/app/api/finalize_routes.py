import json
from fastapi import APIRouter, HTTPException

from app.cases.repo import get_case, set_final_reply
from app.graph.finalize_graph import build_finalize_graph

router = APIRouter(prefix="/cases", tags=["cases"])
_finalize_graph = build_finalize_graph()


@router.post("/{case_id}/finalize")
def finalize_case(case_id: str):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Must have a human decision first
    if not case.get("human_decision"):
        raise HTTPException(status_code=400, detail="Human decision is required before finalizing")

    # Build state for finalize graph
    state = {
        "order_id": case["order_id"],
        "reason": case["reason"],
        "customer_message": case.get("customer_message"),
        "order": case.get("order_facts_json") or {},
        "decision": case.get("ai_decision_json") or {},
        "human_decision": case.get("human_decision"),
        "human_notes": case.get("human_notes"),
        "photo_urls": case.get("photo_urls_json") or [],
        "complexity": 4,  # warranty/photo review tends to be complex; you can store actual value in DB later
    }

    out = _finalize_graph.invoke(state)
    raw = out.get("finalize_output_raw", "")

    try:
        payload = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=500, detail=f"Finalize output was not valid JSON. Raw: {raw[:300]}")

    customer_reply = (payload.get("customer_reply") or "").strip()
    if not customer_reply:
        raise HTTPException(status_code=500, detail="Finalize output missing customer_reply")

    set_final_reply(case_id, customer_reply)

    return {
        "case_id": case_id,
        "status": "closed",
        "customer_reply": customer_reply,
        "next_actions": payload.get("next_actions") or [],
        "raw": payload,  # useful for debugging; remove later if you want
    }
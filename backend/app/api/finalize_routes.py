import json
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException

from app.cases.repo import get_case, set_final_outcome
from app.graph.finalize_graph import build_finalize_graph
from app.security.basic_auth import require_reviewer_basic_auth

router = APIRouter(prefix="/cases", tags=["cases"])
_finalize_graph = build_finalize_graph()


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except Exception:
        # Try to extract JSON object from mixed output
        if raw:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                snippet = raw[start : end + 1]
                return json.loads(snippet)
        raise


def _fallback_finalize_payload(case: Dict[str, Any]) -> Dict[str, Any]:
    decision = case.get("ai_decision_json") or {}
    human_decision = (case.get("human_decision") or "").lower()
    notes = case.get("human_notes") or ""
    notes_lower = notes.lower()
    order = case.get("order_facts_json") or {}
    items = order.get("items") or []

    first_item = items[0] if items else {}
    sku = first_item.get("sku")
    qty = int(first_item.get("qty", 1)) if first_item else None

    # Build reason text from reviewer notes
    reason_text = ""
    if notes.strip():
        reason_text = f" Reason: {notes.strip()}"

    if human_decision == "approved":
        action_type = "issue_refund" if "out of stock" in notes_lower else "issue_replacement"
        
        # Build approval message with next steps
        if action_type == "issue_refund":
            next_steps = (
                "\n\nNext steps:\n"
                "1. Your refund will be processed within 3-5 business days.\n"
                "2. You'll receive a confirmation email with refund details.\n"
                "3. The refund will be credited to your original payment method."
            )
        else:
            next_steps = (
                "\n\nNext steps:\n"
                "1. We'll ship your replacement item within 1-2 business days.\n"
                "2. You'll receive a tracking number via email once shipped.\n"
                "3. Please return the defective item using the prepaid label we'll send."
            )
        
        reply = (
            f"Great news! Your request has been approved.{reason_text}"
            f"{next_steps}"
        )
        next_actions = [
            {
                "type": action_type,
                "summary": "Approved resolution",
                "sku": sku,
                "qty": qty,
                "refund_amount": None,
                "refund_method": None,
            }
        ]
    elif human_decision == "denied":
        can_return = decision.get("resolution_type") == "return_for_refund"
        
        # Include reason for denial
        if reason_text:
            denial_reason = reason_text
        else:
            denial_reason = " Unfortunately, your request does not meet our policy criteria for approval."
        
        if can_return:
            reply = (
                f"We're sorry, but your warranty claim has been denied.{denial_reason}\n\n"
                "However, you may still be eligible for a standard return. "
                "Please visit our returns page or start a new chat to explore return options."
            )
        else:
            reply = (
                f"We're sorry, but your request has been denied.{denial_reason}\n\n"
                "If you believe this decision was made in error or have additional information to share, "
                "please start a new chat and we'll be happy to review your case again."
            )
        next_actions = [
            {
                "type": "manual_agent_followup",
                "summary": "Communicate denial to customer",
                "sku": sku,
                "qty": qty,
                "refund_amount": None,
                "refund_method": None,
            }
        ]
    else:
        reply = (
            "Thanks for the update. We need a bit more information to proceed—"
            "please share clear photos of the issue, plus your order ID and SKU."
        )
        next_actions = [
            {
                "type": "request_more_info",
                "summary": "Request photos and order details",
                "sku": sku,
                "qty": qty,
                "refund_amount": None,
                "refund_method": None,
            }
        ]

    return {"customer_reply": reply, "next_actions": next_actions}


@router.post("/{case_id}/finalize", dependencies=[Depends(require_reviewer_basic_auth)])
def finalize_case(case_id: str):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Idempotency: if already closed with final reply, return stored result
    if case.get("status") == "closed" and case.get("final_customer_reply"):
        return {
            "case_id": case_id,
            "status": "closed",
            "customer_reply": case.get("final_customer_reply"),
            "next_actions": case.get("next_actions_json") or [],
        }

    if not case.get("human_decision"):
        raise HTTPException(status_code=400, detail="Human decision is required before finalizing")

    # Build state
    state = {
        "order_id": case["order_id"],
        "reason": case["reason"],
        "customer_message": case.get("customer_message"),
        "order": case.get("order_facts_json") or {},
        "decision": case.get("ai_decision_json") or {},
        "human_decision": case.get("human_decision"),
        "human_notes": case.get("human_notes"),
        "photo_urls": case.get("photo_urls_json") or [],
        # warranty review tends to be complex; keep quality model available
        "complexity": 4,
        "llm_profile": "finalize",
    }

    out = _finalize_graph.invoke(state)
    raw = out.get("finalize_output_raw") or ""

    if not raw.strip():
        retry_state = dict(state)
        retry_state["llm_profile"] = "repair"
        retry_state["force_json_only"] = True
        retry_state["force_minimal_prompt"] = True
        out = _finalize_graph.invoke(retry_state)
        raw = out.get("finalize_output_raw") or ""

    try:
        payload = _parse_json(raw)
    except Exception:
        # One retry with repair profile + stricter JSON-only instruction
        retry_state = dict(state)
        retry_state["llm_profile"] = "repair"
        retry_state["force_json_only"] = True
        retry_state["force_minimal_prompt"] = True
        out = _finalize_graph.invoke(retry_state)
        raw = out.get("finalize_output_raw") or ""

        try:
            payload = _parse_json(raw)
        except Exception:
            if not raw.strip():
                payload = _fallback_finalize_payload(case)
            else:
                raise HTTPException(status_code=500, detail=f"Finalize output was not valid JSON. Raw: {raw[:500]}")

    customer_reply = (payload.get("customer_reply") or "").strip()
    next_actions = payload.get("next_actions") or []
    if isinstance(next_actions, dict):
        next_actions = [next_actions]

    if not customer_reply:
        raise HTTPException(status_code=500, detail="Finalize output missing customer_reply")
    if not isinstance(next_actions, list):
        raise HTTPException(status_code=500, detail="Finalize output next_actions must be a list")

    set_final_outcome(case_id, customer_reply, next_actions)

    return {
        "case_id": case_id,
        "status": "closed",
        "customer_reply": customer_reply,
        "next_actions": next_actions,
    }

from fastapi import APIRouter, HTTPException

from app.api.chat_schemas import ChatStartResponse, ChatMessageRequest, ChatMessageResponse
from app.chat.repo import create_session, add_message, get_messages
from app.graph.returns_graph import build_graph
from app.tools.order_lookup import get_order, enrich_order
from app.cases.repo import create_case

router = APIRouter(prefix="/chat", tags=["chat"])
_graph = build_graph()


@router.post("/start", response_model=ChatStartResponse)
def chat_start():
    return ChatStartResponse(session_id=create_session())


@router.post("/{session_id}", response_model=ChatMessageResponse)
def chat_send(session_id: str, req: ChatMessageRequest):
    # Save user message
    add_message(session_id, "user", req.message)

    # Require order id for now (simple production-grade constraint)
    order_id = req.order_id
    if not order_id:
        msg = "Please provide your order ID so I can check eligibility and next steps."
        add_message(session_id, "assistant", msg)
        return ChatMessageResponse(session_id=session_id, assistant_message=msg)

    order = get_order(order_id)
    if not order:
        msg = "I couldn’t find that order ID. Please double-check it and try again."
        add_message(session_id, "assistant", msg)
        return ChatMessageResponse(session_id=session_id, assistant_message=msg)

    order = enrich_order(order)

    # If reason not provided, we do a lightweight inference (keywords)
    inferred_reason = (req.reason or "").strip()
    if not inferred_reason:
        txt = req.message.lower()
        if any(k in txt for k in ["doesn't fit", "too small", "too big", "wrong size", "changed my mind"]):
            inferred_reason = "Doesn't fit"
        elif any(k in txt for k in ["lost", "missing", "not arrived", "label created", "in transit"]):
            inferred_reason = "Shipping issue"
        elif any(k in txt for k in ["defect", "broke", "broken", "fading", "pilling", "zipper", "seam", "quality"]):
            inferred_reason = "Quality issue"
        else:
            inferred_reason = "General inquiry"

    state = {
        "order_id": order_id,
        "reason": inferred_reason,
        "customer_message": req.message,
        "wants_store_credit": req.wants_store_credit,
        "photos_provided": req.photos_provided,
        "order": order,
        "errors": [],
    }

    out = _graph.invoke(state)
    assistant_message = out.get("customer_reply", "").strip() or "Thanks—our team will review this."

    case_id = None
    status = None

    # Create case if escalation or photos required
    decision = out.get("decision") or {}
    escalate = bool(out.get("escalate"))
    photos_required = bool(decision.get("requires_photos"))

    if escalate or photos_required:
        status = "needs_customer_photos" if photos_required else "ready_for_human_review"
        case_id = create_case(
            {
                "order_id": order_id,
                "reason": inferred_reason,
                "customer_message": req.message,
                "wants_store_credit": req.wants_store_credit,
                "photos_required": photos_required,
                "status": status,
                "ai_decision": decision,
                "ai_audit": out.get("audit") or {},
                "policy_citations": [
                    {
                        "source": str(d.metadata.get("source")),
                        "excerpt": (d.page_content or "")[:600],
                        "policy_id": None,
                    }
                    for d in (out.get("policy_docs") or [])[:3]
                ],
                "order_facts": order,  # IMPORTANT: enriched order stored
                "photo_urls": [],
            }
        )

    # Save assistant message linked to case if present
    add_message(session_id, "assistant", assistant_message, case_id=case_id)

    return ChatMessageResponse(
        session_id=session_id,
        assistant_message=assistant_message,
        case_id=case_id,
        status=status,
    )
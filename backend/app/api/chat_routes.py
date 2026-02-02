from fastapi import APIRouter, HTTPException

from app.api.chat_schemas import ChatStartResponse, ChatMessageRequest, ChatMessageResponse
from app.chat.repo import create_session, add_message, get_messages
from app.graph.returns_graph import build_graph
from app.tools.order_lookup import get_order, enrich_order, normalize_order_id
from app.cases.repo import create_case, get_active_case_for_session, get_closed_case_for_session
from app.rag.retriever import retrieve_policy_chunks_strict

router = APIRouter(prefix="/chat", tags=["chat"])
_graph = build_graph()


def _answer_general_query(query: str) -> str:
    """
    Answer general policy-related queries using RAG retrieval.
    Returns a helpful answer or a formal fallback message.
    """
    # Try to retrieve relevant policy chunks
    try:
        docs = retrieve_policy_chunks_strict(query)
    except Exception:
        docs = []
    
    if not docs:
        return (
            "I apologize, but I'm unable to assist with that particular query. "
            "For further assistance, please start a new chat or contact our customer support team."
        )
    
    # Check if query is relevant to our policies (returns, warranty, refunds, shipping)
    query_lower = query.lower()
    policy_keywords = [
        "return", "refund", "exchange", "warranty", "shipping", "delivery",
        "replacement", "defect", "damaged", "lost", "policy", "credit",
        "cancel", "order", "product", "item"
    ]
    
    is_relevant = any(keyword in query_lower for keyword in policy_keywords)
    
    if not is_relevant:
        return (
            "I apologize, but that question is outside the scope of what I can help with. "
            "I'm here to assist with returns, warranties, refunds, and shipping inquiries. "
            "For other questions, please contact our customer support team or start a new chat."
        )
    
    # Build a simple response from policy content
    policy_content = "\n".join([doc.page_content[:500] for doc in docs[:2]])
    
    # Return a summary based on the query type
    if "return" in query_lower or "exchange" in query_lower:
        return (
            "Based on our return policy:\n"
            "• Items can be returned within 30 days of delivery for most products.\n"
            "• Items must be in original condition with tags attached.\n"
            "• Final sale items cannot be returned.\n\n"
            "If you have a specific return request, please start a new chat and provide your order ID."
        )
    elif "warranty" in query_lower or "defect" in query_lower:
        return (
            "Based on our warranty policy:\n"
            "• Apparel items have a 90-day warranty against manufacturing defects.\n"
            "• Footwear and accessories have a 180-day warranty.\n"
            "• Photo evidence is required for warranty claims.\n\n"
            "If you'd like to file a warranty claim, please start a new chat with your order ID."
        )
    elif "refund" in query_lower or "credit" in query_lower:
        return (
            "Based on our refund policy:\n"
            "• Refunds are processed within 3-5 business days after approval.\n"
            "• Refunds are credited to your original payment method.\n"
            "• Store credit may be offered as an alternative.\n\n"
            "For a specific refund inquiry, please start a new chat with your order details."
        )
    elif "shipping" in query_lower or "delivery" in query_lower:
        return (
            "Based on our shipping policy:\n"
            "• Standard shipping typically takes 5-7 business days.\n"
            "• Express shipping is available for faster delivery.\n"
            "• Lost packages are investigated after 10 business days.\n\n"
            "For a specific shipping issue, please start a new chat with your order ID."
        )
    else:
        return (
            "I can help answer general questions about our policies. "
            "For specific requests or to file a claim, please start a new chat and provide your order ID. "
            "Our team will be happy to assist you with your inquiry."
        )


@router.post("/start", response_model=ChatStartResponse)
def chat_start():
    return ChatStartResponse(session_id=create_session())


@router.post("/{session_id}", response_model=ChatMessageResponse)
def chat_send(session_id: str, req: ChatMessageRequest):
    # Guard: prevent new case creation if an active case already exists for this session
    active_case = get_active_case_for_session(session_id)
    if active_case:
        status = active_case.get("status")
        msg = (
            "Your case is under review. You'll receive an update here." if status != "needs_customer_photos" else
            "Please upload the requested photos to continue."
        )
        add_message(session_id, "assistant", msg, case_id=active_case.get("case_id"))
        return ChatMessageResponse(
            session_id=session_id,
            assistant_message=msg,
            case_id=active_case.get("case_id"),
            status=status,
        )
    
    # Check if session has a closed case - no new cases allowed, only general queries
    closed_case = get_closed_case_for_session(session_id)
    if closed_case:
        # Save user message
        add_message(session_id, "user", req.message)
        
        # If user is trying to start a new case (providing order ID), redirect them
        if req.order_id:
            msg = (
                "Your previous case has been closed. To submit a new request, "
                "please click 'New' to start a fresh chat session. "
                "This helps us track and resolve your inquiries more effectively."
            )
            add_message(session_id, "assistant", msg)
            return ChatMessageResponse(
                session_id=session_id,
                assistant_message=msg,
                case_id=closed_case.get("case_id"),
                status="closed",
            )
        
        # Answer general queries using RAG
        answer = _answer_general_query(req.message)
        add_message(session_id, "assistant", answer)
        return ChatMessageResponse(
            session_id=session_id,
            assistant_message=answer,
            case_id=closed_case.get("case_id"),
            status="closed",
        )
    
    # Save user message
    add_message(session_id, "user", req.message)

    # Require order id for now (simple production-grade constraint)
    raw_order_id = req.order_id
    if not raw_order_id:
        msg = "Please provide your order ID so I can check eligibility and next steps."
        add_message(session_id, "assistant", msg)
        return ChatMessageResponse(session_id=session_id, assistant_message=msg)

    # Normalize order ID to ORD-xxxxx format
    order_id = normalize_order_id(raw_order_id)

    order = get_order(order_id)
    if not order:
        msg = "I couldn't find that order ID. Please double-check it and try again."
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
                "session_id": session_id,
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

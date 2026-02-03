from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.api.chat_schemas import ChatStartResponse, ChatMessageRequest, ChatMessageResponse
from app.chat.repo import create_session, add_message, get_messages
from app.graph.returns_graph import build_graph
from app.tools.order_lookup import get_order, enrich_order, normalize_order_id
from app.cases.repo import create_case, get_active_case_for_session, get_closed_case_for_session
from app.rag.retriever import retrieve_policy_chunks_strict

router = APIRouter(prefix="/chat", tags=["chat"])
_graph = build_graph()


def _is_status_inquiry(message: str) -> bool:
    """
    Check if the message is asking about order status/tracking (not an issue).
    These should NOT create a case for human review.
    """
    msg_lower = message.lower()
    
    # Keywords that indicate a status/tracking inquiry
    status_keywords = [
        "status", "track", "tracking", "where is", "where's", "when will",
        "when does", "when is", "delivery date", "estimated", "eta",
        "shipped", "shipping status", "check status", "order status",
        "has it shipped", "has my order", "when can i expect",
        "how long", "arriving", "arrive", "delivery status"
    ]
    
    # Keywords that indicate an actual ISSUE requiring case creation
    issue_keywords = [
        "damage", "damaged", "broken", "defect", "defective", "wrong",
        "missing", "lost", "never arrived", "didn't receive", "not received",
        "haven't received", "did not receive", "never received", "didn't get",
        "did not get", "never got", "haven't got", "not delivered",
        "wasn't delivered", "not here", "never came", "didn't come",
        "quality", "ripped", "torn", "stain", "fading", "pilling",
        "zipper", "seam", "fell apart", "doesn't work", "malfunction",
        "return", "refund", "exchange", "warranty", "claim", "complaint",
        "doesn't fit", "too small", "too big", "wrong size", "wrong color",
        "wrong item", "not what i ordered"
    ]
    
    has_status_keyword = any(kw in msg_lower for kw in status_keywords)
    has_issue_keyword = any(kw in msg_lower for kw in issue_keywords)
    
    # It's a status inquiry if it has status keywords but NO issue keywords
    return has_status_keyword and not has_issue_keyword


def _is_non_receipt_claim(message: str, order: dict) -> bool:
    """
    Check if the user is claiming non-receipt of a delivered order.
    This is a special case that MUST create a case for investigation.
    """
    tracking_status = order.get("tracking_status", "")
    if tracking_status != "delivered":
        return False
    
    msg_lower = message.lower()
    
    # Patterns indicating non-receipt claim
    non_receipt_patterns = [
        "didn't receive", "did not receive", "haven't received", "not received",
        "never received", "didn't get", "did not get", "haven't got", "never got",
        "not delivered", "wasn't delivered", "never arrived", "didn't arrive",
        "not here", "never came", "didn't come", "where is it", "still waiting",
        "hasn't arrived", "has not arrived", "haven't gotten", "didn't show",
        "not showing", "can't find", "cannot find", "don't have", "do not have"
    ]
    
    return any(pattern in msg_lower for pattern in non_receipt_patterns)


def _format_order_status_response(order: dict, message: str) -> str:
    """
    Generate a helpful response for order status inquiries directly from order data.
    No case is created - this is informational only.
    """
    order_id = order.get("order_id", "Unknown")
    tracking_status = order.get("tracking_status", "unknown")
    delivered_at = order.get("delivered_at")
    tracking_last_scan = order.get("tracking_last_scan_at")
    shipping_method = order.get("shipping_method", "standard")
    placed_at = order.get("placed_at")
    
    # Format dates nicely
    def format_date(date_str):
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%B %d, %Y at %I:%M %p")
        except:
            return date_str
    
    status_emoji = {
        "delivered": "✅",
        "in_transit": "🚚",
        "label_created": "📦",
        "out_for_delivery": "🏃",
        "unknown": "❓"
    }
    
    emoji = status_emoji.get(tracking_status, "📦")
    
    if tracking_status == "delivered":
        delivered_date = format_date(delivered_at) or "recently"
        return (
            f"Hi, thanks for reaching out about order **{order_id}**.\n\n"
            f"{emoji} **Status: Delivered**\n\n"
            f"Great news! Your order was delivered on **{delivered_date}**.\n\n"
            "If you haven't received it or there's an issue with your items, "
            "please let me know and I'll be happy to help!"
        )
    
    elif tracking_status == "in_transit":
        last_scan = format_date(tracking_last_scan) or "recently"
        shipping_times = {
            "standard": "5-7 business days",
            "express": "2-3 business days",
            "overnight": "1 business day"
        }
        expected = shipping_times.get(shipping_method, "5-7 business days")
        return (
            f"Hi, thanks for reaching out about order **{order_id}**.\n\n"
            f"{emoji} **Status: In Transit**\n\n"
            f"Your order is on its way! Last scan: **{last_scan}**\n"
            f"Shipping method: **{shipping_method.title()}** (typically {expected})\n\n"
            "Please check the tracking link in your order confirmation email for real-time updates.\n\n"
            "If your package doesn't arrive within the expected timeframe, let me know and I'll investigate."
        )
    
    elif tracking_status == "label_created":
        placed_date = format_date(placed_at) or "recently"
        return (
            f"Hi, thanks for reaching out about order **{order_id}**.\n\n"
            f"{emoji} **Status: Label Created**\n\n"
            f"Your order was placed on **{placed_date}** and is being prepared for shipment.\n"
            "The shipping label has been created, and your package should be picked up soon.\n\n"
            "You'll receive tracking updates via email once the carrier scans your package.\n\n"
            "If you don't see movement within 2-3 business days, please reach out and I'll look into it."
        )
    
    else:
        return (
            f"Hi, thanks for reaching out about order **{order_id}**.\n\n"
            f"📦 **Status: Processing**\n\n"
            "Your order is currently being processed. You'll receive tracking information "
            "via email once it ships.\n\n"
            "If you have any concerns, please let me know!"
        )


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
    
    # Check if query is relevant to our policies (returns, warranty, refunds, shipping)
    query_lower = query.lower()
    policy_keywords = [
        "return", "refund", "exchange", "warranty", "shipping", "delivery",
        "replacement", "defect", "damaged", "lost", "policy", "policies",
        "credit", "cancel", "order", "product", "item", "money back",
        "how long", "how do", "what is", "what are", "can i", "do you"
    ]
    
    is_relevant = any(keyword in query_lower for keyword in policy_keywords)
    
    if not is_relevant and not docs:
        return (
            "I apologize, but that question is outside the scope of what I can help with. "
            "I'm here to assist with returns, warranties, refunds, and shipping inquiries. "
            "For other questions, please contact our customer support team."
        )
    
    # Return a summary based on the query type
    if "return" in query_lower or "exchange" in query_lower:
        return (
            "Here's our **Return Policy**:\n\n"
            "✅ **30-Day Return Window** - Most items can be returned within 30 days of delivery.\n"
            "✅ **Original Condition** - Items must have tags attached and be unworn/unused.\n"
            "✅ **Free Returns** - We provide prepaid return labels for eligible items.\n"
            "❌ **Final Sale** - Items marked 'Final Sale' cannot be returned.\n"
            "❌ **Personalized Items** - Custom/personalized items are non-returnable.\n\n"
            "Would you like to start a return? Please provide your **Order ID** and I'll check eligibility."
        )
    elif "warranty" in query_lower or "defect" in query_lower or "quality" in query_lower:
        return (
            "Here's our **Warranty Policy**:\n\n"
            "🛡️ **Apparel** - 90-day warranty against manufacturing defects.\n"
            "🛡️ **Footwear & Accessories** - 180-day warranty against defects.\n"
            "📸 **Photo Required** - Clear photos of the defect are needed for claims.\n"
            "✅ **Coverage** - Includes stitching issues, hardware failures, fabric defects.\n"
            "❌ **Not Covered** - Normal wear and tear, misuse, or accidental damage.\n\n"
            "To file a warranty claim, please provide your **Order ID** and describe the issue."
        )
    elif "refund" in query_lower or "credit" in query_lower or "money" in query_lower:
        return (
            "Here's our **Refund Policy**:\n\n"
            "⏱️ **Processing Time** - Refunds are processed within 3-5 business days after approval.\n"
            "💳 **Payment Method** - Refunds go back to your original payment method.\n"
            "🎁 **Store Credit** - You can opt for store credit (often processed faster).\n"
            "📦 **Shipping Costs** - Original shipping fees are non-refundable unless we made an error.\n"
            "🔄 **Exchanges** - We can exchange for a different size/color if available.\n\n"
            "For a specific refund inquiry, please provide your **Order ID**."
        )
    elif "shipping" in query_lower or "delivery" in query_lower or "lost" in query_lower or "track" in query_lower:
        return (
            "Here's our **Shipping Policy**:\n\n"
            "📦 **Standard Shipping** - 5-7 business days.\n"
            "🚀 **Express Shipping** - 2-3 business days.\n"
            "✈️ **Overnight** - Next business day delivery.\n"
            "📍 **Tracking** - You'll receive tracking info via email once shipped.\n"
            "❓ **Lost Packages** - If not delivered within 10 business days, we'll investigate.\n\n"
            "Having a shipping issue? Please provide your **Order ID** and I'll look into it."
        )
    else:
        return (
            "I can help you with questions about:\n\n"
            "• **Returns** - 30-day return window for most items\n"
            "• **Warranties** - 90-180 day coverage for defects\n"
            "• **Refunds** - 3-5 business days processing\n"
            "• **Shipping** - Tracking and delivery issues\n\n"
            "What would you like to know more about? Or provide your **Order ID** to file a specific request."
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

    # Check if this is a general policy question (no order ID provided)
    raw_order_id = req.order_id
    if not raw_order_id:
        # Check if user is asking a general policy question
        query_lower = req.message.lower()
        policy_keywords = [
            "return", "refund", "exchange", "warranty", "shipping", "delivery",
            "replacement", "defect", "damaged", "lost", "policy", "policies",
            "credit", "cancel", "how long", "how do", "what is", "what are",
            "can i", "do you", "is there"
        ]
        
        is_policy_question = any(keyword in query_lower for keyword in policy_keywords)
        
        if is_policy_question:
            # Answer the general policy question using RAG
            answer = _answer_general_query(req.message)
            add_message(session_id, "assistant", answer)
            return ChatMessageResponse(session_id=session_id, assistant_message=answer)
        else:
            # Check if it's a greeting or irrelevant query
            greeting_keywords = ["hi", "hello", "hey", "wsup", "sup", "what's up", "howdy", "good morning", "good afternoon", "good evening"]
            is_greeting = any(keyword in query_lower for keyword in greeting_keywords)
            
            if is_greeting and len(req.message.split()) < 10:
                # It's just a greeting, respond friendly and ask how to help
                msg = (
                    "Hello! 👋 I'm your Returns & Warranty Assistant. I can help you with:\n\n"
                    "• **Returns & Exchanges** - Items within 30 days of delivery\n"
                    "• **Warranty Claims** - Manufacturing defects\n"
                    "• **Refunds** - Processing and status\n"
                    "• **Shipping Issues** - Lost or delayed packages\n\n"
                    "How can I assist you today? If you have a specific order, please provide your Order ID."
                )
                add_message(session_id, "assistant", msg)
                return ChatMessageResponse(session_id=session_id, assistant_message=msg)
            else:
                # Not a policy question - formal fallback
                msg = (
                    "I apologize, but I'm not sure how to help with that. "
                    "I specialize in returns, warranties, refunds, and shipping inquiries.\n\n"
                    "If you have a question about our policies, feel free to ask! "
                    "Or if you'd like to file a claim, please provide your Order ID."
                )
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

    # Check if user is claiming non-receipt of a "delivered" order - this needs a case
    if _is_non_receipt_claim(req.message, order):
        # Force this to go through case creation with "Shipping issue" reason
        inferred_reason = "Non-receipt claim"
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
        assistant_message = (
            f"I understand you haven't received order **{order_id}** even though it shows as delivered. "
            "I'm sorry for the inconvenience.\n\n"
            "I've escalated this to our team for investigation. They will:\n"
            "• Check with the carrier for delivery confirmation\n"
            "• Review any delivery photos or GPS data\n"
            "• Get back to you within 1-2 business days\n\n"
            "Thank you for your patience!"
        )
        
        decision = out.get("decision") or {}
        escalate = True  # Force escalation for non-receipt claims
        status = "ready_for_human_review"
        
        case_id = create_case(
            {
                "session_id": session_id,
                "order_id": order_id,
                "reason": inferred_reason,
                "customer_message": req.message,
                "wants_store_credit": req.wants_store_credit,
                "photos_required": False,
                "status": status,
                "ai_decision": {"action": "escalate", "reason": "Customer claims non-receipt of delivered order"},
                "ai_audit": out.get("audit") or {},
                "policy_citations": [],
                "order_facts": order,
                "photo_urls": [],
            }
        )
        
        add_message(session_id, "assistant", assistant_message, case_id=case_id)
        return ChatMessageResponse(
            session_id=session_id,
            assistant_message=assistant_message,
            case_id=case_id,
            status=status,
        )

    # Check if this is just a status inquiry (not an issue requiring case creation)
    if _is_status_inquiry(req.message):
        status_response = _format_order_status_response(order, req.message)
        add_message(session_id, "assistant", status_response)
        return ChatMessageResponse(session_id=session_id, assistant_message=status_response)

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

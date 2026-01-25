from fastapi import APIRouter, HTTPException

from app.api.schemas import ResolveRequest, ResolveResponse, Decision, InternalAudit, Citation
from app.graph.returns_graph import build_graph
from app.tools.order_lookup import get_order, enrich_order

router = APIRouter()
_graph = build_graph()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/resolve", response_model=ResolveResponse)
def resolve(req: ResolveRequest):
    order = get_order(req.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order = enrich_order(order)

    state = {
        "order_id": req.order_id,
        "reason": req.reason,
        "customer_message": req.customer_message,
        "wants_store_credit": req.wants_store_credit,
        "photos_provided": req.photos_provided,
        "order": order,
        "errors": [],
    }

    out = _graph.invoke(state)

    # Build citations from retrieved docs (simple MVP)
    citations = []
    for d in out.get("policy_docs", []):
        citations.append(
            Citation(
                source=str(d.metadata.get("source")),
                excerpt=d.page_content[:400],
                policy_id=None,
            )
        )

    decision = Decision(**out["decision"])
    audit = InternalAudit(
        order_facts_used={
            "order_id": order.get("order_id"),
            "delivered_at": order.get("delivered_at"),
            "tracking_status": order.get("tracking_status"),
            "is_gift": order.get("is_gift"),
            "outbound_shipping_paid": order.get("outbound_shipping_paid"),
            "items": [{"sku": i.get("sku"), "qty": i.get("qty"), "unit_price": i.get("unit_price")} for i in order.get("items", [])],
        },
        policy_citations=citations,
        escalate=bool(out.get("escalate")),
    )

    return ResolveResponse(
        decision=decision,
        customer_reply=out.get("customer_reply", ""),
        internal_audit=audit,
    )
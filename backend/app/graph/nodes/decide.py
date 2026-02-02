from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.graph.state import GraphState


def _parse_dt(dt: str | None) -> datetime | None:
    if not dt:
        return None
    return datetime.fromisoformat(dt)


def _today_utc() -> datetime:
    return datetime.now(timezone.utc)


def _money(x: float) -> float:
    return round(float(x), 2)


def _days_between(a: datetime, b: datetime) -> int:
    return (a.astimezone(timezone.utc) - b.astimezone(timezone.utc)).days


def _max_warranty_days(items: list[dict]) -> int:
    """
    Uses enriched product data if present (products.json -> warranty_days).
    Falls back to policy defaults:
      apparel: 90
      footwear_accessories: 180
    """
    days = []
    for it in items:
        product = (it.get("product") or {})
        if isinstance(product.get("warranty_days"), int):
            days.append(product["warranty_days"])
        else:
            cat = (product.get("category") or "").lower()
            if cat == "apparel":
                days.append(90)
            elif cat == "footwear_accessories":
                days.append(180)
    return max(days) if days else 0


def _classify(reason: str, msg: str) -> dict:
    text = f"{reason} {msg}".lower()

    is_preference = any(k in text for k in ["doesn't fit", "does not fit", "changed mind", "wrong size", "buyer remorse", "color looked"])

    # Shipping/lost-in-transit family
    is_shipping_issue = any(k in text for k in ["lost", "not arrived", "missing", "label created", "in transit", "delivered but missing"])

    # Warranty/defect family (expanded)
    is_warranty_issue = any(
        k in text
        for k in [
            "warranty",
            "defect",
            "manufacturing",
            "quality issue",
            "quality",
            "fading",
            "color fades",
            "colour fades",
            "color faded",
            "patch",
            "hole",
            "tear",
            "ripped",
            "rip",
            "stain",
            "frayed",
            "stitching",
            "pilling",
            "seam",
            "stitch",
            "zipper",
            "broken",
            "hardware",
        ]
    )

    # Vendor error (wrong/damaged on arrival) - separate from manufacturing defect
    is_vendor_error = any(k in text for k in ["wrong item", "arrived damaged", "damaged on arrival", "item arrived damaged"])

    return {
        "is_preference": is_preference,
        "is_shipping_issue": is_shipping_issue,
        "is_warranty_issue": is_warranty_issue,
        "is_vendor_error": is_vendor_error,
    }


def decide_node(state: GraphState) -> GraphState:
    order = state.get("order") or {}
    items = order.get("items", [])
    currency = order.get("currency", "USD")

    reason_raw = state.get("reason") or ""
    msg = state.get("customer_message") or ""

    wants_store_credit = bool(state.get("wants_store_credit"))
    photos_provided = bool(state.get("photos_provided"))

    delivered_at = _parse_dt(order.get("delivered_at"))
    placed_at = _parse_dt(order.get("placed_at"))

    # computed values
    item_subtotal = sum(float(i.get("unit_price", 0.0)) * int(i.get("qty", 1)) for i in items)
    is_gift = bool(order.get("is_gift"))

    any_final_sale = any(bool((i.get("product") or {}).get("is_final_sale")) for i in items)
    any_gift_card = any(((i.get("product") or {}).get("category") == "gift_card") for i in items)
    any_custom = any(((i.get("product") or {}).get("category") == "custom_personalized") for i in items)

    cls = _classify(reason_raw, msg)

    decision: Dict[str, Any] = {
        "eligible": False,
        "resolution_type": "manual_review",
        "refund_method": None,
        "refund_estimate": None,
        "currency": currency,
        "requires_photos": False,
        "requires_return": False,
        "deadline": None,
        "fees": [],
    }

    # 0) Hard non-returnable rejects (only for preference returns)
    if cls["is_preference"] and (any_final_sale or any_gift_card or any_custom):
        decision.update(eligible=False, resolution_type="reject", requires_return=False)
        state["decision"] = decision
        state["escalate"] = False
        return state

    # 1) Shipping issues
    tracking_status = (order.get("tracking_status") or "").lower()
    if cls["is_shipping_issue"]:
        if tracking_status == "delivered":
            decision.update(eligible=True, resolution_type="carrier_investigation", requires_return=False)
        else:
            decision.update(eligible=True, resolution_type="replacement", requires_return=False)
        state["decision"] = decision
        state["escalate"] = False
        return state

    # 2) Preference return flow (30 days)
    if cls["is_preference"]:
        if not delivered_at:
            decision.update(eligible=False, resolution_type="manual_review")
            state["decision"] = decision
            state["escalate"] = True
            return state

        days_since_delivery = _days_between(_today_utc(), delivered_at)
        if days_since_delivery > 30:
            decision.update(eligible=False, resolution_type="manual_review")
            state["decision"] = decision
            state["escalate"] = True
            return state

        decision.update(
            eligible=True,
            resolution_type="return_for_refund",
            requires_return=True,
            refund_method="store_credit" if (is_gift or wants_store_credit) else "original_payment",
        )

        fees: List[Dict[str, Any]] = []
        if decision["refund_method"] == "original_payment":
            fees.append({"code": "return_shipping_fee", "amount": 8.0, "currency": currency, "description": "Return shipping fee (deducted from refund)"})

        high_value = any(float(i.get("unit_price", 0.0)) > 500.0 for i in items)
        bulk = any(int(i.get("qty", 1)) >= 5 for i in items)
        if high_value or bulk:
            fees.append({"code": "restocking_fee", "amount": _money(item_subtotal * 0.15), "currency": currency, "description": "Restocking fee (15%)"})

        decision["fees"] = fees
        decision["refund_estimate"] = _money(max(item_subtotal - sum(float(f["amount"]) for f in fees), 0.0))
        decision["deadline"] = (delivered_at.date() + timedelta(days=30)).isoformat()

        state["decision"] = decision
        state["escalate"] = False
        return state

    # 3) Warranty/quality issues (HITL-friendly)
    if cls["is_warranty_issue"] or cls["is_vendor_error"]:
        # Warranty window check using product metadata
        if delivered_at:
            warranty_days = _max_warranty_days(items)
            if warranty_days > 0:
                days_since_delivery = _days_between(_today_utc(), delivered_at)
                if days_since_delivery > warranty_days:
                    # Out of warranty window -> manual review (don’t auto reject; keep it safe)
                    decision.update(eligible=False, resolution_type="manual_review", requires_photos=False, requires_return=False)
                    state["decision"] = decision
                    state["escalate"] = True
                    return state

        # If photos missing, open a warranty case and request evidence
        if not photos_provided:
            decision.update(
                eligible=True,
                resolution_type="warranty_claim_pending",
                requires_photos=True,
                requires_return=False,
            )
            state["decision"] = decision
            state["escalate"] = True  # create case + wait for photos/human review
            return state

        # Photos provided -> send to human review (do not auto-approve yet)
        decision.update(
            eligible=True,
            resolution_type="manual_review",
            requires_photos=False,
            requires_return=False,
        )
        state["decision"] = decision
        state["escalate"] = True
        return state

    # 4) Default fallback
    decision.update(eligible=False, resolution_type="manual_review")
    state["decision"] = decision
    state["escalate"] = True
    return state
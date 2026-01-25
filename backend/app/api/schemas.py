from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ResolveRequest(BaseModel):
    order_id: str = Field(..., examples=["ORD-10001"])
    reason: str = Field(..., examples=["Doesn't fit", "Arrived damaged", "Wrong item sent", "Quality issue"])
    customer_message: Optional[str] = Field(None, examples=["My zipper broke after 2 weeks."])
    wants_store_credit: bool = False
    photos_provided: bool = False


ResolutionType = Literal[
    "reject",
    "manual_review",
    "return_for_refund",
    "exchange",
    "replacement",
    "refund_no_return",
    "carrier_investigation",
    "warranty_claim_pending",
]


class FeeLine(BaseModel):
    code: str
    amount: float
    currency: str = "USD"
    description: str


class Decision(BaseModel):
    eligible: bool
    resolution_type: ResolutionType
    refund_method: Optional[Literal["original_payment", "store_credit"]] = None
    refund_estimate: Optional[float] = None
    currency: str = "USD"
    requires_photos: bool = False
    requires_return: bool = False
    deadline: Optional[str] = None
    fees: List[FeeLine] = []


class Citation(BaseModel):
    source: str
    excerpt: str
    policy_id: Optional[str] = None


class InternalAudit(BaseModel):
    order_facts_used: dict
    policy_citations: List[Citation]
    escalate: bool
    notes: Optional[str] = None


class ResolveResponse(BaseModel):
    decision: Decision
    customer_reply: str
    internal_audit: InternalAudit
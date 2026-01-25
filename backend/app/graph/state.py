from __future__ import annotations
from typing import Any, Dict, List, Optional, TypedDict, Literal

from langchain_core.documents import Document


LLMProfile = Literal["fast", "quality", "repair"]


class GraphState(TypedDict, total=False):
    # Input
    order_id: str
    reason: str
    customer_message: Optional[str]
    wants_store_credit: bool
    photos_provided: bool

    # Tools / data
    order: Dict[str, Any]

    # RAG
    policy_docs: List[Document]

    # Routing / model selection
    complexity: int               # 1..5
    llm_profile: LLMProfile       # fast/quality/repair

    # Outputs
    decision: Dict[str, Any]
    customer_reply: str
    audit: Dict[str, Any]

    # Control
    escalate: bool
    errors: List[str]
    retries: int
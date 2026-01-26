from typing import Optional
from pydantic import BaseModel, Field


class ChatStartResponse(BaseModel):
    session_id: str


class ChatMessageRequest(BaseModel):
    message: str = Field(..., examples=["My sneaker color faded after a week"])
    order_id: Optional[str] = Field(None, examples=["ORD-10003"])
    reason: Optional[str] = Field(None, examples=["Quality issue"])
    wants_store_credit: bool = False
    photos_provided: bool = False


class ChatMessageResponse(BaseModel):
    session_id: str
    assistant_message: str
    case_id: Optional[str] = None
    status: Optional[str] = None  # needs_customer_photos | ready_for_human_review | closed | None
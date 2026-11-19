from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

class Recommendation(str, Enum):
    REFUND_REVIEW = 'REFUND_REVIEW'
    REPLACE_REVIEW = 'REPLACE_REVIEW'
    INVESTIGATE_DELIVERY = 'INVESTIGATE_DELIVERY'
    REQUEST_INFO = 'REQUEST_INFO'
    NOT_ELIGIBLE = 'NOT_ELIGIBLE'
    MANUAL_REVIEW = 'MANUAL_REVIEW'

class EvidenceItem(BaseModel):
    source: str
    reference: str
    fact: str
    kind: str = Field(description='verified_fact, customer_claim, or tool_observation')

class CaseReport(BaseModel):
    case_id: str
    order_id: str | None
    detected_intent: str
    verified_order_status: str | None
    within_return_window: bool | None
    replacement_stock_available: bool | None
    recommendation: Recommendation
    evidence: list[EvidenceItem]
    policy_clause: list[str]
    confidence_note: str
    needs_human_approval: bool
    explanation: str
    approval_status: str = 'REVIEW_REQUIRED'

class EvidencePacket(BaseModel):
    case_id: str
    case: dict[str, Any]
    order: dict[str, Any] | None
    policy_summary: str
    inventory: dict[str, Any] | None
    within_return_window: bool | None
    days_after_delivery: int | None
    errors: list[str] = []

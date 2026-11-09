"""Research job and audit domain models."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ResearchJob(BaseModel):
    id: str
    user_id: str
    idempotency_key: str
    tab: Literal["news", "sentiment"]
    ticker_list: List[str]
    start_at: str
    end_at: str
    horizon_days: Optional[Literal[1, 7, 30, 90]] = None
    status: Literal[
        "requested", "validating", "authorized", "collecting",
        "normalizing", "verifying", "analyzing", "reporting",
        "completed", "failed", "cancelled", "rate_limited", "no_data"
    ] = "requested"
    created_at: str
    completed_at: Optional[str] = None
    error_code: Optional[str] = None
    credit_debited: int = Field(ge=0, le=1, default=0)


class AuditEvent(BaseModel):
    id: str
    actor_user_id: Optional[str] = None
    action: str
    subject_id: Optional[str] = None
    created_at: str
    metadata: Optional[dict] = None


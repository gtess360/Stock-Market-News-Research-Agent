"""Access token and token request domain models."""
from typing import Literal, Optional
from pydantic import BaseModel


class AccessToken(BaseModel):
    id: str
    token_hash: str
    token_prefix: str
    issued_to_user_id: Optional[str] = None
    status: Literal["active", "redeemed", "expired", "revoked"] = "active"
    created_at: str
    expires_at: Optional[str] = None
    revoked_at: Optional[str] = None
    issued_by_admin_id: Optional[str] = None
    redeemed_at: Optional[str] = None


class TokenRequest(BaseModel):
    id: str
    user_id: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    reason: Optional[str] = None
    requested_at: str
    reviewed_at: Optional[str] = None
    reviewer_id: Optional[str] = None


class EntitlementStatus(BaseModel):
    can_research: bool
    reason: str
    remaining_free: int
    has_unlimited: bool
    user_id: str
    role: str


"""User and usage account domain models."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class User(BaseModel):
    id: str
    auth_provider_subject: str
    role: Literal["user", "admin"] = "user"
    created_at: str
    status: Literal["active", "suspended", "deactivated"] = "active"


class UsageAccount(BaseModel):
    user_id: str
    free_success_count: int = Field(ge=0, le=3, default=0)
    updated_at: str
    version: int = 1

    @property
    def free_remaining(self) -> int:
        return max(0, 3 - self.free_success_count)


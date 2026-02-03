"""Auth-related Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel


class DevLoginRequest(BaseModel):
    username: str = "dev_admin"
    tenant_name: str = "default"


class DevLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    user_id: str
    role: str

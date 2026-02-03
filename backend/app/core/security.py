"""JWT helpers and authentication dependencies."""

from __future__ import annotations

import datetime as dt
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

_bearer = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


def create_access_token(
    tenant_id: str,
    user_id: str,
    role: str = "analyst",
    extra: dict[str, Any] | None = None,
) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": user_id,
        "tid": tenant_id,
        "role": role,
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.APP_JWT_EXPIRE_MIN),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.APP_JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.APP_JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


class CurrentUser:
    """Decoded JWT payload injected by FastAPI ``Depends``."""

    def __init__(self, tenant_id: str, user_id: str, role: str):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.role = role


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if cred is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    payload = decode_token(cred.credentials)
    return CurrentUser(
        tenant_id=payload["tid"],
        user_id=payload["sub"],
        role=payload.get("role", "analyst"),
    )

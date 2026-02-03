"""POST /api/v1/auth/dev-login – Dev environment login."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.models.models import Tenant, User
from app.schemas.auth import DevLoginRequest, DevLoginResponse
from app.schemas.common import ApiResponse
from app.utils.ulid import generate_ulid

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/dev-login", response_model=ApiResponse[DevLoginResponse])
def dev_login(body: DevLoginRequest, db: Session = Depends(get_db)):
    """Auto-create tenant + user for dev environment and return JWT."""
    # Find or create tenant
    tenant = db.query(Tenant).filter_by(name=body.tenant_name).first()
    if not tenant:
        tenant = Tenant(
            tenant_id=generate_ulid("tnt"),
            name=body.tenant_name,
        )
        db.add(tenant)
        db.flush()

    # Find or create user
    user = db.query(User).filter_by(tenant_id=tenant.tenant_id, username=body.username).first()
    if not user:
        user = User(
            user_id=generate_ulid("usr"),
            tenant_id=tenant.tenant_id,
            username=body.username,
            role="admin",
        )
        db.add(user)
        db.flush()

    db.commit()

    token = create_access_token(
        tenant_id=tenant.tenant_id,
        user_id=user.user_id,
        role=user.role,
    )

    return ApiResponse(
        data=DevLoginResponse(
            access_token=token,
            tenant_id=tenant.tenant_id,
            user_id=user.user_id,
            role=user.role,
        )
    )

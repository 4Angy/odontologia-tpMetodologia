from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app import deps
from app.core.security import AuthUser, require_auth
from app.core.tenancy.repositories import UnitOfWork


def require_tenant(user: AuthUser = Depends(require_auth)) -> AuthUser:
    return user


def get_uow(
    session: Session = Depends(deps.get_session),
    user: AuthUser = Depends(require_auth),
) -> UnitOfWork:
    return UnitOfWork(user.tenant_id, session)


__all__ = ["get_uow", "require_tenant"]

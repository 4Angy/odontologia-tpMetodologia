"""Auth JWT mínima del slice (el auth completo es C-03).

- Tenant SIEMPRE del JWT validado (R2).
- Sin/inválido JWT → 403 (RN-AU-01: sin tenant no hay respuesta útil).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request

JWT_ALG = "HS256"


def _secret() -> str:
    """Secreto del entorno con fallback solo-local para dev/tests."""
    return os.getenv("JWT_SECRET", "dev-secret-cambiar")


@dataclass(frozen=True)
class AuthUser:
    id: str
    tenant_id: str
    roles: tuple


def mint_token(*, user_id: str, tenant_id: str, roles: list) -> str:
    return jwt.encode(
        {"sub": user_id, "tenant_id": tenant_id, "roles": roles}, _secret(), algorithm=JWT_ALG
    )


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"code": "RN-AU-01", "message": "Credenciales inválidas o ausentes."},
    )


def require_auth(request: Request) -> AuthUser:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise _forbidden()
    token = header[len("Bearer "):].strip()
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALG])
        user_id = payload["sub"]
        tenant_id = payload["tenant_id"]
        roles = tuple(payload.get("roles", ()))
    except Exception:
        raise _forbidden() from None
    if not user_id or not tenant_id:
        raise _forbidden()
    return AuthUser(id=user_id, tenant_id=tenant_id, roles=roles)


def require_roles(*permitidos: str):
    """Autorización por unión: basta UN rol permitido (parte de RN-AU-04)."""

    def _check(user: AuthUser = Depends(require_auth)) -> AuthUser:
        if not set(user.roles) & set(permitidos):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "RN-AU-04",
                    "message": "No tenés permiso para esta acción.",
                },
            )
        return user

    return _check

"""Auth JWT del monolito (C-03, reemplaza el stub de C-02).

- Tenant SIEMPRE del JWT validado (R2); sin/inválido JWT → 403 con
  `RN-AU-01` (sin tenant no hay respuesta útil).
- Claims completos: `sub`, `tenant_id`, `roles`, `email`, `jti`, `type`,
  `iat`, `exp` (R7: epoch UTC). Vigencias desde Settings, no hardcode.
- El DTO `TokenClaims` valida con `extra='forbid'` (R4): un claim
  desconocido invalida el token.
- Un token `refresh` presentado como access se rechaza por `type` aun
  cuando la firma sea válida.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.config import get_settings

JWT_ALG = "HS256"

TipoToken = Literal["access", "refresh"]


def _secret() -> str:
    """Secreto de firma desde la configuración validada."""
    return get_settings().jwt_secret_plain()


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"code": "RN-AU-01", "message": "Credenciales inválidas o ausentes."},
    )


class TokenClaims(BaseModel):
    """Claims firmados del JWT (R4: `extra='forbid'` — nada desconocido)."""

    model_config = ConfigDict(extra="forbid")

    sub: str
    tenant_id: str
    roles: list[str] = []
    email: str | None = None
    jti: str
    type: TipoToken
    iat: int
    exp: int


class AuthUser:
    """Usuario autenticado derivado del JWT (id, tenant, roles, email)."""

    __slots__ = ("id", "tenant_id", "roles", "email", "jti")

    def __init__(
        self,
        *,
        id: str,
        tenant_id: str,
        roles: tuple | list,
        email: str | None = None,
        jti: str | None = None,
    ) -> None:
        self.id = id
        self.tenant_id = tenant_id
        self.roles = tuple(roles)
        self.email = email
        self.jti = jti


def mint_token(
    *,
    user_id: str,
    tenant_id: str,
    roles: list,
    email: str | None = None,
    token_type: TipoToken = "access",
    jti: str | None = None,
    now: datetime | None = None,
    ttl_segundos: int | None = None,
) -> str:
    """Firma un JWT con claims completos.

    Vigencias por defecto desde Settings: access `JWT_ACCESS_MIN` minutos,
    refresh `JWT_REFRESH_DAYS` días. `ttl_segundos` permite overrides de test.
    """
    settings = get_settings()
    if ttl_segundos is None:
        ttl_segundos = (
            settings.jwt_refresh_days * 24 * 3600
            if token_type == "refresh"
            else settings.jwt_access_min * 60
        )
    ahora = now or datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "roles": list(roles),
        "email": email,
        "jti": jti or str(uuid.uuid4()),
        "type": token_type,
        "iat": int(ahora.timestamp()),
        "exp": int((ahora + timedelta(seconds=ttl_segundos)).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALG)


def validar_token(token: str, *, tipos: tuple[str, ...] = ("access",)) -> TokenClaims:
    """Decodifica y valida un token: firma, expiración, tipo y claims (R4).

    Devuelve los claims tipados o levanta `HTTPException 403 RN-AU-01`.
    """
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALG])
        claims = TokenClaims.model_validate(payload)
    except jwt.ExpiredSignatureError:
        raise _forbidden() from None
    except (jwt.PyJWTError, ValidationError):
        raise _forbidden() from None
    if claims.type not in tipos:
        raise _forbidden()
    if not claims.sub or not claims.tenant_id:
        raise _forbidden()
    return claims


def require_auth(request: Request) -> AuthUser:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise _forbidden()
    token = header[len("Bearer "):].strip()
    claims = validar_token(token)
    return AuthUser(
        id=claims.sub,
        tenant_id=claims.tenant_id,
        roles=claims.roles,
        email=claims.email,
        jti=claims.jti,
    )


def has_effective_permission(roles: tuple | list | set, *permitidos: str) -> bool:
    """Un usuario tiene permiso si la unión de sus roles incluye alguno de los requeridos."""
    if not permitidos:
        return True
    return bool(set(roles) & set(permitidos))


def require_roles(*permitidos: str):
    """Autorización por unión: basta UN rol permitido (parte de RN-AU-04)."""

    def _check(user: AuthUser = Depends(require_auth)) -> AuthUser:
        if not has_effective_permission(user.roles, *permitidos):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "RN-AU-04",
                    "message": "No tenés permiso para esta acción.",
                },
            )
        return user

    return _check


__all__ = [
    "JWT_ALG",
    "AuthUser",
    "TokenClaims",
    "has_effective_permission",
    "mint_token",
    "require_auth",
    "require_roles",
    "validar_token",
]

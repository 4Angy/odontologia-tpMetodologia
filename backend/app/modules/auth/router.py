"""Router de sesión (C-03): /auth/login, /auth/refresh, /auth/logout, /me, /auth/password-reset.

- Access en el body; refresh SOLO en cookie HttpOnly (secure, samesite=lax,
  path=/auth/refresh) — design decisión 3.
- El tenant SIEMPRE sale del JWT o de la fila del refresh en la DB (R2).
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app import deps
from app.core.rate_limit import InMemoryRateLimiter
from app.core.security import AuthUser, require_auth
from app.modules.auth.schemas import (
    LoginRequest,
    MeResponse,
    ResetConfirmarRequest,
    ResetSolicitudResponse,
    ResetSolicitarRequest,
    TokenResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter()

#: Rate limiter in-memory (singleton para toda la app)
_rate_limiter = InMemoryRateLimiter()

#: Nombre de la cookie de refresh (path acotado al endpoint que la usa).
COOKIE_REFRESH = "refresh_token"


def _setear_cookie_refresh(resp: Response, jti: str, expira: datetime) -> None:
    """Cookie HttpOnly del refresh: secure + samesite=lax + path acotado."""
    resp.set_cookie(
        key=COOKIE_REFRESH,
        value=jti,
        expires=expira,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/auth/refresh",
    )


def _limpiar_cookie(resp: Response) -> None:
    resp.delete_cookie(key=COOKIE_REFRESH, path="/auth/refresh")


@router.post("/auth/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(deps.get_session),
    now_utc: datetime = Depends(deps.get_now),
) -> TokenResponse:
    servicio = AuthService(session, rate_limiter=_rate_limiter)
    client_ip = request.client.host if request.client else None
    emitida = servicio.login(
        email=payload.email,
        password=payload.password,
        tenant_slug=payload.tenant_slug,
        now=now_utc,
        client_ip=client_ip,
    )
    _setear_cookie_refresh(response, emitida.refresh_jti, emitida.refresh_expira)
    return TokenResponse(access_token=emitida.access_token, expires_in=emitida.expires_in)


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    session: Session = Depends(deps.get_session),
    now_utc: datetime = Depends(deps.get_now),
) -> TokenResponse:
    jti = request.cookies.get(COOKIE_REFRESH)
    servicio = AuthService(session)
    emitida = servicio.refresh(refresh_jti=jti or "", now=now_utc)
    _setear_cookie_refresh(response, emitida.refresh_jti, emitida.refresh_expira)
    return TokenResponse(access_token=emitida.access_token, expires_in=emitida.expires_in)


@router.post("/auth/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(deps.get_session),
    now_utc: datetime = Depends(deps.get_now),
) -> Response:
    servicio = AuthService(session)
    servicio.logout(refresh_jti=request.cookies.get(COOKIE_REFRESH), now=now_utc)
    _limpiar_cookie(response)
    return Response(status_code=204)


@router.get("/me", response_model=MeResponse)
def me(
    user: AuthUser = Depends(require_auth),
    session: Session = Depends(deps.get_session),
) -> MeResponse:
    servicio = AuthService(session)
    return MeResponse(**servicio.me(usuario_id=user.id, tenant_id=user.tenant_id))


@router.post("/auth/password-reset", response_model=ResetSolicitudResponse)
def reset_solicitar(
    payload: ResetSolicitarRequest,
    session: Session = Depends(deps.get_session),
    now_utc: datetime = Depends(deps.get_now),
) -> ResetSolicitudResponse:
    servicio = AuthService(session)
    resultado = servicio.reset_solicitar(email=payload.email, now=now_utc)
    return ResetSolicitudResponse(**resultado)


@router.post("/auth/password-reset/confirmar")
def reset_confirmar(
    payload: ResetConfirmarRequest,
    response: Response,
    session: Session = Depends(deps.get_session),
    now_utc: datetime = Depends(deps.get_now),
) -> dict:
    servicio = AuthService(session)
    _limpiar_cookie(response)
    return servicio.reset_confirmar(
        token=payload.token, nueva_password=payload.nueva_password, now=now_utc
    )

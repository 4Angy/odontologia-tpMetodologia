"""Tests de claims JWT completos (Task 1.2). Datos sintéticos (R14)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.security import JWT_ALG, mint_token, validar_token


def _secret() -> str:
    return get_settings().jwt_secret_plain()


def test_mint_token_access_firma_claims_completos():
    token = mint_token(user_id="u-1", tenant_id="t-1", roles=["dueno"], email="u@demo.com")
    claims = jwt.decode(token, _secret(), algorithms=[JWT_ALG])
    assert claims["sub"] == "u-1"
    assert claims["tenant_id"] == "t-1"
    assert claims["roles"] == ["dueno"]
    assert claims["email"] == "u@demo.com"
    assert claims["type"] == "access"
    assert claims["jti"]  # hay un identificador de token
    assert claims["exp"] - claims["iat"] == get_settings().jwt_access_min * 60


def test_mint_token_refresh_vigencia_de_configuration():
    token = mint_token(user_id="u-1", tenant_id="t-1", roles=[], token_type="refresh")
    claims = jwt.decode(token, _secret(), algorithms=[JWT_ALG])
    diferencia = claims["exp"] - claims["iat"]
    assert diferencia == get_settings().jwt_refresh_days * 24 * 3600


def test_require_auth_rechaza_refresh_usado_como_access():
    token = mint_token(user_id="u-1", tenant_id="t-1", roles=["dueno"], token_type="refresh")
    with pytest.raises(HTTPException) as exc:
        validar_token(token)
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "RN-AU-01"


def test_validar_token_tambien_acepta_refresh_cuando_corresponde():
    """El endpoint de refresh es el único que pide token tipo refresh."""
    token = mint_token(user_id="u-1", tenant_id="t-1", roles=[], token_type="refresh")
    claims = validar_token(token, tipos=("refresh",))
    assert claims.type == "refresh"


def test_require_auth_rechaza_token_expirado():
    token = mint_token(
        user_id="u-1",
        tenant_id="t-1",
        roles=[],
        now=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    with pytest.raises(HTTPException) as exc:
        validar_token(token)
    assert exc.value.status_code == 403


def test_reject_claim_extra_no_declarado():
    """DTO con extra=forbid: un claim desconocido no valida (R4, variante)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "u-1",
        "tenant_id": "t-1",
        "roles": [],
        "jti": str(uuid.uuid4()),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "is_admin": True,  # claim desconocido: forbidden
    }
    token = jwt.encode(payload, _secret(), algorithm=JWT_ALG)
    with pytest.raises(HTTPException) as exc:
        validar_token(token)
    assert exc.value.status_code == 403

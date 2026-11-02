"""Tests de API: POST /auth/login (Task 2.2) — rojo primero (R11).

Datos sintéticos (R14); Postgres real via conftest de backend/.
"""
from __future__ import annotations

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import JWT_ALG
from app.main import create_app
from app.modules.agenda.models import TenantModel, UsuarioModel
from app.modules.auth.passwords import hash_password

TENANT = "t-login"
EMAIL = "duena@demo.com"
PASSWORD = "Correcta-Horse-Battery-01"


@pytest.fixture()
def setup_db(session_factory):  # noqa: ANN201
    s = session_factory()
    s.add(TenantModel(id=TENANT, nombre="Demo", slug="demo"))
    s.flush()
    s.add(
        UsuarioModel(
            id="u-1",
            tenant_id=TENANT,
            email=EMAIL,
            password_hash=hash_password(PASSWORD),
            roles=["dueno", "recepcion"],
        )
    )
    s.add(
        UsuarioModel(
            id="u-inactivo",
            tenant_id=TENANT,
            email="inactivo@demo.com",
            password_hash=hash_password(PASSWORD),
            roles=["recepcion"],
            activo=False,
        )
    )
    s.commit()
    s.close()
    return session_factory


@pytest.fixture()
def client(setup_db):  # noqa: ANN201
    app = create_app(session_factory=setup_db)
    return TestClient(app)


def _body(email=EMAIL, password=PASSWORD):  # noqa: ANN201
    return {"email": email, "password": password}


def test_login_valido_200_emite_pareja(client):
    r = client.post("/auth/login", json=_body())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    claims = jwt.decode(
        body["access_token"], get_settings().jwt_secret_plain(), algorithms=[JWT_ALG]
    )
    assert claims["sub"] == "u-1"
    assert claims["tenant_id"] == TENANT
    assert claims["email"] == EMAIL
    assert claims["roles"] == ["dueno", "recepcion"]
    assert claims["type"] == "access"
    # refresh NUNCA viaja en el body: va por cookie HttpOnly
    assert "refresh_token" not in body


def test_login_cookie_refresh_httponly_path_samesite(client):
    r = client.post("/auth/login", json=_body())
    cookie_header = r.headers.get("set-cookie", "")
    assert cookie_header.startswith("refresh_token=")
    assert "HttpOnly" in cookie_header
    assert "Secure" in cookie_header
    assert "SameSite=lax" in cookie_header
    assert "Path=/auth/refresh" in cookie_header


def test_login_credenciales_invalidas_401_misma_respuesta(client):
    """Anti-enumeración: password incorrecta e email inexistente → mismo 401."""
    r_password = client.post("/auth/login", json=_body(password="incorrecta"))
    r_email = client.post("/auth/login", json=_body(email="nadie@demo.com"))
    for respuesta in (r_password, r_email):
        assert respuesta.status_code == 401, respuesta.text
        assert respuesta.json()["code"] == "RN-AU-01"
        assert respuesta.json()["message"] == r_password.json()["message"]


def test_login_usuario_inactivo_403(client):
    r = client.post("/auth/login", json=_body(email="inactivo@demo.com"))
    assert r.status_code == 403, r.text
    body = r.json()
    assert "dueño" in body["message"].lower() or "responsable" in body["message"].lower()


def test_login_password_vacia_422(client):
    r = client.post("/auth/login", json={"email": EMAIL, "password": ""})
    assert r.status_code == 422, r.text


def test_login_campos_desconocidos_rechazados(client):
    """DTO con extra=forbid (R4)."""
    r = client.post("/auth/login", json={**_body(), "tenant_id": "t-otro"})
    assert r.status_code == 422, r.text

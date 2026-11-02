"""Tests de API: refresh, logout y /me (Tasks 2.3–2.5).

El refresh viaja por cookie HttpOnly Secure; en TestClient (http) se envía
manualmente por header `Cookie`, que es exactamente lo que hará el browser.
"""
from __future__ import annotations

import re
import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import JWT_ALG
from app.main import create_app
from app.modules.agenda.models import TenantModel, UsuarioModel
from app.modules.auth.passwords import hash_password

TENANT = "t-session"
EMAIL = "multi@demo.com"
PASSWORD = "Otra-Pass-Demo-22"


@pytest.fixture()
def setup_db(session_factory):  # noqa: ANN201
    s = session_factory()
    s.add(TenantModel(id=TENANT, nombre="Demo", slug="demo"))
    s.flush()
    s.add(UsuarioModel(
        id="u-multi", tenant_id=TENANT, email=EMAIL,
        password_hash=hash_password(PASSWORD), roles=["dueno", "recepcion"],
    ))
    s.add(UsuarioModel(
        id="u-off", tenant_id=TENANT, email="off@demo.com",
        password_hash=hash_password(PASSWORD), roles=["recepcion"],
    ))
    s.commit()
    s.close()
    return session_factory


@pytest.fixture()
def client(setup_db):  # noqa: ANN201
    return TestClient(create_app(session_factory=setup_db))


def _jti_de_cookie(header: str) -> str:
    m = re.search(r"refresh_token=([^;]+)", header)
    assert m, header
    return m.group(1)


def _login(client) -> tuple[TestClient, str, dict]:
    r = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200, r.text
    jti = _jti_de_cookie(r.headers.get("set-cookie", ""))
    return jti, r.json()


def _refresh_headers(jti: str) -> dict:
    return {"Cookie": f"refresh_token={jti}"}


# --- Task 2.3: refresh ---------------------------------------------------------------


def test_refresh_rota_y_emite_nueva_pareja(client):
    jti, body = _login(client)
    r = client.post("/auth/refresh", headers=_refresh_headers(jti))
    assert r.status_code == 200, r.text
    nuevo = jwt.decode(
        r.json()["access_token"], get_settings().jwt_secret_plain(), algorithms=[JWT_ALG]
    )
    assert nuevo["sub"] == "u-multi"
    assert nuevo["tenant_id"] == TENANT
    nuevo_jti = _jti_de_cookie(r.headers.get("set-cookie", ""))
    assert nuevo_jti != jti  # rotación: siempre un jti nuevo


def test_reuse_de_refresh_revoca_toda_la_familia(client):
    jti_viejo, _ = _login(client)
    r1 = client.post("/auth/refresh", headers=_refresh_headers(jti_viejo))
    assert r1.status_code == 200
    jti_nuevo = _jti_de_cookie(r1.headers.get("set-cookie", ""))

    # reuse del viejo: familia completa al suelo (RN-AU-02)
    r2 = client.post("/auth/refresh", headers=_refresh_headers(jti_viejo))
    assert r2.status_code == 401, r2.text
    assert r2.json()["code"] == "RN-AU-02"

    # el más nuevo de esa familia también queda muerto
    r3 = client.post("/auth/refresh", headers=_refresh_headers(jti_nuevo))
    assert r3.status_code == 401, r3.text


def test_refresh_cookie_ausente_401(client):
    r = client.post("/auth/refresh")
    assert r.status_code == 401, r.text
    assert r.json()["code"] == "RN-AU-02"


def test_refresh_de_usuario_desactivado_rechaza_403(client):
    """Inactividad revoca el acceso en la próxima rotación (spec RN-AU-04 borde)."""
    jti, _ = _login(client)
    s = client.app.state.session_factory()
    usuario = s.get(UsuarioModel, "u-multi")
    usuario.activo = False
    s.commit()
    s.close()
    r = client.post("/auth/refresh", headers=_refresh_headers(jti))
    assert r.status_code == 403, r.text
    assert "inactivo" in r.json()["message"].lower()


# --- Task 2.4: logout ----------------------------------------------------------------


def test_logout_invalida_la_familia(client):
    jti, _ = _login(client)
    r = client.post("/auth/logout", headers=_refresh_headers(jti))
    assert r.status_code == 204, r.text
    r2 = client.post("/auth/refresh", headers=_refresh_headers(jti))
    assert r2.status_code == 401, r2.text


def test_logout_sin_cookie_es_idempotente(client):
    r = client.post("/auth/logout")
    assert r.status_code == 204, r.text


# --- Task 2.5: /me -------------------------------------------------------------------


def test_me_devuelve_roles_y_union(client):
    jti, body = _login(client)
    r = client.get("/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["sub"] == "u-multi"
    assert data["roles"] == ["dueno", "recepcion"]
    assert data["permisos"] == ["dueno", "recepcion"]  # unión ordenada


def test_me_sin_token_403(client):
    r = client.get("/me")
    assert r.status_code == 403
    assert r.json()["code"] == "RN-AU-01"

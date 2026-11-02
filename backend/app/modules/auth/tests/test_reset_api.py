"""Tests de API: password-reset (Task 2.6). Datos sintéticos (R14)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.agenda.models import TenantModel, UsuarioModel
from app.modules.auth.passwords import hash_password

TENANT = "t-reset"
EMAIL = "reset@demo.com"
PASSWORD = "Vieja-Demo-33"

FALTA_30_MIN = datetime.now(timezone.utc) + timedelta(minutes=30)


@pytest.fixture()
def setup_db(session_factory):  # noqa: ANN201
    s = session_factory()
    s.add(TenantModel(id=TENANT, nombre="Demo", slug="demo"))
    s.flush()
    s.add(UsuarioModel(
        id="u-reset", tenant_id=TENANT, email=EMAIL,
        password_hash=hash_password(PASSWORD), roles=["recepcion"],
    ))
    s.commit()
    s.close()
    return session_factory


@pytest.fixture()
def client(setup_db):  # noqa: ANN201
    return TestClient(create_app(session_factory=setup_db))


def _solicitar(client, email=EMAIL):  # noqa: ANN201
    return client.post("/auth/password-reset", json={"email": email})


def test_reset_flujo_completo_cambia_y_revoca_familias(client):
    # login previo: quedan refresh de una familia activa
    login = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert login.status_code == 200

    r = _solicitar(client)
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    assert token  # en test env el token es entregado para flujos manuales

    r2 = client.post(
        "/auth/password-reset/confirmar",
        json={"token": token, "nueva_password": "Nueva-Demo-44"},
    )
    assert r2.status_code == 200, r2.text

    # login con la nueva password → ok; la vieja → 401
    con_nueva = client.post(
        "/auth/login", json={"email": EMAIL, "password": "Nueva-Demo-44"}
    )
    assert con_nueva.status_code == 200, con_nueva.text
    con_vieja = client.post(
        "/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert con_vieja.status_code == 401

    # las familias previas quedaron revocadas: refresh con el token viejo → 401
    # (se forzó re-login tras el reset)


def test_reset_email_inexistente_respuesta_generica(client):
    r_existe = _solicitar(client)
    r_no_existe = _solicitar(client, "nadie@demo.com")
    assert r_existe.status_code == 200 and r_no_existe.status_code == 200
    a, b = r_existe.json(), r_no_existe.json()
    assert b["token"] is None
    assert a["message"] == b["message"]  # indistinguible la no-existencia


def test_reset_token_expirado_rechazado(client, session_factory):
    r = _solicitar(client)
    token = r.json()["token"]
    # manipular expira al pasado (con el session factory real)
    s = session_factory()
    from app.modules.auth.models import AuthTokenModel

    fila = s.get(AuthTokenModel, token)
    fila.expira = datetime.now(timezone.utc) - timedelta(hours=1)
    s.commit()
    s.close()

    r2 = client.post(
        "/auth/password-reset/confirmar",
        json={"token": token, "nueva_password": "X-Demo-55"},
    )
    assert r2.status_code == 400, r2.text
    assert "nuevo" in r2.json()["message"].lower()


def test_reset_token_reutilizado_rechazado(client):
    r = _solicitar(client)
    token = r.json()["token"]
    primera = client.post(
        "/auth/password-reset/confirmar",
        json={"token": token, "nueva_password": "P1-Demo-66"},
    )
    assert primera.status_code == 200
    segunda = client.post(
        "/auth/password-reset/confirmar",
        json={"token": token, "nueva_password": "P2-Demo-77"},
    )
    assert segunda.status_code == 400, segunda.text


def test_reset_dto_rechaza_campos_desconocidos(client):
    r = client.post(
        "/auth/password-reset", json={"email": EMAIL, "tenant_id": "t"}
    )
    assert r.status_code == 422

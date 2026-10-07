"""Tests de API: GET/PUT /config (Task 3.5, RED primero). Datos sintéticos (R14)."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.core.security import mint_token
from app.modules.agenda.models import Base, ConfigModel, TenantModel, TurnoModel

TENANT_A = "tenant-demo-a"
AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    s.add(TenantModel(id=TENANT_A, nombre="Demo A"))
    s.add(ConfigModel(tenant_id=TENANT_A, antelacion_cancel_hs=24))
    s.add(TurnoModel(
        id="turno-medio", tenant_id=TENANT_A, paciente_id="pac-1",
        profesional_id="prof-1", profesional_usuario_id="user-odonto-1",
        inicio=AHORA + timedelta(hours=30), fin=AHORA + timedelta(hours=30, minutes=30),
        estado="confirmado",
    ))
    s.commit()
    s.close()
    return TestClient(create_app(session_factory=Session, now_fn=lambda: AHORA))


def _auth(user_id, roles):
    return {"Authorization": f"Bearer {mint_token(user_id=user_id, tenant_id=TENANT_A, roles=list(roles))}"}


def test_config_dueno_actualiza_y_rige_futuro_no_retroactivo(client):
    r = client.put("/config", json={"antelacion_cancel_hs": 48},
                   headers=_auth("u-dueno", ("dueno",)))
    assert r.status_code == 200, r.text
    assert r.json()["antelacion_cancel_hs"] == 48

    # Rige a futuro: turno a 30h ahora queda fuera de término (48h).
    rc = client.post("/turnos/turno-medio/cancelar", json={"motivo": "x"},
                     headers=_auth("u-recep", ("recepcion",)))
    assert rc.status_code == 409
    assert rc.json()["code"] == "RN-AG-01"

    # Cancelaciones ya efectuadas no cambian: cancelamos otro en término con 0h.
    r0 = client.put("/config", json={"antelacion_cancel_hs": 0},
                    headers=_auth("u-dueno", ("dueno",)))
    assert r0.status_code == 200
    rc2 = client.post("/turnos/turno-medio/cancelar", json={"motivo": "ok"},
                      headers=_auth("u-recep", ("recepcion",)))
    assert rc2.status_code == 200, rc2.text


def test_config_no_dueno_403(client):
    r = client.put("/config", json={"antelacion_cancel_hs": 5},
                   headers=_auth("u-recep", ("recepcion",)))
    assert r.status_code == 403, r.text


def test_config_negativo_422(client):
    r = client.put("/config", json={"antelacion_cancel_hs": -1},
                   headers=_auth("u-dueno", ("dueno",)))
    assert r.status_code == 422, r.text
    # ...y el valor previo sigue intacto.
    g = client.get("/config", headers=_auth("u-dueno", ("dueno",)))
    assert g.json()["antelacion_cancel_hs"] == 24


def test_config_get_visible_cero_valido(client):
    client.put("/config", json={"antelacion_cancel_hs": 0},
               headers=_auth("u-dueno", ("dueno",)))
    g = client.get("/config", headers=_auth("u-recep", ("recepcion",)))
    assert g.status_code == 200
    assert g.json()["antelacion_cancel_hs"] == 0

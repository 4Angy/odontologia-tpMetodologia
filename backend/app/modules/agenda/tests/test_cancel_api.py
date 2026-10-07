"""Tests de API: POST /turnos/:id/cancelar (Task 3.1, RED primero).

TDD estricto, datos sintéticos (R14). TestClient + SQLite en memoria.
"""
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
        id="turno-ok", tenant_id=TENANT_A, paciente_id="pac-1",
        profesional_id="prof-1", profesional_usuario_id="user-odonto-1",
        inicio=AHORA + timedelta(hours=48), fin=AHORA + timedelta(hours=48, minutes=30),
        estado="confirmado",
    ))
    s.add(TurnoModel(
        id="turno-cerca", tenant_id=TENANT_A, paciente_id="pac-1",
        profesional_id="prof-1", profesional_usuario_id="user-odonto-1",
        inicio=AHORA + timedelta(hours=2), fin=AHORA + timedelta(hours=2, minutes=30),
        estado="confirmado",
    ))
    s.add(TurnoModel(
        id="turno-pasado", tenant_id=TENANT_A, paciente_id="pac-1",
        profesional_id="prof-1", profesional_usuario_id="user-odonto-1",
        inicio=AHORA - timedelta(hours=1), fin=AHORA - timedelta(minutes=30),
        estado="confirmado",
    ))
    s.commit()
    s.close()

    app = create_app(session_factory=Session, now_fn=lambda: AHORA)
    return TestClient(app)


def _token(user_id="user-recep-1", roles=("recepcion",), tenant=TENANT_A):
    return mint_token(user_id=user_id, tenant_id=tenant, roles=list(roles))


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_api_cancel_en_termino_200_cancelado(client):
    r = client.post("/turnos/turno-ok/cancelar", json={"motivo": "Paciente avisa"},
                    headers=_auth(_token()))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["estado"] == "cancelado"
    assert body["motivo"] == "Paciente avisa"
    assert body["cancelled_by"] == "user-recep-1"
    assert body["senia_pendiente_definicion"] is False


def test_api_cancel_fuera_de_termino_409_rn_ag_01_con_action(client):
    r = client.post("/turnos/turno-cerca/cancelar", json={"motivo": "x"},
                    headers=_auth(_token()))
    assert r.status_code == 409, r.text
    body = r.json()
    assert body["code"] == "RN-AG-01"
    assert body["message"]  # español-AR mostrable
    assert body["action"]["type"] == "reprogramar"
    assert body["action"]["hint"]


def test_api_cancel_turno_pasado_409(client):
    r = client.post("/turnos/turno-pasado/cancelar", json={"motivo": "x"},
                    headers=_auth(_token()))
    assert r.status_code == 409, r.text
    assert r.json()["code"]

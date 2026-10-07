"""Tests de API: RBAC por unión + aislamiento (Task 3.3, RED primero).

4 casos RBAC + 3 de aislamiento. Datos sintéticos (R14).
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
TENANT_B = "tenant-demo-b"
AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    for t in (TENANT_A, TENANT_B):
        s.add(TenantModel(id=t, nombre=t))
        s.add(ConfigModel(tenant_id=t, antelacion_cancel_hs=24))
    s.add(TurnoModel(
        id="turno-ajeno", tenant_id=TENANT_A, paciente_id="pac-1",
        profesional_id="prof-otro", profesional_usuario_id="user-odonto-otro",
        inicio=AHORA + timedelta(hours=48), fin=AHORA + timedelta(hours=48, minutes=30),
        estado="confirmado",
    ))
    s.add(TurnoModel(
        id="turno-huerfano", tenant_id=TENANT_A, paciente_id="pac-1",
        profesional_id="prof-sin-user", profesional_usuario_id=None,
        inicio=AHORA + timedelta(hours=48), fin=AHORA + timedelta(hours=48, minutes=30),
        estado="confirmado",
    ))
    s.add(TurnoModel(
        id="turno-b", tenant_id=TENANT_B, paciente_id="pac-1",
        profesional_id="prof-1", profesional_usuario_id="user-odonto-1",
        inicio=AHORA + timedelta(hours=48), fin=AHORA + timedelta(hours=48, minutes=30),
        estado="confirmado",
    ))
    s.commit()
    s.close()
    return TestClient(create_app(session_factory=Session, now_fn=lambda: AHORA))


def _auth(user_id, roles, tenant=TENANT_A):
    token = mint_token(user_id=user_id, tenant_id=tenant, roles=list(roles))
    return {"Authorization": f"Bearer {token}"}


def test_rbac_sin_permiso_403(client):
    r = client.post("/turnos/turno-ajeno/cancelar", json={"motivo": "x"},
                    headers=_auth("u-pac", ("paciente",)))
    assert r.status_code == 403, r.text


def test_rbac_odontologo_solo_sus_turnos(client):
    # Turno de otro profesional → 403.
    r = client.post("/turnos/turno-ajeno/cancelar", json={"motivo": "x"},
                    headers=_auth("user-odonto-1", ("odontologo",)))
    assert r.status_code == 403, r.text
    # Turno propio → 200. (Lo crea el fixture? No: ajeno es de otro; propio = huerfano? No.)
    # Propio: turno-b es de user-odonto-1 pero en TENANT_B; con JWT de A → 404.
    # Para el caso propio positivo usamos turno-ajeno con el dueño del turno:
    r2 = client.post("/turnos/turno-ajeno/cancelar", json={"motivo": "soy su odonto"},
                     headers=_auth("user-odonto-otro", ("odontologo",)))
    assert r2.status_code == 200, r2.text


def test_rbac_union_multirol_cancela_via_recepcion(client):
    r = client.post("/turnos/turno-huerfano/cancelar", json={"motivo": "union"},
                    headers=_auth("user-multi", ("recepcion", "odontologo")))
    assert r.status_code == 200, r.text


def test_rbac_profesional_usuario_null_403_con_code(client):
    r = client.post("/turnos/turno-huerfano/cancelar", json={"motivo": "x"},
                    headers=_auth("user-odonto-9", ("odontologo",)))
    assert r.status_code == 403, r.text
    assert r.json()["code"]


def test_aislamiento_inexistente_y_cross_tenant_404_identico(client):
    h = _auth("user-recep-1", ("recepcion",))
    r1 = client.post("/turnos/no-existe/cancelar", json={"motivo": "x"}, headers=h)
    r2 = client.post("/turnos/turno-b/cancelar", json={"motivo": "x"}, headers=h)
    assert r1.status_code == 404 and r2.status_code == 404
    assert r1.json() == r2.json(), "indistinguible: sin fuga por enumeración"


def test_aislamiento_sin_jwt_o_invalido_403(client):
    r1 = client.post("/turnos/turno-ajeno/cancelar", json={"motivo": "x"})
    assert r1.status_code == 403, r1.text
    r2 = client.post("/turnos/turno-ajeno/cancelar", json={"motivo": "x"},
                     headers={"Authorization": "Bearer invalido"})
    assert r2.status_code == 403, r2.text

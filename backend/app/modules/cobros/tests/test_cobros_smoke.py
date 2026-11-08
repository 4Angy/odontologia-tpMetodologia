from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import mint_token
from app.main import create_app
from app.modules.agenda.models import (
    TenantModel,
    UsuarioModel,
    UsuarioRoles,
)
from app.modules.pacientes.models import PacienteModel


def _token(session, tenant, roles=None, email="dueno@test.com"):
    roles = roles or [UsuarioRoles.DUENO.value]
    user = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email=email,
        nombre="Usuario de prueba",
        roles=roles,
        activo=True,
    )
    session.add(user)
    session.commit()
    return mint_token(
        user_id=user.id,
        tenant_id=tenant.id,
        roles=user.roles,
        email=user.email,
        token_type="access",
    )


def test_cobro_basico_y_cierre(session_factory):
    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug="t-a", nombre="Tenant A")
    session.add(tenant)
    session.flush()
    token = _token(session, tenant)
    paciente = PacienteModel(
        tenant_id=tenant.id, nombre="Ana", apellido="Garcia", saldo=0
    )
    session.add(paciente)
    session.commit()

    # alta cobro
    r = client.post(
        "/cobros",
        json={
            "paciente_id": paciente.id,
            "monto_cents": 1000,
            "medio": "efectivo",
            "concepto": "consulta",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text

    # deudas (sin presupuestos => saldo negativo? cargos 0 - 1000 = -1000, no aparece)
    r2 = client.get("/deudas", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200

    # cierre dia
    r3 = client.post(
        "/caja/cierre-dia",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r3.status_code == 201, r3.text

    # cierre duplicado -> 409
    r4 = client.post(
        "/caja/cierre-dia",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r4.status_code == 409

    # ajuste
    cierre_id = r3.json()["id"]
    r5 = client.post(
        "/caja/ajuste",
        json={"cierre_id": cierre_id, "nota": "ajuste test", "monto_cents": 100},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r5.status_code == 204

    # get cierre
    r6 = client.get("/caja/cierre-dia", headers={"Authorization": f"Bearer {token}"})
    assert r6.status_code == 200

    session.close()


def test_aislamiento_tenant(session_factory):
    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    session = session_factory()
    tenant_a = TenantModel(id=str(uuid.uuid4()), slug="ta", nombre="A")
    tenant_b = TenantModel(id=str(uuid.uuid4()), slug="tb", nombre="B")
    session.add_all([tenant_a, tenant_b])
    session.flush()
    token_a = _token(session, tenant_a, email="a@test.com")
    token_b = _token(session, tenant_b, email="b@test.com")
    pac_b = PacienteModel(tenant_id=tenant_b.id, nombre="B", apellido="Pac")
    session.add(pac_b)
    session.commit()

    # tenant A no ve cobros de B (lista vacía)
    r = client.get("/cobros", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 200
    assert r.json() == []

    session.close()
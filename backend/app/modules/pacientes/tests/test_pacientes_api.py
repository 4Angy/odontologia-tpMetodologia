from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import mint_token
from app.main import create_app
from app.modules.agenda.models import TenantModel, UsuarioModel, UsuarioRoles


def _token(session: Session, tenant: TenantModel, email: str = "dueno@test.com") -> str:
    user = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email=email,
        nombre="Dueño",
        roles=[UsuarioRoles.DUENO.value],
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


def test_crear_y_listar_pacientes_por_tenant(session_factory):
    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug="tenant-a", nombre="Tenant A")
    tenant_b = TenantModel(id=str(uuid.uuid4()), slug="tenant-b", nombre="Tenant B")
    session.add_all([tenant, tenant_b])
    session.flush()
    token_a = _token(session, tenant)
    token_b = _token(session, tenant_b, email="dueno-b@test.com")

    payload = {
        "nombre": "Ana",
        "apellido": "García",
        "dni": "30111222",
        "telefono": "+5491123456789",
        "email": "ana@example.com",
    }
    r1 = client.post("/pacientes", json=payload, headers={"Authorization": f"Bearer {token_a}"})
    assert r1.status_code == 201, r1.text
    assert r1.json()["apellido"] == "García"

    r2 = client.get("/pacientes", headers={"Authorization": f"Bearer {token_a}"})
    assert r2.status_code == 200, r2.text
    assert len(r2.json()) == 1

    r3 = client.get("/pacientes", headers={"Authorization": f"Bearer {token_b}"})
    assert r3.status_code == 200, r3.text
    assert r3.json() == []

    session.close()


def test_optin_whatsapp_requiere_telefono_y_aisla_por_tenant(session_factory):
    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug="tenant-c", nombre="Tenant C")
    session.add(tenant)
    session.flush()
    token = _token(session, tenant)

    paciente = {
        "nombre": "Luis",
        "apellido": "Pérez",
        "dni": "22333444",
        "telefono": "+5491165432198",
        "email": "luis@example.com",
    }
    create = client.post("/pacientes", json=paciente, headers={"Authorization": f"Bearer {token}"})
    paciente_id = create.json()["id"]

    r1 = client.put(
        f"/pacientes/{paciente_id}/optins",
        json={"canal": "whatsapp", "estado": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["canal"] == "whatsapp"
    assert r1.json()["estado"] is True

    paciente_sin_telefono = client.post(
        "/pacientes",
        json={"nombre": "Marta", "apellido": "Díaz", "dni": "33444555", "email": "marta@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert paciente_sin_telefono.status_code == 201, paciente_sin_telefono.text
    patient_id = paciente_sin_telefono.json()["id"]

    r2 = client.put(
        f"/pacientes/{patient_id}/optins",
        json={"canal": "whatsapp", "estado": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 422, r2.text
    assert "telefono" in r2.json()["message"]

    session.close()


def test_import_csv_y_export_pacientes(session_factory):
    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug="tenant-d", nombre="Tenant D")
    session.add(tenant)
    session.flush()
    token = _token(session, tenant)

    csv_text = (
        "nombre,apellido,dni,telefono,email\n"
        "Ana,García,30111222,+5491123456789,ana@example.com\n"
        "Ana,García,30111222,+5491123456789,ana@example.com\n"
        "Marta,Díaz,33444555,,marta@example.com\n"
    )
    r = client.post(
        "/pacientes/import-csv",
        content=csv_text,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["importadas"] == 2
    assert r.json()["duplicadas"] == 1

    export = client.get("/export/pacientes.csv", headers={"Authorization": f"Bearer {token}"})
    assert export.status_code == 200, export.text
    body = export.text
    assert "Ana" in body
    assert "Marta" in body

    session.close()


def test_evolucion_y_presupuesto_alimentan_ficha(session_factory):
    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug="tenant-e", nombre="Tenant E")
    session.add(tenant)
    session.flush()
    token = _token(session, tenant)

    paciente = client.post(
        "/pacientes",
        json={"nombre": "Lucía", "apellido": "Pérez", "dni": "40111222", "telefono": "+5491155556666", "email": "lucia@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    paciente_id = paciente.json()["id"]

    evo = client.post(
        f"/pacientes/{paciente_id}/evoluciones",
        json={"motivo": "Control", "detalle": "Se observa mejora", "firma_simple": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert evo.status_code == 201, evo.text
    assert evo.json()["motivo"] == "Control"
    assert evo.json()["firma_simple"] is True

    list_evo = client.get(f"/pacientes/{paciente_id}/evoluciones", headers={"Authorization": f"Bearer {token}"})
    assert list_evo.status_code == 200, list_evo.text
    assert len(list_evo.json()) == 1

    presupuesto = client.post(
        f"/pacientes/{paciente_id}/presupuestos",
        json={"items": [{"descripcion": "Limpieza", "monto_cents": 15000}, {"descripcion": "Blanqueamiento", "monto_cents": 25000}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert presupuesto.status_code == 201, presupuesto.text
    assert presupuesto.json()["total_cents"] == 40000

    paciente_actualizado = client.get(f"/pacientes/{paciente_id}", headers={"Authorization": f"Bearer {token}"})
    assert paciente_actualizado.json()["saldo"] == 40000

    session.close()


def test_adjunto_rechaza_archivo_grande(session_factory):
    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    session = session_factory()
    tenant = TenantModel(id=str(uuid.uuid4()), slug="tenant-f", nombre="Tenant F")
    session.add(tenant)
    session.flush()
    token = _token(session, tenant)

    paciente = client.post(
        "/pacientes",
        json={"nombre": "Nora", "apellido": "Santos", "dni": "33445566", "telefono": "+5491166667777", "email": "nora@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    paciente_id = paciente.json()["id"]

    r = client.post(
        f"/pacientes/{paciente_id}/adjuntos",
        json={"nombre": "foto.png", "tipo": "image/png", "tamano_bytes": 11_000_000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422, r.text
    assert "10 MB" in r.json()["message"]

    session.close()

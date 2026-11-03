from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import create_app
from app.core.security import mint_token
from app.modules.agenda.models import TenantModel, UsuarioModel


def _auth(session, tenant_id, email="dueno@test.com", roles=("dueno",)):
    user = UsuarioModel(
        id="u-1",
        tenant_id=tenant_id,
        email=email,
        nombre="Dueño",
        roles=[r for r in roles],
        activo=True,
    )
    session.add(user)
    session.commit()
    return {"Authorization": f"Bearer {mint_token(user_id=user.id, tenant_id=tenant_id, roles=user.roles, email=user.email, token_type='access')}"}


def test_catalogo_agenda_base_crud(session_factory):
    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    session = session_factory()
    tenant = TenantModel(id="tenant-06", slug="tenant-06", nombre="Tenant 06")
    session.add(tenant)
    session.flush()
    headers = _auth(session, tenant.id)

    prof = client.post(
        "/profesionales",
        json={"nombre": "Dra. Gómez", "usuario_id": "u-odonto-1", "color_agenda": "#123456", "activo": True},
        headers=headers,
    )
    assert prof.status_code == 201, prof.text
    profesional_id = prof.json()["id"]

    prest = client.post(
        "/prestaciones",
        json={"nombre": "Limpieza", "duracion_min": 30, "precio_ref": 15000, "activa": True},
        headers=headers,
    )
    assert prest.status_code == 201, prest.text
    prestacion_id = prest.json()["id"]

    bloqueo = client.post(
        "/bloqueos",
        json={
            "profesional_id": profesional_id,
            "inicio": "2026-11-02T10:00:00+00:00",
            "fin": "2026-11-02T11:00:00+00:00",
            "motivo": "Mantenimiento",
        },
        headers=headers,
    )
    assert bloqueo.status_code == 201, bloqueo.text
    assert bloqueo.json()["motivo"] == "Mantenimiento"

    lista = client.get("/profesionales", headers=headers)
    assert lista.status_code == 200
    assert len(lista.json()) == 1

    cfg = client.get("/config", headers=headers)
    assert cfg.status_code == 200, cfg.text
    assert cfg.json()["antelacion_cancel_hs"] >= 0

    session.close()


def test_config_reserva_rechaza_negativo(session_factory):
    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    session = session_factory()
    tenant = TenantModel(id="tenant-07", slug="tenant-07", nombre="Tenant 07")
    session.add(tenant)
    session.flush()
    headers = _auth(session, tenant.id)

    r = client.put(
        "/config",
        json={"antelacion_cancel_hs": 24, "antelacion_reserva_hs": -1},
        headers=headers,
    )
    assert r.status_code == 422, r.text

    session.close()

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.core.audit import AuditEventModel
from app.core.security import mint_token
from app.main import create_app
from app.modules.agenda.models import (
    BloqueoModel,
    PrestacionModel,
    ProfesionalModel,
    TenantModel,
    UsuarioModel,
    UsuarioRoles,
)


def _owner(session, slug: str) -> tuple[TenantModel, dict[str, str]]:
    tenant_id = str(uuid.uuid4())
    tenant = TenantModel(
        id=tenant_id,
        slug=slug,
        nombre="Consultorio sintético",
    )
    user = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        email=f"owner-{slug}@example.test",
        nombre="Dueño sintético",
        roles=[UsuarioRoles.DUENO.value],
        activo=True,
    )
    session.add_all([tenant, user])
    session.commit()
    token = mint_token(
        user_id=user.id,
        tenant_id=tenant.id,
        roles=user.roles,
        email=user.email,
        token_type="access",
    )
    return tenant, {"Authorization": f"Bearer {token}"}


def test_bloqueo_rechaza_profesional_de_otro_tenant(session_factory):
    session = session_factory()
    tenant, headers = _owner(session, "c06-owner")
    other_tenant, _ = _owner(session, "c06-other")
    own_professional = ProfesionalModel(
        tenant_id=tenant.id,
        nombre="Profesional propio",
    )
    foreign_professional = ProfesionalModel(
        tenant_id=other_tenant.id,
        nombre="Profesional ajeno",
    )
    session.add_all([own_professional, foreign_professional])
    session.commit()
    tenant_id = tenant.id
    own_id = own_professional.id
    foreign_id = foreign_professional.id
    session.close()

    client = TestClient(create_app(session_factory=session_factory))
    response = client.post(
        "/bloqueos",
        json={
            "profesional_id": foreign_id,
            "inicio": "2026-11-02T10:00:00+00:00",
            "fin": "2026-11-02T11:00:00+00:00",
        },
        headers=headers,
    )
    missing = client.post(
        "/bloqueos",
        json={
            "profesional_id": "profesional-inexistente-sintetico",
            "inicio": "2026-11-02T10:00:00+00:00",
            "fin": "2026-11-02T11:00:00+00:00",
        },
        headers=headers,
    )
    own_block = client.post(
        "/bloqueos",
        json={
            "profesional_id": own_id,
            "inicio": "2026-11-02T10:00:00+00:00",
            "fin": "2026-11-02T11:00:00+00:00",
        },
        headers=headers,
    )
    update_foreign = client.put(
        f"/bloqueos/{own_block.json()['id']}",
        json={
            "profesional_id": foreign_id,
            "inicio": "2026-11-02T10:00:00+00:00",
            "fin": "2026-11-02T11:00:00+00:00",
        },
        headers=headers,
    )

    check = session_factory()
    try:
        assert response.status_code == 404
        assert response.json()["code"] == "RN-AU-01"
        assert missing.status_code == 404
        assert missing.json()["code"] == "RN-AU-01"
        assert own_block.status_code == 201
        assert update_foreign.status_code == 404
        assert check.query(BloqueoModel).filter_by(tenant_id=tenant_id).count() == 1
        assert check.query(BloqueoModel).one().profesional_id == own_id
    finally:
        check.close()


def test_bloqueo_rechaza_intervalos_naive_o_invertidos(session_factory):
    session = session_factory()
    tenant, headers = _owner(session, "c06-time")
    professional = ProfesionalModel(tenant_id=tenant.id, nombre="Profesional demo")
    session.add(professional)
    session.commit()
    tenant_id = tenant.id
    professional_id = professional.id
    session.close()
    client = TestClient(create_app(session_factory=session_factory))

    naive = client.post(
        "/bloqueos",
        json={
            "profesional_id": professional_id,
            "inicio": "2026-11-02T10:00:00",
            "fin": "2026-11-02T11:00:00",
        },
        headers=headers,
    )
    reversed_range = client.post(
        "/bloqueos",
        json={
            "profesional_id": professional_id,
            "inicio": "2026-11-02T11:00:00+00:00",
            "fin": "2026-11-02T10:00:00+00:00",
        },
        headers=headers,
    )
    offset = client.post(
        "/bloqueos",
        json={
            "profesional_id": professional_id,
            "inicio": "2026-11-02T10:00:00+03:00",
            "fin": "2026-11-02T11:00:00+03:00",
        },
        headers=headers,
    )

    check = session_factory()
    try:
        assert naive.status_code == 422
        assert reversed_range.status_code == 422
        assert naive.json()["code"] == "RN-GL-02"
        assert reversed_range.json()["code"] == "RN-GL-02"
        assert offset.status_code == 201
        assert offset.json()["inicio"].endswith("Z")
        assert check.query(BloqueoModel).filter_by(tenant_id=tenant_id).count() == 1
    finally:
        check.close()


def test_precio_ref_rechaza_float_y_acepta_centavos_enteros(session_factory):
    session = session_factory()
    tenant, headers = _owner(session, "c06-price")
    tenant_id = tenant.id
    session.close()
    client = TestClient(create_app(session_factory=session_factory))

    fractional = client.post(
        "/prestaciones",
        json={"nombre": "Consulta", "duracion_min": 20, "precio_ref": 15000.0},
        headers=headers,
    )
    integer = client.post(
        "/prestaciones",
        json={"nombre": "Limpieza", "duracion_min": 30, "precio_ref": 15000},
        headers=headers,
    )
    zero = client.post(
        "/prestaciones",
        json={"nombre": "Control", "duracion_min": 20, "precio_ref": 0},
        headers=headers,
    )
    nullable = client.post(
        "/prestaciones",
        json={"nombre": "Evaluación", "duracion_min": 20, "precio_ref": None},
        headers=headers,
    )
    negative = client.post(
        "/prestaciones",
        json={"nombre": "Inválida", "duracion_min": 20, "precio_ref": -1},
        headers=headers,
    )

    check = session_factory()
    try:
        assert fractional.status_code == 422
        assert integer.status_code == 201
        assert integer.json()["precio_ref"] == 15000
        assert zero.status_code == 201
        assert zero.json()["precio_ref"] == 0
        assert nullable.status_code == 201
        assert nullable.json()["precio_ref"] is None
        assert negative.status_code == 422
        assert check.query(PrestacionModel).filter_by(tenant_id=tenant_id).count() == 3
    finally:
        check.close()


def test_mutacion_de_catalogo_audita_actor_tenant_y_utc(session_factory):
    session = session_factory()
    tenant, headers = _owner(session, "c06-audit")
    receptionist_id = str(uuid.uuid4())
    receptionist = UsuarioModel(
        id=receptionist_id,
        tenant_id=tenant.id,
        email="frontdesk-c06@example.test",
        nombre="Recepción sintética",
        roles=[UsuarioRoles.RECEPCION.value],
        activo=True,
    )
    session.add(receptionist)
    foreign_tenant = TenantModel(
        id="tenant-c06-rbac-foreign",
        slug="tenant-c06-rbac-foreign",
        nombre="Tenant sintético ajeno",
    )
    session.add(foreign_tenant)
    session.add(
        ProfesionalModel(
            id="prof-c06-rbac-foreign",
            tenant_id=foreign_tenant.id,
            nombre="Profesional ajeno",
        )
    )
    session.commit()
    receptionist_token = mint_token(
        user_id=receptionist.id,
        tenant_id=tenant.id,
        roles=receptionist.roles,
        email=receptionist.email,
        token_type="access",
    )
    tenant_id = tenant.id
    session.close()
    client = TestClient(create_app(session_factory=session_factory))

    created = client.post(
        "/profesionales",
        json={"nombre": "Profesional Demo"},
        headers=headers,
    )
    config = client.put(
        "/config",
        json={
            "antelacion_cancel_hs": 24,
            "antelacion_reserva_hs": 3,
            "recordatorio_t_48h": True,
            "recordatorio_t_24h": False,
        },
        headers=headers,
    )
    schedule = client.put(
        f"/profesionales/{created.json()['id']}/horarios",
        json={"horarios": [{"dia_semana": 0, "inicio": "09:00", "fin": "12:00"}]},
        headers=headers,
    )
    audit = client.get("/auditoria", headers=headers)
    denied = client.get(
        "/auditoria",
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )

    check = session_factory()
    try:
        event = (
            check.query(AuditEventModel)
            .filter_by(
                tenant_id=tenant_id,
                recurso_id=created.json()["id"],
                accion="agenda.profesional.creado",
            )
            .one()
        )
        config_event = (
            check.query(AuditEventModel)
            .filter_by(tenant_id=tenant_id, recurso="config", accion="agenda.configuracion.actualizada")
            .one()
        )
        schedule_event = (
            check.query(AuditEventModel)
            .filter_by(
                tenant_id=tenant_id,
                recurso_id=created.json()["id"],
                accion="agenda.horario_profesional.actualizado",
            )
            .one()
        )
        assert created.status_code == 201
        assert config.status_code == 200
        assert schedule.status_code == 200
        assert audit.status_code == 200
        assert denied.status_code == 403
        assert event.actor_id
        assert event.ocurrido_at.tzinfo is not None
        assert {"nombre", "usuario_id", "color_agenda", "activo"} <= set(event.campos)
        assert config_event.actor_id == event.actor_id
        assert "antelacion_reserva_hs" in config_event.campos
        assert schedule_event.actor_id == event.actor_id
        assert schedule_event.campos == ["horarios"]
    finally:
        check.close()


def test_catalogo_devuelve_dto_estricto_y_aplica_permisos_por_rol(session_factory):
    session = session_factory()
    tenant, owner_headers = _owner(session, "c06-dto-rbac")
    receptionist_id = str(uuid.uuid4())
    receptionist = UsuarioModel(
        id=receptionist_id,
        tenant_id=tenant.id,
        email="reception-dto@example.test",
        nombre="Recepción sintética",
        roles=[UsuarioRoles.RECEPCION.value],
        activo=True,
    )
    session.add(receptionist)
    session.commit()
    reception_token = mint_token(
        user_id=receptionist.id,
        tenant_id=tenant.id,
        roles=receptionist.roles,
        email=receptionist.email,
        token_type="access",
    )
    session.close()
    client = TestClient(create_app(session_factory=session_factory))

    created = client.post(
        "/profesionales",
        json={"nombre": "Profesional sintético"},
        headers={"Authorization": f"Bearer {reception_token}"},
    )
    extra_field = client.post(
        "/profesionales",
        json={"nombre": "Campo extra", "tenant_id": tenant.id},
        headers=owner_headers,
    )

    assert created.status_code == 201
    assert set(created.json()) == {
        "id",
        "tenant_id",
        "nombre",
        "usuario_id",
        "color_agenda",
        "activo",
        "created_at",
        "updated_at",
    }
    assert extra_field.status_code == 422
    own_catalog = client.get(
        "/profesionales",
        headers={"Authorization": f"Bearer {reception_token}"},
    )
    assert own_catalog.status_code == 200
    assert [item["id"] for item in own_catalog.json()] == [created.json()["id"]]
    assert client.post(
        "/profesionales",
        json={"nombre": "No autorizado"},
        headers={"Authorization": f"Bearer {mint_token(user_id=receptionist_id, tenant_id=tenant.id, roles=[UsuarioRoles.ODONTOLOGO.value], email=receptionist.email, token_type='access')}"},
    ).status_code == 403


def test_falla_de_auditoria_revierte_mutacion_de_catalogo(
    session_factory,
    monkeypatch,
):
    import app.modules.agenda.router as agenda_router

    session = session_factory()
    tenant, headers = _owner(session, "c06-audit-rollback")
    tenant_id = tenant.id
    session.close()

    def audit_failure(*args, **kwargs):
        raise RuntimeError("fallo sintético")

    monkeypatch.setattr(agenda_router, "registrar_auditoria", audit_failure)
    client = TestClient(
        create_app(session_factory=session_factory),
        raise_server_exceptions=False,
    )
    response = client.post(
        "/profesionales",
        json={"nombre": "No persistir"},
        headers=headers,
    )

    check = session_factory()
    try:
        assert response.status_code == 500
        assert check.query(ProfesionalModel).filter_by(tenant_id=tenant_id).count() == 0
    finally:
        check.close()

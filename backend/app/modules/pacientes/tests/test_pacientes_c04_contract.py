from __future__ import annotations

import hashlib
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.audit import AuditEventModel
from app.core.security import mint_token
from app.main import create_app
from app.modules.agenda.models import (
    ProfesionalModel,
    TenantModel,
    UsuarioModel,
    UsuarioRoles,
)
from app.modules.pacientes.models import EvolucionModel, PacienteModel


def _token(
    session: Session,
    tenant: TenantModel,
    email: str,
    roles: list[str],
) -> str:
    user = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email=email,
        nombre="Usuario sintético",
        roles=roles,
        activo=True,
    )
    session.add(user)
    session.commit()
    return mint_token(
        user_id=user.id,
        tenant_id=tenant.id,
        roles=roles,
        email=user.email,
        token_type="access",
    )


def _tenant(session: Session, slug: str) -> TenantModel:
    tenant = TenantModel(id=str(uuid.uuid4()), slug=slug, nombre="Consultorio sintético")
    session.add(tenant)
    session.commit()
    return tenant


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_contactos_solo_recepcion_y_dueno_pueden_mutarse(session_factory):
    session = session_factory()
    tenant = _tenant(session, "c04-rbac")
    owner = _token(session, tenant, "owner@c04.test", [UsuarioRoles.DUENO.value])
    frontdesk = _token(session, tenant, "frontdesk@c04.test", [UsuarioRoles.RECEPCION.value])
    dentist = _token(session, tenant, "dentist@c04.test", [UsuarioRoles.ODONTOLOGO.value])
    client = TestClient(create_app(session_factory=session_factory))
    owner_headers = _headers(owner)
    dentist_headers = _headers(dentist)

    paciente = client.post(
        "/pacientes",
        json={"nombre": "Julia", "apellido": "Sosa"},
        headers=owner_headers,
    ).json()
    patient_id = paciente["id"]

    assert client.get(
        f"/pacientes/{patient_id}", headers=dentist_headers
    ).status_code == 200
    assert client.put(
        f"/pacientes/{patient_id}",
        json={"nombre": "Otro nombre"},
        headers=dentist_headers,
    ).status_code == 403
    assert client.put(
        f"/pacientes/{patient_id}/optins",
        json={"canal": "email", "estado": True, "version_texto": "email-v1"},
        headers=dentist_headers,
    ).status_code == 403
    assert client.post(
        "/pacientes",
        json={"nombre": "Ana", "apellido": "Paz"},
        headers=_headers(frontdesk),
    ).status_code == 201

    other_tenant = _tenant(session, "c04-other")
    other_owner = _token(session, other_tenant, "owner@other-c04.test", [UsuarioRoles.DUENO.value])
    hidden = client.get(
        f"/pacientes/{patient_id}",
        headers=_headers(other_owner),
    )
    missing = client.get("/pacientes/no-existe", headers=_headers(other_owner))
    assert hidden.status_code == missing.status_code == 404
    assert hidden.json() == missing.json()
    session.close()


def test_cambio_de_telefono_revoca_optin_y_audita_sin_datos_clinicos(session_factory):
    session = session_factory()
    tenant = _tenant(session, "c04-consent")
    owner = _token(session, tenant, "owner@consent.test", [UsuarioRoles.DUENO.value])
    client = TestClient(create_app(session_factory=session_factory))
    headers = _headers(owner)

    paciente = client.post(
        "/pacientes",
        json={
            "nombre": "Eva",
            "apellido": "Luna",
            "telefono": "+5491122223333",
            "notas": "Nota clínica sintética que no debe ir a auditoría",
        },
        headers=headers,
    ).json()
    patient_id = paciente["id"]
    missing_version = client.put(
        f"/pacientes/{patient_id}/optins",
        json={"canal": "whatsapp", "estado": True},
        headers=headers,
    )
    assert missing_version.status_code == 422

    enabled = client.put(
        f"/pacientes/{patient_id}/optins",
        json={
            "canal": "whatsapp",
            "estado": True,
            "version_texto": "wa-notice-v1",
        },
        headers=headers,
    )
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["consentimiento_version"] == "wa-notice-v1"
    assert enabled.json()["consentimiento_actor_id"]
    assert enabled.json()["consentimiento_at"].endswith("Z")

    changed = client.put(
        f"/pacientes/{patient_id}",
        json={"telefono": "+5491144445555"},
        headers=headers,
    )
    assert changed.status_code == 200, changed.text
    optin = client.get(f"/pacientes/{patient_id}/optins", headers=headers).json()[0]
    assert optin["estado"] is False
    assert optin["consentimiento_version"] == "wa-notice-v1"
    audit = client.get("/auditoria", headers=headers)
    assert audit.status_code == 200
    assert any(
        evento["accion"] == "paciente.telefono_cambiado"
        for evento in audit.json()
    )
    assert all(
        "Nota clínica sintética que no debe ir a auditoría" not in str(evento)
        for evento in audit.json()
    )

    receptionist = _token(
        session,
        tenant,
        "frontdesk@consent.test",
        [UsuarioRoles.RECEPCION.value],
    )
    assert client.get("/auditoria", headers=_headers(receptionist)).status_code == 403

    other_tenant = _tenant(session, "c04-consent-other")
    other_owner = _token(
        session,
        other_tenant,
        "owner@consent-other.test",
        [UsuarioRoles.DUENO.value],
    )
    other_patient = client.post(
        "/pacientes",
        json={"nombre": "Otra", "apellido": "Persona", "telefono": "+5491166667777"},
        headers=_headers(other_owner),
    ).json()
    client.put(
        f"/pacientes/{other_patient['id']}",
        json={"telefono": "+5491188889999"},
        headers=_headers(other_owner),
    )
    audit_after_other_tenant = client.get("/auditoria", headers=headers)
    assert all(
        evento["recurso_id"] != other_patient["id"]
        for evento in audit_after_other_tenant.json()
    )

    check = session_factory()
    try:
        phone_change = (
            check.query(AuditEventModel)
            .filter_by(
                tenant_id=tenant.id,
                recurso_id=patient_id,
                accion="paciente.telefono_cambiado",
            )
            .one()
        )
        assert phone_change.invalidated_destination_hash == hashlib.sha256(
            "+5491122223333".encode("utf-8")
        ).hexdigest()
        assert "+5491122223333" not in str(phone_change.invalidated_destination_hash)
    finally:
        check.close()
    session.close()


def test_paciente_rechaza_telefono_no_e164_campos_extra_y_fecha_naive(session_factory):
    session = session_factory()
    tenant = _tenant(session, "c04-validation")
    owner = _token(session, tenant, "owner@validation.test", [UsuarioRoles.DUENO.value])
    client = TestClient(create_app(session_factory=session_factory))
    headers = _headers(owner)

    valid = client.post(
        "/pacientes",
        json={
            "nombre": "Noa",
            "apellido": "Paz",
            "telefono": "+5491122223333",
            "fecha_nac": "2000-01-02T03:04:05+03:00",
        },
        headers=headers,
    )
    assert valid.status_code == 201
    assert valid.json()["fecha_nac"].endswith("Z")

    for phone in ("+0123456789", "+1234567890123456", "11 2222 3333"):
        invalid = client.post(
            "/pacientes",
            json={"nombre": "Noa", "apellido": "Paz", "telefono": phone},
            headers=headers,
        )
        assert invalid.status_code == 422

    extra_field = client.post(
        "/pacientes",
        json={"nombre": "Ana", "apellido": "Paz", "saldo": 1},
        headers=headers,
    )
    assert extra_field.status_code == 422
    naive_datetime = client.post(
        "/pacientes",
        json={
            "nombre": "Ana",
            "apellido": "Paz",
            "fecha_nac": "2000-01-02T03:04:05",
        },
        headers=headers,
    )
    assert naive_datetime.status_code == 422
    session.close()


def test_importacion_csv_informa_filas_y_rechaza_limites(session_factory):
    session = session_factory()
    tenant = _tenant(session, "c04-csv")
    owner = _token(session, tenant, "owner@csv.test", [UsuarioRoles.DUENO.value])
    client = TestClient(create_app(session_factory=session_factory))
    headers = {
        **_headers(owner),
        "Content-Type": "text/csv; charset=utf-8",
    }

    csv_bytes = (
        "\ufeffnombre,apellido,dni,telefono,email\n"
        "Eva,Luna,30123456,+5491122223333,eva@example.test\n"
        "Eva,Luna,30123456,+5491122223333,eva@example.test\n"
        ",Inválida,,,\n"
        "Mara,Paz,,,mara@example.test\n"
    ).encode("utf-8")
    response = client.post("/pacientes/import-csv", content=csv_bytes, headers=headers)
    assert response.status_code == 200, response.text
    report = response.json()
    assert (report["importadas"], report["duplicadas"], report["fallidas"]) == (2, 1, 1)
    assert [row["fila"] for row in report["resultados"]] == [2, 3, 4, 5]
    assert {row["estado"] for row in report["resultados"]} == {
        "importada",
        "duplicada",
        "fallida",
    }
    assert session.query(PacienteModel).filter_by(tenant_id=tenant.id).count() == 2

    unsupported_header = client.post(
        "/pacientes/import-csv",
        content=b"nombre,apellido,notas\nEva,Luna,nota",
        headers=headers,
    )
    assert unsupported_header.status_code == 422
    malformed_utf8 = client.post(
        "/pacientes/import-csv",
        content=b"nombre,apellido\nEva,\xff",
        headers=headers,
    )
    assert malformed_utf8.status_code == 422
    too_many_rows = client.post(
        "/pacientes/import-csv",
        content=("nombre,apellido\n" + "A,B\n" * 5001).encode("utf-8"),
        headers=headers,
    )
    assert too_many_rows.status_code == 413
    too_large = client.post(
        "/pacientes/import-csv",
        content=b"x" * (5 * 1024 * 1024 + 1),
        headers=headers,
    )
    assert too_large.status_code == 413
    session.close()


def test_baja_logica_preserva_historia_y_eliminacion_es_auditable(session_factory, session):
    tenant = _tenant(session, "c04-delete")
    owner = _token(session, tenant, "owner@delete.test", [UsuarioRoles.DUENO.value])
    client = TestClient(create_app(session_factory=session_factory))
    headers = _headers(owner)
    paciente = client.post(
        "/pacientes",
        json={"nombre": "Mara", "apellido": "Paz"},
        headers=headers,
    ).json()
    patient_id = paciente["id"]
    dentist_token = _token(
        session,
        tenant,
        "dentist@delete.test",
        [UsuarioRoles.ODONTOLOGO.value],
    )
    dentist = session.query(UsuarioModel).filter_by(email="dentist@delete.test").one()
    professional = ProfesionalModel(
        tenant_id=tenant.id,
        usuario_id=dentist.id,
        nombre="Odontólogo sintético",
        activo=True,
    )
    session.add(professional)
    session.commit()
    clinical = client.post(
        f"/pacientes/{patient_id}/evoluciones",
        json={
            "profesional_id": professional.id,
            "motivo": "Control",
            "detalle": "Registro sintético",
        },
        headers=_headers(dentist_token),
    )
    assert clinical.status_code == 201

    deleted = client.delete(f"/pacientes/{patient_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/pacientes/{patient_id}", headers=headers).status_code == 404
    assert client.get("/pacientes", headers=headers).json() == []
    assert session.query(PacienteModel).filter_by(id=patient_id).one().deleted_at is not None
    assert session.query(EvolucionModel).filter_by(paciente_id=patient_id).count() == 1

    patient_without_history = client.post(
        "/pacientes",
        json={"nombre": "Noa", "apellido": "Paz"},
        headers=headers,
    ).json()
    deleted_without_history = client.delete(
        f"/pacientes/{patient_without_history['id']}",
        headers=headers,
    )
    assert deleted_without_history.status_code == 204
    assert (
        session.query(PacienteModel)
        .filter_by(id=patient_without_history["id"])
        .one()
        .deleted_at
        is not None
    )


def test_falla_de_auditoria_revierte_la_mutacion(session_factory, monkeypatch):
    import app.modules.pacientes.service as paciente_service

    session = session_factory()
    tenant = _tenant(session, "c04-atomic-audit")
    owner = _token(
        session,
        tenant,
        "owner@atomic-audit.test",
        [UsuarioRoles.DUENO.value],
    )
    session.close()

    def auditoria_falla(*args, **kwargs):
        raise RuntimeError("fallo sintético")

    monkeypatch.setattr(paciente_service, "registrar_auditoria", auditoria_falla)
    client = TestClient(
        create_app(session_factory=session_factory),
        raise_server_exceptions=False,
    )
    response = client.post(
        "/pacientes",
        json={"nombre": "Noa", "apellido": "Paz"},
        headers=_headers(owner),
    )

    check = session_factory()
    try:
        assert response.status_code == 500
        assert check.query(PacienteModel).filter_by(tenant_id=tenant.id).count() == 0
    finally:
        check.close()

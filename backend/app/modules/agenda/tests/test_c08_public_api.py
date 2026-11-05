from __future__ import annotations

from datetime import datetime, timezone
from datetime import time
import hashlib

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.agenda.models import (
    PrestacionModel,
    ProfesionalModel,
    PublicTokenModel,
    PublicAuditModel,
    ConfigModel,
    BloqueoModel,
    HorarioProfesionalModel,
    TenantModel,
    TurnoModel,
)
from app.modules.agenda.public_booking import PUBLIC_RATE_LIMITER


def _client(session_factory):
    PUBLIC_RATE_LIMITER._timestamps.clear()
    return TestClient(
        create_app(
            session_factory=session_factory,
            now_fn=lambda: datetime(2030, 1, 1, 12, tzinfo=timezone.utc),
        )
    )


def _booking_payload() -> dict[str, object]:
    return {
        "tenant_slug": "missing",
        "profesional_id": "professional",
        "prestacion_id": "service",
        "inicio": "2030-01-03T10:00:00-03:00",
        "nombre": "Ana",
        "apellido": "Pérez",
    }


def test_public_booking_rate_limit_returns_retry_after_without_creating_turns(
    session_factory,
):
    client = _client(session_factory)

    responses = [
        client.post(
            "/public/reservar",
            json=_booking_payload(),
            headers={"Idempotency-Key": f"booking-{index}"},
        )
        for index in range(11)
    ]

    assert all(response.status_code == 404 for response in responses[:10])
    assert responses[-1].status_code == 429
    assert responses[-1].headers["Retry-After"].isdigit()
    session = session_factory()
    try:
        assert session.query(TurnoModel).count() == 0
    finally:
        session.close()


def test_public_availability_returns_catalog_and_chronological_slots(session_factory):
    session = session_factory()
    tenant = TenantModel(id="tenant-api-availability", slug="api-availability", nombre="Demo")
    professional = ProfesionalModel(
        id="professional-api-availability",
        tenant_id=tenant.id,
        nombre="Dra. Demo",
    )
    service = PrestacionModel(
        id="service-api-availability",
        tenant_id=tenant.id,
        nombre="Consulta",
        duracion_min=30,
    )
    session.add(tenant)
    session.flush()
    session.add_all([
        professional,
        service,
        ConfigModel(tenant_id=tenant.id, antelacion_reserva_hs=2),
        HorarioProfesionalModel(
            id="schedule-api-availability",
            tenant_id=tenant.id,
            profesional_id=professional.id,
            dia_semana=0,
            hora_inicio=time(9),
            hora_fin=time(11),
        ),
    ])
    session.commit()
    professional_id = professional.id
    service_id = service.id
    session.close()
    client = _client(session_factory)

    response = client.get(
        "/r/api-availability",
        params={
            "profesional_id": professional_id,
            "prestacion_id": service_id,
            "desde": "2030-01-07T00:00:00Z",
            "hasta": "2030-01-08T00:00:00Z",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_slug"] == "api-availability"
    assert body["professionals"][0]["id"] == professional_id
    assert body["services"][0]["id"] == service_id
    assert body["slots"] == sorted(body["slots"])


def test_public_availability_excludes_blocked_slots_and_respects_advance_notice(session_factory):
    session = session_factory()
    tenant = TenantModel(id="tenant-api-blocked", slug="api-blocked", nombre="Demo")
    professional = ProfesionalModel(id="professional-api-blocked", tenant_id=tenant.id, nombre="Dra. Demo")
    service = PrestacionModel(id="service-api-blocked", tenant_id=tenant.id, nombre="Consulta", duracion_min=30)
    session.add(tenant)
    session.flush()
    session.add_all([professional, service, ConfigModel(
        tenant_id=tenant.id,
        antelacion_reserva_hs=48,
    )])
    session.flush()
    session.add_all([
        HorarioProfesionalModel(
            id="schedule-api-blocked",
            tenant_id=tenant.id,
            profesional_id=professional.id,
            dia_semana=0,
            hora_inicio=time(9),
            hora_fin=time(11),
        ),
        BloqueoModel(
            id="block-api-blocked",
            tenant_id=tenant.id,
            profesional_id=professional.id,
            inicio=datetime(2030, 1, 7, 12, tzinfo=timezone.utc),
            fin=datetime(2030, 1, 7, 12, 30, tzinfo=timezone.utc),
            motivo="mantenimiento",
        ),
    ])
    session.commit()
    professional_id = professional.id
    service_id = service.id
    session.close()

    client = _client(session_factory)
    response = client.get(
        "/r/api-blocked",
        params={
            "profesional_id": professional_id,
            "prestacion_id": service_id,
            "desde": "2030-01-07T00:00:00Z",
            "hasta": "2030-01-08T00:00:00Z",
        },
    )

    assert response.status_code == 200
    slots = response.json()["slots"]
    assert "2030-01-07T12:00:00+00:00" not in slots
    assert "2030-01-07T12:30:00Z" in slots


def test_public_action_rate_limit_is_separate_from_booking_limit(session_factory):
    client = _client(session_factory)

    responses = [
        client.post(
            "/public/turnos/opaque/confirmar",
            json={"tenant_slug": "missing"},
        )
        for _ in range(21)
    ]

    assert all(response.status_code == 404 for response in responses[:20])
    assert responses[-1].status_code == 429
    assert responses[-1].headers["Retry-After"].isdigit()


def test_public_availability_rate_limit_is_separate_from_mutations(session_factory):
    client = _client(session_factory)

    responses = [
        client.get("/r/missing")
        for _ in range(61)
    ]

    assert all(response.status_code == 404 for response in responses[:60])
    assert responses[-1].status_code == 429
    assert responses[-1].headers["Retry-After"].isdigit()


def test_public_booking_requires_idempotency_header(session_factory):
    client = _client(session_factory)

    response = client.post("/public/reservar", json=_booking_payload())

    assert response.status_code == 422
    assert response.json()["code"] == "RN-GL-00"


def test_public_action_rejects_expired_and_revoked_tokens(session_factory):
    setup = session_factory()
    tenant = TenantModel(id="tenant-api-actions", slug="api-actions", nombre="Demo")
    professional = ProfesionalModel(
        id="professional-api-actions",
        tenant_id=tenant.id,
        nombre="Dra. Demo",
    )
    service = PrestacionModel(
        id="service-api-actions",
        tenant_id=tenant.id,
        nombre="Consulta",
        duracion_min=30,
    )
    setup.add(tenant)
    setup.flush()
    setup.add_all([professional, service])
    setup.commit()
    tenant_slug = tenant.slug
    professional_id = professional.id
    service_id = service.id
    setup.close()

    client = _client(session_factory)
    payload = {
        "tenant_slug": tenant_slug,
        "profesional_id": professional_id,
        "prestacion_id": service_id,
        "inicio": "2030-01-03T10:00:00-03:00",
        "nombre": "Ana",
        "apellido": "Pérez",
    }
    booking = client.post(
        "/public/reservar",
        json=payload,
        headers={"Idempotency-Key": "api-actions-booking"},
    )
    assert booking.status_code == 201
    tokens = booking.json()["action_tokens"]

    conflict = client.post(
        "/public/reservar",
        json=payload,
        headers={"Idempotency-Key": "api-actions-conflict"},
    )
    assert conflict.status_code == 409

    wrong_purpose = client.post(
        f"/public/turnos/{tokens['cancel']}/confirmar",
        json={"tenant_slug": tenant_slug},
    )
    assert wrong_purpose.status_code == 401
    session = session_factory()
    try:
        rejected_audit = session.query(PublicAuditModel).filter_by(
            tenant_id=tenant.id,
            action="confirm",
            outcome="token_rechazado",
        ).one()
        assert rejected_audit.turno_id is None
    finally:
        session.close()

    confirmed = client.post(
        f"/public/turnos/{tokens['confirm']}/confirmar",
        json={"tenant_slug": tenant_slug},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["estado"] == "confirmado"
    session = session_factory()
    try:
        assert session.query(PublicAuditModel).filter_by(
            tenant_id=tenant.id,
            action="reserva",
            outcome="creada",
        ).count() == 1
        assert session.query(PublicAuditModel).filter_by(
            tenant_id=tenant.id,
            action="confirm",
            outcome="token_validado",
        ).count() == 1
    finally:
        session.close()

    session = session_factory()
    try:
        expired = session.query(PublicTokenModel).filter_by(
            token_hash=hashlib.sha256(
                tokens["cancel"].encode("utf-8")
            ).hexdigest()
        ).one()
        expired.expires_at = datetime(2030, 1, 1, 11, tzinfo=timezone.utc)
        session.commit()
    finally:
        session.close()
    expired_response = client.post(
        f"/public/turnos/{tokens['cancel']}/cancelar",
        json={"tenant_slug": tenant_slug},
    )
    assert expired_response.status_code == 401
    session = session_factory()
    try:
        assert session.query(PublicAuditModel).filter_by(
            tenant_id=tenant.id,
            action="cancel",
            outcome="token_expirado",
        ).count() == 1
    finally:
        session.close()

    session = session_factory()
    try:
        revoked = session.query(PublicTokenModel).filter_by(
            token_hash=hashlib.sha256(
                tokens["reschedule"].encode("utf-8")
            ).hexdigest()
        ).one()
        revoked.revoked_at = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)
        session.commit()
    finally:
        session.close()
    revoked_response = client.post(
        f"/public/turnos/{tokens['reschedule']}/reprogramar",
        json={
            "tenant_slug": tenant.slug,
            "profesional_id": professional_id,
            "prestacion_id": service_id,
            "inicio": "2030-01-04T10:00:00-03:00",
        },
    )
    assert revoked_response.status_code == 401


def test_public_cancel_honors_rn_ag_01_without_partial_mutation(session_factory):
    setup = session_factory()
    tenant = TenantModel(id="tenant-api-cancel", slug="api-cancel", nombre="Demo")
    professional = ProfesionalModel(
        id="professional-api-cancel",
        tenant_id=tenant.id,
        nombre="Dra. Demo",
    )
    service = PrestacionModel(
        id="service-api-cancel",
        tenant_id=tenant.id,
        nombre="Consulta",
        duracion_min=30,
    )
    setup.add(tenant)
    setup.flush()
    setup.add_all([
        professional,
        service,
        ConfigModel(
            tenant_id=tenant.id,
            antelacion_cancel_hs=72,
            antelacion_reserva_hs=0,
        ),
    ])
    setup.commit()
    tenant_slug = tenant.slug
    professional_id = professional.id
    service_id = service.id
    setup.close()

    client = _client(session_factory)
    booking = client.post(
        "/public/reservar",
        json={
            "tenant_slug": tenant_slug,
            "profesional_id": professional_id,
            "prestacion_id": service_id,
            "inicio": "2030-01-03T10:00:00-03:00",
            "nombre": "Ana",
            "apellido": "Pérez",
        },
        headers={"Idempotency-Key": "cancel-rn-ag-01"},
    )
    assert booking.status_code == 201
    token = booking.json()["action_tokens"]["cancel"]
    turno_id = booking.json()["turno_id"]

    response = client.post(
        f"/public/turnos/{token}/cancelar",
        json={"tenant_slug": tenant_slug},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "RN-AG-01"
    session = session_factory()
    try:
        turno = session.get(TurnoModel, turno_id)
        assert turno is not None
        assert turno.estado == "pendiente_confirmacion"
        assert turno.cancelled_at is None
    finally:
        session.close()


def test_public_reschedule_conflict_returns_alternatives_without_changing_original(
    session_factory,
):
    setup = session_factory()
    tenant = TenantModel(id="tenant-api-reschedule", slug="api-reschedule", nombre="Demo")
    professional = ProfesionalModel(
        id="professional-api-reschedule",
        tenant_id=tenant.id,
        nombre="Dra. Demo",
    )
    service = PrestacionModel(
        id="service-api-reschedule",
        tenant_id=tenant.id,
        nombre="Consulta",
        duracion_min=30,
    )
    setup.add(tenant)
    setup.flush()
    setup.add_all([professional, service, ConfigModel(
        tenant_id=tenant.id,
        antelacion_reserva_hs=0,
    ), HorarioProfesionalModel(
        id="schedule-api-reschedule",
        tenant_id=tenant.id,
        profesional_id=professional.id,
        dia_semana=2,
        hora_inicio=time(9),
        hora_fin=time(12),
    )])
    setup.commit()
    tenant_slug = tenant.slug
    professional_id = professional.id
    service_id = service.id
    setup.close()

    client = _client(session_factory)
    base_payload = {
        "tenant_slug": tenant_slug,
        "profesional_id": professional_id,
        "prestacion_id": service_id,
        "inicio": "2030-01-03T10:00:00-03:00",
        "nombre": "Ana",
        "apellido": "Pérez",
    }
    first = client.post(
        "/public/reservar",
        json=base_payload,
        headers={"Idempotency-Key": "reschedule-original"},
    )
    second = client.post(
        "/public/reservar",
        json={**base_payload, "nombre": "Luis"},
        headers={"Idempotency-Key": "reschedule-occupied"},
    )
    assert first.status_code == 201
    assert second.status_code == 409

    token = first.json()["action_tokens"]["reschedule"]
    response = client.post(
        f"/public/turnos/{token}/reprogramar",
        json={
            "tenant_slug": tenant_slug,
            "profesional_id": professional_id,
            "prestacion_id": service_id,
            "inicio": "2030-01-03T10:00:00-03:00",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "RN-AG-03"
    assert isinstance(response.json()["alternativas"], list)
    alternative = response.json()["alternativas"][0]
    moved = client.post(
        f"/public/turnos/{token}/reprogramar",
        json={
            "tenant_slug": tenant_slug,
            "profesional_id": professional_id,
            "prestacion_id": service_id,
            "inicio": alternative,
        },
    )
    assert moved.status_code == 200
    assert moved.json()["estado"] == "pendiente_confirmacion"
    session = session_factory()
    try:
        original = session.get(TurnoModel, first.json()["turno_id"])
        assert original is not None
        assert original.estado == "reprogramado"
    finally:
        session.close()

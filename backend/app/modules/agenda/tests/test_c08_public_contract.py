from datetime import datetime, timedelta, timezone
import uuid

import pytest
from pydantic import ValidationError

from app.modules.agenda.public_booking import (
    PublicBookingService,
    PublicBookingRequest,
    release_expired_pending_payments,
    _hash,
)
from app.modules.agenda.repository import PublicTokenRepository
from app.modules.agenda.models import (
    ConfigModel,
    PrestacionModel,
    ProfesionalModel,
    PublicTokenModel,
    TenantModel,
    TurnoModel,
)
from app.modules.pacientes.models import PacienteModel


def _payload(**overrides):
    payload = {
        "tenant_slug": "demo",
        "profesional_id": "professional",
        "prestacion_id": "service",
        "inicio": "2030-01-02T10:00:00-03:00",
        "nombre": "Ana",
        "apellido": "Pérez",
        "telefono": "+5491123456789",
        "whatsapp_opt_in": True,
    }
    payload.update(overrides)
    return payload


def test_public_booking_rejects_extra_fields_and_naive_datetimes():
    with pytest.raises(ValidationError):
        PublicBookingRequest(**_payload(extra="no"))
    with pytest.raises(ValidationError):
        PublicBookingRequest(**_payload(inicio=datetime(2030, 1, 2, 10, 0)))


def test_public_booking_requires_e164_when_whatsapp_is_requested():
    with pytest.raises(ValidationError):
        PublicBookingRequest(**_payload(telefono="1123456789"))


def test_public_token_hash_is_not_the_raw_value():
    raw = "token-value"
    assert _hash(raw) != raw
    assert len(_hash(raw)) == 64


def test_public_token_repository_isolates_tenant_and_checks_expiry_and_purpose(session):
    now = datetime.now(timezone.utc)
    tenant_a = TenantModel(id=str(uuid.uuid4()), slug="token-a", nombre="A")
    tenant_b = TenantModel(id=str(uuid.uuid4()), slug="token-b", nombre="B")
    session.add_all([tenant_a, tenant_b])
    session.flush()
    raw = "opaque-token"
    token = PublicTokenModel(
        tenant_id=tenant_a.id,
        turno_id="turn-a",
        token_hash=_hash(raw),
        purpose="confirm",
        expires_at=now + timedelta(hours=1),
    )
    session.add(token)
    session.flush()
    repository = PublicTokenRepository(session)

    assert repository.get_valid(
        tenant_id=tenant_a.id, raw_token=raw, purpose="confirm", now=now
    ) is token
    assert repository.get_valid(
        tenant_id=tenant_b.id, raw_token=raw, purpose="confirm", now=now
    ) is None
    assert repository.get_valid(
        tenant_id=tenant_a.id, raw_token=raw, purpose="cancel", now=now
    ) is None
    assert repository.get_valid(
        tenant_id=tenant_a.id,
        raw_token=raw,
        purpose="confirm",
        now=now + timedelta(hours=2),
    ) is None


def test_public_token_repository_revokes_tokens_without_exposing_raw_value(session):
    now = datetime.now(timezone.utc)
    tenant = TenantModel(id=str(uuid.uuid4()), slug="token-revoke", nombre="Demo")
    session.add(tenant)
    session.flush()
    raw = "revocable-token"
    token = PublicTokenModel(
        tenant_id=tenant.id,
        turno_id="turn-revoke",
        token_hash=_hash(raw),
        purpose="cancel",
        expires_at=now + timedelta(hours=1),
    )
    session.add(token)
    session.flush()

    repository = PublicTokenRepository(session)
    assert repository.revoke_for_turno(
        tenant_id=tenant.id,
        turno_id="turn-revoke",
        revoked_at=now,
        reason="phone_changed",
    ) == 1
    session.flush()
    assert repository.get_valid(
        tenant_id=tenant.id, raw_token=raw, purpose="cancel", now=now
    ) is None
    assert token.token_hash == _hash(raw)
    assert token.revocation_reason == "phone_changed"


def test_public_booking_creates_pending_turn_and_scoped_tokens(session):
    tenant_id = str(uuid.uuid4())
    tenant = TenantModel(id=tenant_id, slug="public-demo", nombre="Demo")
    professional = ProfesionalModel(
        id=str(uuid.uuid4()), tenant_id=tenant_id, nombre="Dra. Demo"
    )
    service = PrestacionModel(
        id=str(uuid.uuid4()), tenant_id=tenant_id, nombre="Consulta", duracion_min=30
    )
    session.add(tenant)
    session.flush()
    session.add_all([professional, service])
    session.flush()
    now = datetime.now(timezone.utc)
    request = PublicBookingRequest(**_payload(
        tenant_slug=tenant.slug,
        profesional_id=professional.id,
        prestacion_id=service.id,
        inicio=(now + timedelta(days=2)).isoformat(),
    ))
    result = PublicBookingService(session).create(request, "booking-key", now)
    session.commit()
    assert result.estado == "pendiente_confirmacion"
    assert set(result.action_tokens) == {"confirm", "cancel", "reschedule"}
    assert all(token.token_hash not in result.action_tokens.values() for token in session.query(PublicTokenModel).all())


def test_public_booking_reuses_idempotency_without_duplicate_turn(session):
    tenant_id = str(uuid.uuid4())
    tenant = TenantModel(id=tenant_id, slug="retry-demo", nombre="Demo")
    professional = ProfesionalModel(id=str(uuid.uuid4()), tenant_id=tenant_id, nombre="Dra. Demo")
    service = PrestacionModel(id=str(uuid.uuid4()), tenant_id=tenant_id, nombre="Consulta", duracion_min=30)
    session.add(tenant)
    session.flush()
    session.add_all([professional, service])
    session.flush()
    now = datetime.now(timezone.utc)
    request = PublicBookingRequest(**_payload(
        tenant_slug=tenant.slug,
        profesional_id=professional.id,
        prestacion_id=service.id,
        inicio=(now + timedelta(days=2)).isoformat(),
    ))
    service_impl = PublicBookingService(session)
    first = service_impl.create(request, "same-key", now)
    session.commit()
    second = service_impl.create(request, "same-key", now)
    assert second.turno_id == first.turno_id
    assert session.query(TurnoModel).count() == 1


def test_public_booking_phone_change_revokes_pending_tokens(session):
    tenant_id = str(uuid.uuid4())
    tenant = TenantModel(id=tenant_id, slug="phone-change", nombre="Demo")
    professional = ProfesionalModel(id=str(uuid.uuid4()), tenant_id=tenant_id, nombre="Dra. Demo")
    service = PrestacionModel(id=str(uuid.uuid4()), tenant_id=tenant_id, nombre="Consulta", duracion_min=30)
    session.add(tenant)
    session.flush()
    session.add_all([professional, service])
    session.flush()
    now = datetime.now(timezone.utc)
    first = PublicBookingService(session).create(
        PublicBookingRequest(**_payload(
            tenant_slug=tenant.slug,
            profesional_id=professional.id,
            prestacion_id=service.id,
            email="ana@example.test",
            telefono="+5491123456789",
            inicio=(now + timedelta(days=2)).isoformat(),
        )),
        "phone-old",
        now,
    )
    session.commit()
    second = PublicBookingService(session).create(
        PublicBookingRequest(**_payload(
            tenant_slug=tenant.slug,
            profesional_id=professional.id,
            prestacion_id=service.id,
            email="ana@example.test",
            telefono="+5491198765432",
            inicio=(now + timedelta(days=3)).isoformat(),
        )),
        "phone-new",
        now,
    )
    session.commit()
    assert first.turno_id != second.turno_id
    old_tokens = session.query(PublicTokenModel).filter_by(
        turno_id=first.turno_id,
    ).all()
    assert old_tokens
    assert all(token.revocation_reason == "phone_changed" for token in old_tokens)
    patient = session.query(PacienteModel).filter_by(email="ana@example.test").one()
    assert patient.telefono == "+5491198765432"


def test_expired_pending_payment_releases_slot_and_revokes_tokens(session):
    tenant_id = str(uuid.uuid4())
    tenant = TenantModel(id=tenant_id, slug="payment-timeout", nombre="Demo")
    professional = ProfesionalModel(id=str(uuid.uuid4()), tenant_id=tenant_id, nombre="Dra. Demo")
    service = PrestacionModel(id=str(uuid.uuid4()), tenant_id=tenant_id, nombre="Consulta", duracion_min=30)
    session.add(tenant)
    session.flush()
    session.add_all([
        professional,
        service,
        ConfigModel(tenant_id=tenant.id, senia_requerida=True),
    ])
    session.flush()
    created = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)
    booking = PublicBookingService(session).create(
        PublicBookingRequest(**_payload(
            tenant_slug=tenant.slug,
            profesional_id=professional.id,
            prestacion_id=service.id,
            inicio=(created + timedelta(days=2)).isoformat(),
        )),
        "payment-timeout-key",
        created,
    )
    session.commit()

    released = release_expired_pending_payments(
        session,
        created + timedelta(minutes=31),
    )
    session.commit()
    assert released == 1
    turno = session.get(TurnoModel, booking.turno_id)
    assert turno is not None
    assert turno.estado == "cancelado"
    assert session.query(PublicTokenModel).filter_by(
        turno_id=turno.id,
        revocation_reason="payment_timeout",
    ).count() == 3

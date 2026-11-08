from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.security import mint_token
from app.main import create_app
from app.modules.agenda.models import (
    ConfigModel,
    TenantModel,
    TurnoModel,
    UsuarioModel,
)
from app.modules.notificaciones.models import (
    NotificacionEnvioModel,
    PlantillaModel,
)
from app.modules.notificaciones.repository import (
    NotificacionEnvioRepository,
    PlantillaRepository,
)
from app.modules.notificaciones.scheduler import SchedulerService
from app.modules.notificaciones.sender import SenderService
from app.modules.notificaciones.whatsapp import FakeClient as FakeWhatsApp
from app.modules.notificaciones.email import FakeEmailClient
from app.modules.pacientes.models import OptInModel, PacienteModel

TENANT = "tenant-notif-test"
AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def base(session_factory):
    s = session_factory()
    s.add(TenantModel(id=TENANT, nombre="Demo Notif", slug="demo-notif"))
    s.flush()
    s.add(ConfigModel(
        tenant_id=TENANT,
        antelacion_cancel_hs=24,
        antelacion_reserva_hs=2,
        recordatorio_t_48h=True,
        recordatorio_t_24h=True,
        recordatorio_1_hs=48,
        recordatorio_2_hs=24,
        whatsapp_costo_centavos=120,
    ))
    # plantilla activa
    repo = PlantillaRepository(s)
    for canal in ("whatsapp", "email"):
        repo.upsert(PlantillaModel(
            tenant_id=TENANT,
            codigo="recordatorio",
            canal=canal,
            idioma="es-AR",
            cuerpo="Hola {{paciente}} turno {{fecha}} {{link}}",
            activa=True,
            asunto="Rec" if canal == "email" else None,
        ))
    s.commit()
    s.close()
    return session_factory


def _paciente(session, pid="pac-1", telefono="+5491112345678", email="p@test.com", optin=True):
    p = PacienteModel(id=pid, tenant_id=TENANT, nombre="Ana", apellido="Test", telefono=telefono, email=email)
    session.add(p)
    session.flush()
    if optin and telefono:
        session.add(OptInModel(
            id=f"opt-{pid}", tenant_id=TENANT, paciente_id=pid, canal="whatsapp", estado=True,
            updated_at=AHORA,
        ))
    session.flush()


def _turno(session, tid="turno-1", horas=48, estado="confirmado", paciente_id="pac-1"):
    t = TurnoModel(
        id=tid,
        tenant_id=TENANT,
        paciente_id=paciente_id,
        profesional_id="prof-1",
        inicio=AHORA + timedelta(hours=horas),
        fin=AHORA + timedelta(hours=horas, minutes=30),
        estado=estado,
    )
    session.add(t)
    session.flush()
    return t


def test_scheduler_encola_turno_con_optin(base):
    sf = base
    s = sf()
    _paciente(s)
    _turno(s, horas=48)
    s.commit()
    svc = SchedulerService(s, enabled=True, now=AHORA, redis_client=None)
    encolados = svc.ejecutar()
    assert len(encolados) == 1
    envio = s.execute(select(NotificacionEnvioModel)).scalar_one()
    assert envio.canal == "whatsapp"
    assert envio.ventana == "t-48h"
    assert envio.estado == "encolada"
    assert envio.next_attempt_at is not None
    s.close()


def test_scheduler_omitida_sin_canal(base):
    sf = base
    s = sf()
    _paciente(s, pid="pac-2", telefono=None, email=None, optin=False)
    _turno(s, tid="turno-2", horas=48, paciente_id="pac-2")
    s.commit()
    svc = SchedulerService(s, enabled=True, now=AHORA, redis_client=None)
    svc.ejecutar()
    envio = s.execute(select(NotificacionEnvioModel)).scalar_one()
    assert envio.estado == "omitida"
    assert envio.motivo_code == "RN-PA-01"
    s.close()


def test_scheduler_no_reenvia_segundo_tick(base):
    sf = base
    s = sf()
    _paciente(s)
    _turno(s, horas=48)
    s.commit()
    svc = SchedulerService(s, enabled=True, now=AHORA, redis_client=None)
    svc.ejecutar()
    s.commit()
    # segundo tick mismo now
    svc2 = SchedulerService(s, enabled=True, now=AHORA, redis_client=None)
    nuevos = svc2.ejecutar()
    assert nuevos == []
    total = s.execute(select(NotificacionEnvioModel)).scalars().all()
    assert len(total) == 1
    s.close()


def test_sender_exitoso(base):
    sf = base
    s = sf()
    _paciente(s)
    _turno(s, horas=48)
    s.commit()
    svc = SchedulerService(s, enabled=True, now=AHORA, redis_client=None)
    svc.ejecutar()
    s.commit()
    fake = FakeWhatsApp(ok=True, provider_msg_id="wamid-1")
    email = FakeEmailClient()
    sender = SenderService(s, whatsapp=fake, email=email, now=AHORA)
    procesados = sender.ejecutar()
    assert len(procesados) == 1
    envio = s.execute(select(NotificacionEnvioModel)).scalar_one()
    assert envio.estado == "enviada"
    assert envio.provider_msg_id == "wamid-1"
    assert envio.costo_estimado_centavos == 120
    assert envio.enviado_at is not None
    s.close()


def test_sender_fallo_transitorio_y_fallback_email(base):
    sf = base
    s = sf()
    _paciente(s)
    _turno(s, horas=48)
    s.commit()
    svc = SchedulerService(s, enabled=True, now=AHORA, redis_client=None)
    svc.ejecutar()
    s.commit()
    fake = FakeWhatsApp(ok=False, error_code="RN-GL-03", transitorio=True)
    email = FakeEmailClient()
    sender = SenderService(s, whatsapp=fake, email=email, now=AHORA)
    sender.ejecutar()  # intento 1
    s.commit()
    envio = s.execute(select(NotificacionEnvioModel).where(NotificacionEnvioModel.canal == "whatsapp")).scalar_one()
    assert envio.estado == "encolada"
    assert envio.intentos == 1
    # forzar 3 intentos
    envio.next_attempt_at = AHORA
    s.commit()
    sender2 = SenderService(s, whatsapp=fake, email=email, now=AHORA)
    sender2.ejecutar()  # intento 2
    s.commit()
    envio.next_attempt_at = AHORA
    s.commit()
    sender3 = SenderService(s, whatsapp=fake, email=email, now=AHORA)
    sender3.ejecutar()  # intento 3 -> fallida + email fallback
    s.commit()
    wa = s.execute(select(NotificacionEnvioModel).where(NotificacionEnvioModel.canal == "whatsapp")).scalar_one()
    assert wa.estado == "fallida"
    emails = s.execute(select(NotificacionEnvioModel).where(NotificacionEnvioModel.canal == "email")).scalars().all()
    assert len(emails) == 1
    assert emails[0].estado == "encolada"
    assert emails[0].motivo_code == "RN-PA-04"
    s.close()


def test_webhook_firma_y_idempotencia(base):
    from app.modules.notificaciones.webhook import WebhookService, verify_signature
    import hashlib, hmac
    sf = base
    s = sf()
    _paciente(s)
    _turno(s, horas=48)
    s.commit()
    svc = SchedulerService(s, enabled=True, now=AHORA, redis_client=None)
    svc.ejecutar()
    s.commit()
    fake = FakeWhatsApp(ok=True, provider_msg_id="wamid-xyz")
    email = FakeEmailClient()
    sender = SenderService(s, whatsapp=fake, email=email, now=AHORA)
    sender.ejecutar()
    s.commit()
    envio = s.execute(select(NotificacionEnvioModel)).scalar_one()
    envio.provider_msg_id = "wamid-xyz"
    s.commit()

    secret = "appsecret"
    body = b'{"provider_msg_id": "wamid-xyz", "status": "delivered"}'
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(body, sig, secret) is True
    assert verify_signature(body, "sha256=bad", secret) is False

    ws = WebhookService(s, AHORA)
    n1 = ws.procesar({"provider_msg_id": "wamid-xyz", "status": "delivered"})
    s.commit()
    assert n1 == 1
    envio = s.execute(select(NotificacionEnvioModel)).scalar_one()
    assert envio.estado == "entregada"

    # duplicado no cambia
    ws2 = WebhookService(s, AHORA)
    n2 = ws2.procesar({"provider_msg_id": "wamid-xyz", "status": "delivered"})
    s.commit()
    assert n2 == 0
    envio = s.execute(select(NotificacionEnvioModel)).scalar_one()
    assert envio.estado == "entregada"

    # sent después de delivered no retrocede
    ws3 = WebhookService(s, AHORA)
    ws3.procesar({"provider_msg_id": "wamid-xyz", "status": "sent"})
    s.commit()
    envio = s.execute(select(NotificacionEnvioModel)).scalar_one()
    assert envio.estado == "entregada"
    s.close()


def test_acuse_no_cambia_estado(base):
    sf = base
    s = sf()
    _paciente(s)
    t = _turno(s, horas=48, estado="confirmado")
    s.commit()
    from app.modules.agenda.public_booking import PublicBookingService
    svc = PublicBookingService(s)
    svc.confirm(t, AHORA)
    s.commit()
    t2 = s.get(TurnoModel, t.id)
    assert t2.estado == "confirmado"
    assert t2.confirmado_paciente_at is not None
    primero = t2.confirmado_paciente_at
    # idempotente
    svc.confirm(t2, AHORA + timedelta(minutes=5))
    s.commit()
    t3 = s.get(TurnoModel, t.id)
    assert t3.confirmado_paciente_at == primero
    s.close()


def test_api_consumo_y_permisos(base):
    sf = base
    s = sf()
    _paciente(s)
    _turno(s, horas=48)
    s.commit()
    svc = SchedulerService(s, enabled=True, now=AHORA, redis_client=None)
    svc.ejecutar()
    s.commit()
    fake = FakeWhatsApp(ok=True, provider_msg_id="wamid-1")
    email = FakeEmailClient()
    sender = SenderService(s, whatsapp=fake, email=email, now=AHORA)
    sender.ejecutar()
    s.commit()
    s.close()

    client = create_app(session_factory=sf, now_fn=lambda: AHORA)
    from fastapi.testclient import TestClient
    tc = TestClient(client)
    # recepcion no puede ver consumo -> 403
    token_rec = mint_token(user_id="u-rec", tenant_id=TENANT, roles=["recepcion"])
    r = tc.get("/notificaciones/consumo?desde=2026-10-01&hasta=2026-10-31", headers={"Authorization": f"Bearer {token_rec}"})
    assert r.status_code == 403
    # dueno ve consumo
    token_dueno = mint_token(user_id="u-dueno", tenant_id=TENANT, roles=["dueno"])
    r2 = tc.get("/notificaciones/consumo?desde=2026-10-01&hasta=2026-10-31", headers={"Authorization": f"Bearer {token_dueno}"})
    assert r2.status_code == 200
    data = r2.json()
    assert "items" in data
    # aislamiento: otro tenant no ve envíos (tenant inexistente -> 404, sin filtración)
    token_otro = mint_token(user_id="u-otro", tenant_id="tenant-otro", roles=["dueno"])
    r3 = tc.get("/notificaciones/consumo?desde=2026-10-01&hasta=2026-10-31", headers={"Authorization": f"Bearer {token_otro}"})
    assert r3.status_code in (200, 404)
    if r3.status_code == 200:
        assert r3.json()["items"] == []
    # ensure user exists not required for jwt validation

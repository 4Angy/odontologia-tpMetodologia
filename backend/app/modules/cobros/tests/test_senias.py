"""Tests C-12: señas de Mercado Pago (R11: dos casos mínimos por conducta).

Cubre los scenarios de `specs/cobros/senias/spec.md` y el contrato C-08
(integración con la reserva pública). R14: solo datos sintéticos.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.agenda.models import (
    ConfigModel,
    PrestacionModel,
    ProfesionalModel,
    TenantModel,
    TurnoModel,
    UsuarioModel,
    UsuarioRoles,
)
from app.modules.agenda.public_booking import (
    PublicBookingRequest,
    PublicBookingService,
    release_expired_pending_payments,
)
from app.modules.cobros import senias_service
from app.modules.cobros.webhook import (
    build_manifest,
    extract_payment_id,
    verify_signature,
)
from app.modules.cobros import webhook as mp_webhook
from app.modules.cobros.models import SeniaModel
from app.modules.cobros.mp_client import FakeMPClient
from app.modules.cobros.senias_service import SeniaService
from app.modules.cobros.service import CobroService
from app.modules.pacientes.models import PacienteModel, PresupuestoModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture()
def fake_mp():
    """Inyecta el fake de MP como client por defecto y lo limpia al salir."""
    fake = FakeMPClient()
    senias_service.set_default_mp_client(fake)
    yield fake
    senias_service.set_default_mp_client(None)


def _alta_tenant(session, slug: str) -> TenantModel:
    tenant = TenantModel(id=str(uuid.uuid4()), slug=slug, nombre="Demo")
    session.add(tenant)
    session.flush()
    return tenant


def _reserva_payload(*, slug, profesional_id, prestacion_id, now):
    return {
        "tenant_slug": slug,
        "profesional_id": profesional_id,
        "prestacion_id": prestacion_id,
        "inicio": (now + timedelta(days=2)).isoformat(),
        "nombre": "Ana",
        "apellido": "Perez",
        "telefono": "+5491123456789",
        "whatsapp_opt_in": True,
    }


def _fixture_reserva(session, *, slug, con_senia) -> tuple:
    tenant = _alta_tenant(session, slug)
    profesional = ProfesionalModel(
        id=str(uuid.uuid4()), tenant_id=tenant.id, nombre="Dra. Demo"
    )
    prestacion = PrestacionModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        nombre="Limpieza" if con_senia else "Consulta",
        duracion_min=30,
        senia_requerida=con_senia,
        senia_monto_cents=5000 if con_senia else None,
    )
    session.add_all([profesional, prestacion])
    session.flush()
    return tenant, profesional, prestacion


def _reservar(session, *, tenant, profesional, prestacion, key, now):
    request = PublicBookingRequest(
        **_reserva_payload(
            slug=tenant.slug,
            profesional_id=profesional.id,
            prestacion_id=prestacion.id,
            now=now,
        )
    )
    return PublicBookingService(session).create(request, key, now)


def _nueva_sena(
    session,
    *,
    tenant_id: str,
    paciente_id: str,
    turno_id: str,
    monto: int = 5000,
    estado: str = "pendiente",
):
    senia = SeniaModel(
        tenant_id=tenant_id,
        turno_id=turno_id,
        paciente_id=paciente_id,
        monto_cents=monto,
        estado=estado,
        mp_preference_id=f"pref-{uuid.uuid4().hex[:8]}",
    )
    session.add(senia)
    session.flush()
    return senia


def _nuevo_turno(
    session,
    *,
    tenant_id: str,
    paciente_id: str,
    estado: str = "pendiente_confirmacion",
    senia_id: str | None = None,
    senia_pendiente: bool | None = None,
) -> TurnoModel:
    inicio = _utcnow() + timedelta(days=2)
    flag = (senia_id is not None) if senia_pendiente is None else senia_pendiente
    turno = TurnoModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        paciente_id=paciente_id,
        profesional_id=str(uuid.uuid4()),
        inicio=inicio,
        fin=inicio + timedelta(minutes=30),
        estado=estado,
        origen="reserva_publica",
        senia_id=senia_id,
        senia_pendiente_definicion=flag,
    )
    session.add(turno)
    session.flush()
    return turno


def _nuevo_paciente(session, *, tenant_id: str) -> PacienteModel:
    paciente = PacienteModel(tenant_id=tenant_id, nombre="Ana", apellido="Garcia", saldo=0)
    session.add(paciente)
    session.flush()
    return paciente


# ---------- Reserva pública (preferencia + checkout) ----------


def test_reserva_con_sena_requerida_devuelve_checkout_url_y_crea_sena(session, fake_mp):
    tenant, profesional, prestacion = _fixture_reserva(
        session, slug="senia-demo", con_senia=True
    )
    now = _utcnow()
    resultado = _reservar(session, tenant=tenant, profesional=profesional, prestacion=prestacion, key="key-senia-1", now=now)
    session.commit()

    assert resultado.checkout_url, "checkout_url debe ser no vacío"
    turno = session.get(TurnoModel, resultado.turno_id)
    assert turno.senia_id is not None
    senia = session.get(SeniaModel, turno.senia_id)
    assert senia.estado == "pendiente"
    assert senia.monto_cents == 5000
    assert fake_mp.llamadas_preferencia, "debe crear la preferencia en MP"


def test_reserva_sin_sena_no_crea_preferencia_ni_checkout(session, fake_mp):
    tenant, profesional, prestacion = _fixture_reserva(
        session, slug="senia-off", con_senia=False
    )
    now = _utcnow()
    resultado = _reservar(session, tenant=tenant, profesional=profesional, prestacion=prestacion, key="key-senia-2", now=now)
    session.commit()

    assert resultado.checkout_url in (None, "")
    turno = session.get(TurnoModel, resultado.turno_id)
    assert turno.senia_id is None
    assert session.query(SeniaModel).count() == 0


def test_reintento_idempotente_recupera_checkout(session, fake_mp):
    tenant, profesional, prestacion = _fixture_reserva(
        session, slug="senia-replay", con_senia=True
    )
    now = _utcnow()
    primero = _reservar(session, tenant=tenant, profesional=profesional, prestacion=prestacion, key="same-key-3", now=now)
    session.commit()
    segundo = _reservar(session, tenant=tenant, profesional=profesional, prestacion=prestacion, key="same-key-3", now=now)
    assert segundo.turno_id == primero.turno_id
    assert segundo.checkout_url is not None


# ---------- Acreditación por webhook (R8) ----------


def test_webhook_acredita_sena_y_confirma_turno(session, fake_mp):
    tenant = _alta_tenant(session, "webhook-demo")
    paciente = _nuevo_paciente(session, tenant_id=tenant.id)
    turno = _nuevo_turno(session, tenant_id=tenant.id, paciente_id=paciente.id)
    senia = _nueva_sena(
        session, tenant_id=tenant.id, paciente_id=paciente.id, turno_id=turno.id
    )
    session.commit()

    fake_mp.pagos["pay-1"] = {
        "id": 1,
        "status": "approved",
        "external_reference": senia.id,
    }
    procesado = SeniaService(session).acreditar_desde_webhook(payment_id="pay-1")
    session.commit()

    assert procesado is True
    senia = session.get(SeniaModel, senia.id)
    assert senia.estado == "acreditada"
    assert senia.mp_payment_id == "pay-1"
    turno = session.get(TurnoModel, turno.id)
    assert turno.estado == "confirmado"


def test_webhook_duplicado_es_noop(session, fake_mp):
    tenant = _alta_tenant(session, "webhook-dup")
    paciente = _nuevo_paciente(session, tenant_id=tenant.id)
    turno = _nuevo_turno(session, tenant_id=tenant.id, paciente_id=paciente.id)
    senia = _nueva_sena(
        session, tenant_id=tenant.id, paciente_id=paciente.id, turno_id=turno.id
    )
    session.commit()

    fake_mp.pagos["pay-dup"] = {
        "id": 2,
        "status": "approved",
        "external_reference": senia.id,
    }
    servicio = SeniaService(session)
    assert servicio.acreditar_desde_webhook(payment_id="pay-dup") is True
    session.commit()
    # Duplicado inmediato.
    assert servicio.acreditar_desde_webhook(payment_id="pay-dup") is False
    senia = session.get(SeniaModel, senia.id)
    assert senia.mp_payment_id == "pay-dup"  # sin cambios
    # Duplicado después de quedar aplicada también es no-op.
    servicio.aplicar_politica_cancelacion(turno)
    session.commit()
    assert servicio.acreditar_desde_webhook(payment_id="pay-dup") is False
    assert session.get(SeniaModel, senia.id).estado == "aplicada"


def test_webhook_pago_no_aprobado_no_acredita(session, fake_mp):
    tenant = _alta_tenant(session, "webhook-rech")
    paciente = _nuevo_paciente(session, tenant_id=tenant.id)
    turno = _nuevo_turno(session, tenant_id=tenant.id, paciente_id=paciente.id)
    senia = _nueva_sena(
        session, tenant_id=tenant.id, paciente_id=paciente.id, turno_id=turno.id
    )
    session.commit()

    fake_mp.pagos["pay-nok"] = {
        "id": 3,
        "status": "rejected",
        "external_reference": senia.id,
    }
    servicio = SeniaService(session)
    assert servicio.acreditar_desde_webhook(payment_id="pay-nok") is False
    session.commit()
    assert session.get(SeniaModel, senia.id).estado == "pendiente"


# ---------- Firma del webhook ----------


def test_firma_valida_aceptada_e_invalida_rechazada():
    data_id = "12345"
    request_id = "req-1"
    ts = "1700000000"
    secret = "secreto-demo"
    firma = hmac.new(
        secret.encode(),
        build_manifest(data_id, request_id, ts).encode(),
        hashlib.sha256,
    ).hexdigest()

    assert verify_signature(
        data_id=data_id, request_id=request_id, ts=ts, received_v1=firma, secret=secret
    ) is True
    assert verify_signature(
        data_id=data_id, request_id=request_id, ts=ts, received_v1="deadbeef", secret=secret
    ) is False
    assert verify_signature(
        data_id=data_id, request_id=request_id, ts=ts, received_v1=firma, secret="otro"
    ) is False


def test_firma_sin_secreto_permite_dev():
    assert verify_signature(
        data_id="1", request_id=None, ts=None, received_v1=None, secret=None
    ) is True


def test_extract_payment_id_acepta_formatos_de_mp():
    assert extract_payment_id({"type": "payment", "data": {"id": "111"}}) == "111"
    assert extract_payment_id({"topic": "payment", "resource": "/v1/payments/222"}) == "222"
    assert extract_payment_id({"otro": "sin data"}, query_id="333") == "333"
    assert extract_payment_id({"otro": "sin data"}) is None


def test_api_webhook_401_con_firma_invalida(session_factory, monkeypatch):
    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    monkeypatch.setattr(mp_webhook, "webhook_secret", lambda: "s-demo")
    payload = {"type": "payment", "data": {"id": "777"}}
    r = client.post("/webhooks/mercadopago", json=payload)
    assert r.status_code == 401


def test_api_webhook_sin_secreto_acredita(session_factory, fake_mp):
    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    preparar = session_factory()
    tenant = _alta_tenant(preparar, "api-wh")
    paciente = _nuevo_paciente(preparar, tenant_id=tenant.id)
    turno = _nuevo_turno(preparar, tenant_id=tenant.id, paciente_id=paciente.id)
    senia = _nueva_sena(
        preparar, tenant_id=tenant.id, paciente_id=paciente.id, turno_id=turno.id
    )
    preparar.commit()
    senia_id, turno_id = senia.id, turno.id
    preparar.close()
    fake_mp.pagos["pay-api"] = {
        "id": 9,
        "status": "approved",
        "external_reference": senia_id,
    }
    r = client.post(
        "/webhooks/mercadopago",
        json={"type": "payment", "data": {"id": "pay-api"}},
    )
    assert r.status_code == 200
    assert r.json()["processed"] is True

    verify = session_factory()
    assert verify.get(SeniaModel, senia_id).estado == "acreditada"
    turno_db = verify.get(TurnoModel, turno_id)
    assert turno_db.estado == "confirmado"
    verify.close()


# ---------- Arrastre en reprogramación ----------


def test_arrastrar_a_prestacion_sin_sena_queda_aplicada(session):
    tenant = _alta_tenant(session, "drag-off")
    paciente = _nuevo_paciente(session, tenant_id=tenant.id)
    turno_viejo = _nuevo_turno(session, tenant_id=tenant.id, paciente_id=paciente.id)
    senia = _nueva_sena(
        session,
        tenant_id=tenant.id,
        paciente_id=paciente.id,
        turno_id=turno_viejo.id,
        estado="acreditada",
    )
    turno_nuevo = _nuevo_turno(session, tenant_id=tenant.id, paciente_id=paciente.id)
    prestacion_nueva = PrestacionModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        nombre="Consulta simple",
        duracion_min=30,
        senia_requerida=False,
    )
    session.add(prestacion_nueva)
    session.flush()

    SeniaService(session).arrastrar(
        turno_viejo=turno_viejo,
        turno_nuevo=turno_nuevo,
        prestacion_nueva=prestacion_nueva,
    )
    session.commit()

    senia = session.get(SeniaModel, senia.id)
    assert senia.estado == "aplicada"
    assert turno_viejo.senia_id is None
    assert turno_nuevo.senia_id is None
    # El crédito queda reflejado íntegro en el saldo derivado.
    assert CobroService(session)._senias_del_paciente(tenant.id, paciente.id) == senia.monto_cents


def test_arrastrar_a_prestacion_con_sena_mueve_la_sena(session):
    tenant = _alta_tenant(session, "drag-on")
    paciente = _nuevo_paciente(session, tenant_id=tenant.id)
    turno_viejo = _nuevo_turno(session, tenant_id=tenant.id, paciente_id=paciente.id)
    senia = _nueva_sena(
        session,
        tenant_id=tenant.id,
        paciente_id=paciente.id,
        turno_id=turno_viejo.id,
        estado="acreditada",
    )
    turno_nuevo = _nuevo_turno(session, tenant_id=tenant.id, paciente_id=paciente.id)
    prestacion_nueva = PrestacionModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        nombre="Limpieza",
        duracion_min=30,
        senia_requerida=True,
        senia_monto_cents=5000,
    )
    session.add(prestacion_nueva)
    session.flush()

    SeniaService(session).arrastrar(
        turno_viejo=turno_viejo,
        turno_nuevo=turno_nuevo,
        prestacion_nueva=prestacion_nueva,
    )
    session.commit()

    senia = session.get(SeniaModel, senia.id)
    assert senia.estado == "acreditada"
    assert senia.turno_id == turno_nuevo.id
    assert turno_nuevo.senia_id == senia.id
    assert turno_viejo.senia_id is None


def test_reprogramacion_interna_arrastra_sena(session):
    """La reprogramación del mostrador (TurnosService) arrastra la seña."""
    from app.modules.agenda.service import User
    from app.modules.agenda.turnos_service import TurnosService

    tenant = _alta_tenant(session, "drag-internal")
    paciente = _nuevo_paciente(session, tenant_id=tenant.id)
    turno_viejo = _nuevo_turno(
        session, tenant_id=tenant.id, paciente_id=paciente.id, senia_pendiente=False
    )
    senia = _nueva_sena(
        session,
        tenant_id=tenant.id,
        paciente_id=paciente.id,
        turno_id=turno_viejo.id,
        estado="acreditada",
    )
    turno_viejo.senia_id = senia.id
    session.flush()

    prestacion = PrestacionModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        nombre="Consulta",
        duracion_min=30,
        senia_requerida=False,
    )
    profesional = ProfesionalModel(
        id=turno_viejo.profesional_id, tenant_id=tenant.id, nombre="Profe"
    )
    session.add_all([prestacion, profesional])
    session.flush()

    class _Request:
        profesional_id = turno_viejo.profesional_id
        inicio = turno_viejo.inicio + timedelta(days=1)
        fin = turno_viejo.inicio + timedelta(days=1, minutes=30)
        prestacion_id = prestacion.id

    servicio = TurnosService(
        repo=_TurnoRepoStub(session),
        pacientes=_StubRepo(session),
        prestaciones=_StubRepo(session),
        disponibilidad=lambda **_: [],
    )
    _, nuevo = servicio.reprogramar_turno(
        tenant_id=tenant.id,
        turno_id=turno_viejo.id,
        user=User(id="u1", tenant_id=tenant.id, roles=("recepcion",)),
        request=_Request(),
        ahora_utc=_utcnow(),
    )
    session.commit()

    senia = session.get(SeniaModel, senia.id)
    assert senia.estado == "aplicada"
    nuevo_db = session.get(TurnoModel, nuevo.id)
    assert nuevo_db.estado == "confirmado"
    # La seña aplicada NO viaja al turno nuevo (no requiere seña).
    assert nuevo_db.senia_id is None
    assert session.get(TurnoModel, turno_viejo.id).senia_id is None


class _StubRepo:
    def __init__(self, session):
        self.session = session

    def get_by_id(self, tenant_id, item_id):
        return self.session.get(PrestacionModel, item_id)


class _TurnoRepoStub:
    def __init__(self, session):
        self.session = session

    def get_by_id(self, tenant_id, turno_id):
        from sqlalchemy import select

        return self.session.execute(
            select(TurnoModel).where(
                TurnoModel.tenant_id == tenant_id, TurnoModel.id == turno_id
            )
        ).scalar_one_or_none()

    def get_for_update(self, tenant_id, turno_id):
        return self.get_by_id(tenant_id, turno_id)

    def lock_profesional(self, tenant_id, profesional_id, require_active=False):
        from sqlalchemy import select

        stmt = select(ProfesionalModel).where(
            ProfesionalModel.tenant_id == tenant_id,
            ProfesionalModel.id == profesional_id,
        )
        if require_active:
            stmt = stmt.where(ProfesionalModel.activo.is_(True))
        return self.session.execute(stmt).scalar_one_or_none()

    def list_solapados(
        self, tenant_id, profesional_id, inicio, fin, excluir_turno_id=None
    ):
        return []

    def create(self, turno):
        self.session.add(turno)
        self.session.flush()
        return turno


# ---------- Política de devolución (RN-CO-03) ----------


def _fixture_politica(session, *, slug, politica, monto=5000):
    tenant = _alta_tenant(session, slug)
    session.add(
        ConfigModel(tenant_id=tenant.id, politica_devolucion_senia=politica)
    )
    session.flush()
    paciente = _nuevo_paciente(session, tenant_id=tenant.id)
    turno = _nuevo_turno(
        session, tenant_id=tenant.id, paciente_id=paciente.id, estado="confirmado"
    )
    senia = _nueva_sena(
        session,
        tenant_id=tenant.id,
        paciente_id=paciente.id,
        turno_id=turno.id,
        monto=monto,
        estado="acreditada",
    )
    turno.senia_id = senia.id
    session.flush()
    return tenant, paciente, turno, senia


def test_politica_default_devuelve_100_saldo_afavor_completo(session):
    tenant, paciente, turno, senia = _fixture_politica(
        session, slug="pol-100", politica="devuelve_100"
    )
    resultado = SeniaService(session).aplicar_politica_cancelacion(turno)
    session.commit()
    assert resultado.estado == "aplicada"
    assert (
        CobroService(session)._senias_del_paciente(tenant.id, paciente.id)
        == senia.monto_cents
    )


def test_politica_devuelve_50_credito_parcial(session):
    tenant, paciente, turno, senia = _fixture_politica(
        session, slug="pol-50", politica="devuelve_50", monto=5000
    )
    SeniaService(session).aplicar_politica_cancelacion(turno)
    session.commit()
    senia = session.get(SeniaModel, senia.id)
    assert senia.estado == "devuelta"
    assert senia.monto_afavor_cents == 2500
    assert CobroService(session)._senias_del_paciente(tenant.id, paciente.id) == 2500


def test_politica_no_devuelve_sin_credito(session):
    tenant, paciente, turno, senia = _fixture_politica(
        session, slug="pol-0", politica="no_devuelve"
    )
    SeniaService(session).aplicar_politica_cancelacion(turno)
    session.commit()
    senia = session.get(SeniaModel, senia.id)
    assert senia.estado == "devuelta"
    assert senia.monto_afavor_cents == 0
    assert CobroService(session)._senias_del_paciente(tenant.id, paciente.id) == 0


# ---------- Timeout (C-08) ----------


def test_timeout_marca_sena_devuelta(session, fake_mp):
    tenant, profesional, prestacion = _fixture_reserva(
        session, slug="timeout-demo", con_senia=True
    )
    session.add(ConfigModel(tenant_id=tenant.id, public_payment_timeout_min=30))
    session.flush()

    now = _utcnow()
    booking = _reservar(
        session,
        tenant=tenant,
        profesional=profesional,
        prestacion=prestacion,
        key="key-timeout",
        now=now,
    )
    session.commit()
    turno = session.get(TurnoModel, booking.turno_id)
    assert turno.senia_id is not None

    liberados = release_expired_pending_payments(session, now + timedelta(minutes=31))
    session.commit()
    assert liberados == 1
    senia = session.get(SeniaModel, turno.senia_id)
    assert senia.estado == "devuelta"
    assert turno.estado == "cancelado"


# ---------- Saldo derivado ----------


def test_saldo_derivado_resta_sena_acreditada(session):
    tenant = _alta_tenant(session, "saldo-demo")
    paciente = _nuevo_paciente(session, tenant_id=tenant.id)
    session.add(
        PresupuestoModel(
            tenant_id=tenant.id,
            paciente_id=paciente.id,
            total_cents=10000,
            estado="aprobado",
        )
    )
    session.flush()

    servicio = CobroService(session)
    assert servicio.saldo_derivado(tenant.id, paciente.id) == 10000

    turno = _nuevo_turno(session, tenant_id=tenant.id, paciente_id=paciente.id)
    _nueva_sena(
        session,
        tenant_id=tenant.id,
        paciente_id=paciente.id,
        turno_id=turno.id,
        monto=4000,
        estado="acreditada",
    )
    session.commit()
    assert servicio.saldo_derivado(tenant.id, paciente.id) == 6000


def test_saldo_derivado_sena_pendiente_no_afecta(session):
    tenant = _alta_tenant(session, "saldo-pend")
    paciente = _nuevo_paciente(session, tenant_id=tenant.id)
    session.add(
        PresupuestoModel(
            tenant_id=tenant.id,
            paciente_id=paciente.id,
            total_cents=10000,
            estado="aprobado",
        )
    )
    session.flush()
    turno = _nuevo_turno(
        session, tenant_id=tenant.id, paciente_id=paciente.id, estado="confirmado"
    )
    _nueva_sena(
        session,
        tenant_id=tenant.id,
        paciente_id=paciente.id,
        turno_id=turno.id,
        monto=4000,
        estado="pendiente",
    )
    session.commit()
    assert CobroService(session).saldo_derivado(tenant.id, paciente.id) == 10000


# ---------- API de señas ----------


def _token_dueno(session, tenant) -> str:
    from app.core.security import mint_token

    usuario = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email="u@test.com",
        nombre="Dueno Test",
        roles=[UsuarioRoles.DUENO.value],
        activo=True,
    )
    session.add(usuario)
    session.commit()
    return mint_token(
        user_id=usuario.id,
        tenant_id=tenant.id,
        roles=usuario.roles,
        email=usuario.email,
        token_type="access",
    )


def test_api_senias_lista_por_turno(session_factory):
    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    preparar = session_factory()
    tenant = _alta_tenant(preparar, "api-senias")
    paciente = _nuevo_paciente(preparar, tenant_id=tenant.id)
    turno = _nuevo_turno(preparar, tenant_id=tenant.id, paciente_id=paciente.id)
    senia = _nueva_sena(
        preparar,
        tenant_id=tenant.id,
        paciente_id=paciente.id,
        turno_id=turno.id,
        estado="acreditada",
    )
    token = _token_dueno(preparar, tenant)
    senia_id, turno_id = senia.id, turno.id
    preparar.close()

    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/senias", params={"turno_id": turno_id}, headers=headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == senia_id
    assert items[0]["estado"] == "acreditada"

    r2 = client.get(f"/senias/{senia_id}", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["mp_payment_id"] is None

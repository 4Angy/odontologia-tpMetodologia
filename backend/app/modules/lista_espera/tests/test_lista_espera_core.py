from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.security import mint_token
from app.main import create_app
from app.modules.agenda.models import (
    ConfigModel,
    ProfesionalModel,
    TenantModel,
    TurnoModel,
    UsuarioModel,
    UsuarioRoles,
)
from app.modules.lista_espera.models import ListaEsperaModel
from app.modules.lista_espera.repository import ListaEsperaRepository
from app.modules.lista_espera.service import Hueco, ListaEsperaService
from app.modules.notificaciones.models import NotificacionEnvioModel
from app.modules.pacientes.models import OptInModel, PacienteModel

TENANT = "tenant-le-test"
AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def base(session_factory):
    s = session_factory()
    s.add(TenantModel(id=TENANT, nombre="Demo LE", slug="demo-le"))
    s.flush()
    s.add(ProfesionalModel(id="prof-1", tenant_id=TENANT, nombre="Dr. Test"))
    s.flush()
    s.add(ConfigModel(
        tenant_id=TENANT,
        antelacion_cancel_hs=24,
        lista_espera_ttl_hs=2,
        whatsapp_costo_centavos=100,
    ))
    s.add(UsuarioModel(
        id="user-recep-le", tenant_id=TENANT, email="r@le.test",
        nombre="Recepcion", roles=[UsuarioRoles.RECEPCION.value], activo=True,
    ))
    s.commit()
    s.close()
    return session_factory


def _paciente(session, pid="pac-1", telefono="+5491112345678", optin=True):
    p = PacienteModel(id=pid, tenant_id=TENANT, nombre="Ana", apellido="Test", telefono=telefono)
    session.add(p)
    session.flush()
    if optin and telefono:
        session.add(OptInModel(
            id=f"opt-{pid}", tenant_id=TENANT, paciente_id=pid, canal="whatsapp", estado=True,
            updated_at=AHORA,
        ))
    session.flush()


def test_alta_y_listado(base):
    sf = base
    s = sf()
    _paciente(s)
    entry = ListaEsperaModel(tenant_id=TENANT, paciente_id="pac-1", prioridad=1)
    s.add(entry)
    s.flush()
    repo = ListaEsperaRepository(s)
    items = repo.list(TENANT, estado="activa")
    assert len(items) == 1
    assert items[0].estado == "activa"
    s.close()


def test_oferta_al_primero_compatible(base):
    sf = base
    s = sf()
    _paciente(s, pid="pac-1", optin=True)
    _paciente(s, pid="pac-2", telefono="+5491199999999", optin=True)
    for pid in ("pac-1", "pac-2"):
        s.add(ListaEsperaModel(tenant_id=TENANT, paciente_id=pid, prioridad=0))
    s.flush()
    svc = ListaEsperaService(s, AHORA)
    hueco = Hueco(profesional_id="prof-1", inicio=AHORA + timedelta(hours=24), fin=AHORA + timedelta(hours=24, minutes=30), prestacion_id="prest-1")
    offered = svc.ofrecer_por_hueco(TENANT, hueco, AHORA)
    assert offered is not None
    assert offered.estado == "ofrecida"
    assert offered.paciente_id == "pac-1"
    envios = s.execute(select(NotificacionEnvioModel)).scalars().all()
    assert any(e.estado == "encolada" and e.plantilla_codigo == "lista_espera" for e in envios)
    s.close()


def test_skip_sin_optin(base):
    sf = base
    s = sf()
    _paciente(s, pid="pac-1", telefono=None, optin=False)
    _paciente(s, pid="pac-2", telefono="+5491199999999", optin=True)
    for pid in ("pac-1", "pac-2"):
        s.add(ListaEsperaModel(tenant_id=TENANT, paciente_id=pid, prioridad=0))
    s.flush()
    svc = ListaEsperaService(s, AHORA)
    hueco = Hueco(profesional_id="prof-1", inicio=AHORA + timedelta(hours=24), fin=AHORA + timedelta(hours=24, minutes=30))
    offered = svc.ofrecer_por_hueco(TENANT, hueco, AHORA)
    assert offered is not None
    assert offered.paciente_id == "pac-2"
    envios = s.execute(select(NotificacionEnvioModel)).scalars().all()
    assert any(e.estado == "omitida" and e.motivo_code == "RN-PA-01" for e in envios)
    s.close()


def test_vencimiento_avanza(base):
    sf = base
    s = sf()
    _paciente(s, pid="pac-1", optin=True)
    _paciente(s, pid="pac-2", telefono="+5491199999999", optin=True)
    for pid in ("pac-1", "pac-2"):
        s.add(ListaEsperaModel(tenant_id=TENANT, paciente_id=pid, prioridad=0))
    s.flush()
    svc = ListaEsperaService(s, AHORA)
    hueco = Hueco(profesional_id="prof-1", inicio=AHORA + timedelta(hours=24), fin=AHORA + timedelta(hours=24, minutes=30))
    offered = svc.ofrecer_por_hueco(TENANT, hueco, AHORA)
    assert offered.paciente_id == "pac-1"
    # vencer
    futuro = AHORA + timedelta(hours=3)
    svc2 = ListaEsperaService(s, futuro)
    n = svc2.vencer_y_avanzar(futuro)
    assert n == 1
    # pac-1 vencida, pac-2 ofrecida
    repo = ListaEsperaRepository(s)
    e1 = [e for e in repo.list(TENANT) if e.paciente_id == "pac-1"][0]
    e2 = [e for e in repo.list(TENANT) if e.paciente_id == "pac-2"][0]
    assert e1.estado == "vencida"
    assert e2.estado == "ofrecida"
    s.close()

def test_aceptar_crea_turno(base):
    sf = base
    s = sf()
    _paciente(s, pid="pac-1", optin=True)
    s.add(ListaEsperaModel(tenant_id=TENANT, paciente_id="pac-1", prioridad=0))
    s.flush()
    svc = ListaEsperaService(s, AHORA)
    hueco = Hueco(profesional_id="prof-1", inicio=AHORA + timedelta(hours=24), fin=AHORA + timedelta(hours=24, minutes=30))
    offered = svc.ofrecer_por_hueco(TENANT, hueco, AHORA)
    assert offered is not None
    tokens = svc._generar_tokens(TENANT, offered.id, offered.expires_at)
    raw = tokens["waitlist_accept"]
    entry, turno = svc.aceptar(raw, "demo-le", AHORA)
    assert entry.estado == "convertida"
    assert turno.origen == "lista_espera"
    assert turno.estado == "confirmado"
    s.close()


def test_declinar_avanza(base):
    sf = base
    s = sf()
    _paciente(s, pid="pac-1", optin=True)
    _paciente(s, pid="pac-2", telefono="+5491199999999", optin=True)
    for pid in ("pac-1", "pac-2"):
        s.add(ListaEsperaModel(tenant_id=TENANT, paciente_id=pid, prioridad=0))
    s.flush()
    svc = ListaEsperaService(s, AHORA)
    hueco = Hueco(profesional_id="prof-1", inicio=AHORA + timedelta(hours=24), fin=AHORA + timedelta(hours=24, minutes=30))
    offered = svc.ofrecer_por_hueco(TENANT, hueco, AHORA)
    assert offered is not None
    tokens = svc._generar_tokens(TENANT, offered.id, offered.expires_at)
    svc.declinar(tokens["waitlist_decline"], "demo-le", AHORA)
    repo = ListaEsperaRepository(s)
    e1 = [e for e in repo.list(TENANT) if e.paciente_id == "pac-1"][0]
    e2 = [e for e in repo.list(TENANT) if e.paciente_id == "pac-2"][0]
    assert e1.estado == "vencida"
    assert e2.estado == "ofrecida"
    s.close()

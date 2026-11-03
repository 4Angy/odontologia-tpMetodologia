from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.modules.agenda.models import TurnoModel
from app.modules.agenda.service import AgendaError, User
from app.modules.agenda.turnos_service import TurnosService

TENANT = "tenant-c07"
PROFESIONAL = "prof-c07"
PACIENTE = "pac-c07"
PRESTACION = "prest-c07"
AHORA = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


class FakeTurnoRepository:
    def __init__(self, *, turnos=None):
        self.profesionales = {
            (TENANT, PROFESIONAL): SimpleNamespace(
                id=PROFESIONAL,
                tenant_id=TENANT,
                usuario_id="odontologo-c07",
                activo=True,
            )
        }
        self.turnos = list(turnos or [])

    def lock_profesional(self, tenant_id, profesional_id, *, require_active=True):
        profesional = self.profesionales.get((tenant_id, profesional_id))
        if require_active and profesional is not None and not profesional.activo:
            return None
        return profesional

    def get_by_id(self, tenant_id, turno_id):
        return next(
            (
                turno
                for turno in self.turnos
                if turno.tenant_id == tenant_id and turno.id == turno_id
            ),
            None,
        )

    def get_by_idempotency_key(self, tenant_id, key):
        return next(
            (
                turno
                for turno in self.turnos
                if turno.tenant_id == tenant_id and turno.idempotency_key == key
            ),
            None,
        )

    def get_for_update(self, tenant_id, turno_id):
        return next(
            (
                turno
                for turno in self.turnos
                if turno.tenant_id == tenant_id and turno.id == turno_id
            ),
            None,
        )

    def list_solapados(self, *, tenant_id, profesional_id, inicio, fin, excluir_turno_id=None):
        return [
            turno
            for turno in self.turnos
            if turno.tenant_id == tenant_id
            and turno.profesional_id == profesional_id
            and turno.estado in {"confirmado", "pendiente_confirmacion"}
            and turno.id != excluir_turno_id
            and turno.inicio < fin
            and turno.fin > inicio
        ]

    def create(self, turno):
        self.turnos.append(turno)
        return turno


class FakePacienteRepository:
    def get_by_id(self, tenant_id, paciente_id):
        if tenant_id == TENANT and paciente_id == PACIENTE:
            return SimpleNamespace(id=paciente_id, tenant_id=tenant_id)
        return None


class FakePrestacionRepository:
    def get_by_id(self, tenant_id, prestacion_id):
        if tenant_id == TENANT and prestacion_id == PRESTACION:
            return SimpleNamespace(
                id=prestacion_id,
                tenant_id=tenant_id,
                duracion_min=30,
                activa=True,
            )
        return None


def _request(**overrides):
    values = {
        "paciente_id": PACIENTE,
        "profesional_id": PROFESIONAL,
        "prestacion_id": PRESTACION,
        "inicio": AHORA + timedelta(days=1),
        "fin": AHORA + timedelta(days=1, minutes=30),
        "sobreturno": False,
        "sobreturno_motivo": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _service(repo=None, disponibilidad=None):
    return TurnosService(
        repo=repo or FakeTurnoRepository(),
        pacientes=FakePacienteRepository(),
        prestaciones=FakePrestacionRepository(),
        disponibilidad=disponibilidad or (lambda **_kwargs: []),
    )


def _recepcion():
    return User(id="user-recepcion", tenant_id=TENANT, roles=("recepcion",))


def test_crear_turno_confirmado_y_reintento_idempotente_no_duplica():
    repo = FakeTurnoRepository()
    service = _service(repo)

    primero = service.crear_turno(
        user=_recepcion(),
        request=_request(),
        idempotency_key="key-1",
        ahora_utc=AHORA,
    )
    segundo = service.crear_turno(
        user=_recepcion(),
        request=_request(),
        idempotency_key="key-1",
        ahora_utc=AHORA + timedelta(minutes=1),
    )

    assert isinstance(primero.turno, TurnoModel)
    assert primero.creado is True
    assert primero.turno.estado == "confirmado"
    assert primero.turno.origen == "mostrador"
    assert primero.turno.profesional_usuario_id == "odontologo-c07"
    assert segundo.creado is False
    assert segundo.turno.id == primero.turno.id
    assert len(repo.turnos) == 1


def test_reutilizar_clave_idempotente_con_payload_distinto_devuelve_conflicto():
    repo = FakeTurnoRepository()
    service = _service(repo)
    service.crear_turno(
        user=_recepcion(),
        request=_request(),
        idempotency_key="key-1",
        ahora_utc=AHORA,
    )

    with pytest.raises(AgendaError) as error:
        service.crear_turno(
            user=_recepcion(),
            request=_request(inicio=AHORA + timedelta(days=2), fin=AHORA + timedelta(days=2, minutes=30)),
            idempotency_key="key-1",
            ahora_utc=AHORA,
        )

    assert error.value.code == "RN-AG-03"
    assert error.value.status == 409
    assert len(repo.turnos) == 1


def test_colision_usa_hasta_tres_alternativas_mas_cercanas_con_empate_anterior():
    turno_existente = TurnoModel(
        id="turno-existente",
        tenant_id=TENANT,
        paciente_id=PACIENTE,
        profesional_id=PROFESIONAL,
        inicio=AHORA + timedelta(days=1),
        fin=AHORA + timedelta(days=1, minutes=30),
        estado="confirmado",
    )
    repo = FakeTurnoRepository(turnos=[turno_existente])
    requested = AHORA + timedelta(days=1)
    opciones = [
        requested - timedelta(minutes=60),
        requested - timedelta(minutes=30),
        requested + timedelta(minutes=30),
        requested + timedelta(minutes=60),
    ]
    service = _service(
        repo,
        disponibilidad=lambda **_kwargs: opciones,
    )

    with pytest.raises(AgendaError) as error:
        service.crear_turno(
            user=_recepcion(),
            request=_request(),
            idempotency_key="key-2",
            ahora_utc=AHORA,
        )

    assert error.value.code == "RN-AG-03"
    assert error.value.status == 409
    assert error.value.alternativas == [
        requested - timedelta(minutes=30),
        requested + timedelta(minutes=30),
        requested - timedelta(minutes=60),
    ]


def test_sobreturno_sin_motivo_o_permiso_es_rechazado():
    service = _service()
    with pytest.raises(AgendaError) as sin_motivo:
        service.crear_turno(
            user=_recepcion(),
            request=_request(sobreturno=True),
            idempotency_key="key-3",
            ahora_utc=AHORA,
        )
    assert sin_motivo.value.status == 422

    with pytest.raises(AgendaError) as sin_permiso:
        service.crear_turno(
            user=User(id="odonto", tenant_id=TENANT, roles=("odontologo",)),
            request=_request(
                sobreturno=True,
                sobreturno_motivo="Urgencia",
            ),
            idempotency_key="key-4",
            ahora_utc=AHORA,
        )
    assert sin_permiso.value.status == 403


def test_sobreturno_autorizado_con_motivo_ignora_solape_y_registra_actor():
    turno_existente = TurnoModel(
        id="turno-existente",
        tenant_id=TENANT,
        paciente_id=PACIENTE,
        profesional_id=PROFESIONAL,
        inicio=AHORA + timedelta(days=1),
        fin=AHORA + timedelta(days=1, minutes=30),
        estado="confirmado",
    )
    repo = FakeTurnoRepository(turnos=[turno_existente])

    resultado = _service(repo).crear_turno(
        user=_recepcion(),
        request=_request(sobreturno=True, sobreturno_motivo="Urgencia clínica"),
        idempotency_key="key-5",
        ahora_utc=AHORA,
    )

    assert resultado.turno.sobreturno is True
    assert resultado.turno.sobreturno_motivo == "Urgencia clínica"
    assert resultado.turno.sobreturno_autorizado_por == "user-recepcion"


def test_creacion_rechaza_paciente_ajeno_y_duracion_incompatible():
    service = _service()
    with pytest.raises(AgendaError) as paciente_ajeno:
        service.crear_turno(
            user=_recepcion(),
            request=_request(paciente_id="paciente-otro-tenant"),
            idempotency_key="key-6",
            ahora_utc=AHORA,
        )
    assert paciente_ajeno.value.status == 404

    with pytest.raises(AgendaError) as duracion_invalida:
        service.crear_turno(
            user=_recepcion(),
            request=_request(fin=AHORA + timedelta(days=1, minutes=45)),
            idempotency_key="key-7",
            ahora_utc=AHORA,
        )
    assert duracion_invalida.value.code == "RN-AG-03"
    assert duracion_invalida.value.status == 422


def test_creacion_rechaza_datetimes_naive():
    service = _service()
    with pytest.raises(AgendaError) as error:
        service.crear_turno(
            user=_recepcion(),
            request=_request(inicio=datetime(2026, 10, 8, 12, 0)),
            idempotency_key="key-8",
            ahora_utc=AHORA,
        )
    assert error.value.code == "RN-GL-02"
    assert error.value.status == 422


def test_confirmar_solo_transiciona_pendiente_a_confirmado():
    turno = TurnoModel(
        id="turno-pendiente",
        tenant_id=TENANT,
        paciente_id=PACIENTE,
        profesional_id=PROFESIONAL,
        inicio=AHORA + timedelta(days=1),
        fin=AHORA + timedelta(days=1, minutes=30),
        estado="pendiente_confirmacion",
    )
    service = _service(FakeTurnoRepository(turnos=[turno]))

    resultado = service.confirmar_turno(
        tenant_id=TENANT,
        turno_id=turno.id,
        user=_recepcion(),
    )
    assert resultado.estado == "confirmado"

    with pytest.raises(AgendaError) as error:
        service.confirmar_turno(
            tenant_id=TENANT,
            turno_id=turno.id,
            user=_recepcion(),
        )
    assert error.value.status == 409


def test_asistencia_requiere_turno_confirmado_y_rol_de_gestion():
    turno = TurnoModel(
        id="turno-confirmado",
        tenant_id=TENANT,
        paciente_id=PACIENTE,
        profesional_id=PROFESIONAL,
        inicio=AHORA,
        fin=AHORA + timedelta(minutes=30),
        estado="confirmado",
    )
    service = _service(FakeTurnoRepository(turnos=[turno]))

    with pytest.raises(AgendaError) as temprano:
        service.marcar_ausente(
            tenant_id=TENANT,
            turno_id=turno.id,
            user=_recepcion(),
            ahora_utc=AHORA + timedelta(minutes=29),
        )
    assert temprano.value.status == 409
    assert turno.estado == "confirmado"

    with pytest.raises(AgendaError) as sin_permiso:
        service.marcar_presente(
            tenant_id=TENANT,
            turno_id=turno.id,
            user=User(id="odonto", tenant_id=TENANT, roles=("odontologo",)),
        )
    assert sin_permiso.value.status == 403

    assert service.marcar_presente(
        tenant_id=TENANT,
        turno_id=turno.id,
        user=_recepcion(),
    ).estado == "presente"


def test_reprogramar_conserva_turno_terminal_y_no_mueve_senia():
    turno = TurnoModel(
        id="turno-a-reprogramar",
        tenant_id=TENANT,
        paciente_id=PACIENTE,
        profesional_id=PROFESIONAL,
        profesional_usuario_id="odontologo-c07",
        prestacion_id=PRESTACION,
        inicio=AHORA + timedelta(days=1),
        fin=AHORA + timedelta(days=1, minutes=30),
        estado="confirmado",
        senia_id="senia-sintetica",
    )
    repo = FakeTurnoRepository(turnos=[turno])

    anterior, nuevo = _service(repo).reprogramar_turno(
        tenant_id=TENANT,
        turno_id=turno.id,
        user=_recepcion(),
        request=_request(
            profesional_id=PROFESIONAL,
            inicio=AHORA + timedelta(days=2),
            fin=AHORA + timedelta(days=2, minutes=30),
        ),
        ahora_utc=AHORA,
    )

    assert anterior.estado == "reprogramado"
    assert anterior.senia_id == "senia-sintetica"
    assert nuevo.estado == "confirmado"
    assert nuevo.senia_id is None
    assert nuevo.paciente_id == PACIENTE
    assert len(repo.turnos) == 2


def test_reprogramacion_con_colision_no_modifica_turno_original():
    inicio = AHORA + timedelta(days=2)
    anterior = TurnoModel(
        id="turno-a-reprogramar",
        tenant_id=TENANT,
        paciente_id=PACIENTE,
        profesional_id=PROFESIONAL,
        inicio=AHORA + timedelta(days=1),
        fin=AHORA + timedelta(days=1, minutes=30),
        estado="confirmado",
    )
    colision = TurnoModel(
        id="turno-colision",
        tenant_id=TENANT,
        paciente_id=PACIENTE,
        profesional_id=PROFESIONAL,
        inicio=inicio,
        fin=inicio + timedelta(minutes=30),
        estado="confirmado",
    )
    repo = FakeTurnoRepository(turnos=[anterior, colision])

    with pytest.raises(AgendaError) as error:
        _service(repo).reprogramar_turno(
            tenant_id=TENANT,
            turno_id=anterior.id,
            user=_recepcion(),
            request=_request(inicio=inicio, fin=inicio + timedelta(minutes=30)),
            ahora_utc=AHORA,
        )

    assert error.value.code == "RN-AG-03"
    assert anterior.estado == "confirmado"
    assert len(repo.turnos) == 2

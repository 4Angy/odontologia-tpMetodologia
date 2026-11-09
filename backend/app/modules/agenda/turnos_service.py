"""Servicios de dominio para la agenda interna."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy.exc import IntegrityError

from app.modules.agenda.models import TurnoModel
from app.modules.agenda.service import AgendaError, User


class ColisionTurnoError(AgendaError):
    def __init__(self, alternativas: list[datetime]) -> None:
        super().__init__(
            code="RN-AG-03",
            message="El profesional ya tiene un turno en ese horario.",
            status=409,
        )
        self.alternativas = alternativas


@dataclass(frozen=True)
class CreacionTurno:
    turno: TurnoModel
    creado: bool


class TurnosService:
    def __init__(
        self,
        *,
        repo,
        pacientes,
        prestaciones,
        disponibilidad: Callable[..., list[datetime]],
    ) -> None:
        self.repo = repo
        self.pacientes = pacientes
        self.prestaciones = prestaciones
        self.disponibilidad = disponibilidad

    def confirmar_turno(
        self, *, tenant_id: str, turno_id: str, user: User
    ) -> TurnoModel:
        turno = self._obtener_para_mutar(tenant_id, turno_id, user)
        if turno.estado != "pendiente_confirmacion":
            raise _transicion_invalida()
        turno.estado = "confirmado"
        return turno

    def marcar_presente(
        self, *, tenant_id: str, turno_id: str, user: User
    ) -> TurnoModel:
        turno = self._obtener_para_mutar(tenant_id, turno_id, user)
        if turno.estado != "confirmado":
            raise _transicion_invalida()
        turno.estado = "presente"
        return turno

    def marcar_ausente(
        self,
        *,
        tenant_id: str,
        turno_id: str,
        user: User,
        ahora_utc: datetime,
    ) -> TurnoModel:
        turno = self._obtener_para_mutar(tenant_id, turno_id, user)
        ahora = _a_utc(ahora_utc, "ahora_utc")
        if turno.estado != "confirmado" or ahora < turno.fin.astimezone(timezone.utc):
            raise _transicion_invalida()
        turno.estado = "ausente"
        return turno

    def reprogramar_turno(
        self,
        *,
        tenant_id: str,
        turno_id: str,
        user: User,
        request,
        ahora_utc: datetime,
    ) -> tuple[TurnoModel, TurnoModel]:
        if tenant_id != user.tenant_id:
            raise _turno_no_encontrado()
        if not _puede_gestionar_agenda(user):
            raise AgendaError(
                "RN-AU-04",
                "No tenés permiso para reprogramar turnos.",
                403,
            )
        turno = self.repo.get_by_id(tenant_id, turno_id)
        if turno is None:
            raise _turno_no_encontrado()
        if turno.estado not in {"confirmado", "pendiente_confirmacion"}:
            raise _transicion_invalida()

        profesional_ids = sorted({turno.profesional_id, request.profesional_id})
        profesionales = {
            profesional_id: self.repo.lock_profesional(
                tenant_id,
                profesional_id,
                require_active=profesional_id == request.profesional_id,
            )
            for profesional_id in profesional_ids
        }
        turno = self.repo.get_for_update(tenant_id, turno_id)
        if turno is None:
            raise _turno_no_encontrado()
        if turno.profesional_id not in profesionales:
            raise _transicion_invalida()
        profesional = profesionales[request.profesional_id]
        if profesional is None:
            raise AgendaError("RN-AU-01", "Profesional no encontrado.", 404)

        inicio = _a_utc(request.inicio, "inicio")
        fin = _a_utc(request.fin, "fin")
        if fin <= inicio:
            raise AgendaError("RN-GL-02", "El fin debe ser posterior al inicio.", 422)

        prestacion_id = request.prestacion_id
        if prestacion_id is not None:
            prestacion = self.prestaciones.get_by_id(tenant_id, prestacion_id)
            if prestacion is None or not prestacion.activa:
                raise AgendaError("RN-AU-01", "Prestación no encontrada.", 404)
            if fin - inicio != timedelta(minutes=prestacion.duracion_min):
                raise AgendaError(
                    "RN-AG-03",
                    "La duración del turno no coincide con la prestación.",
                    422,
                )

        colisiones = self.repo.list_solapados(
            tenant_id=tenant_id,
            profesional_id=profesional.id,
            inicio=inicio,
            fin=fin,
            excluir_turno_id=turno.id,
        )
        if colisiones:
            alternativas = self.disponibilidad(
                tenant_id=tenant_id,
                profesional_id=profesional.id,
                prestacion_id=prestacion_id,
                desde=inicio - timedelta(days=30),
                hasta=inicio + timedelta(days=30),
                ahora_utc=_a_utc(ahora_utc, "ahora_utc"),
            )
            raise ColisionTurnoError(
                sorted(
                    {_a_utc(opcion, "alternativa") for opcion in alternativas},
                    key=lambda opcion: (abs((opcion - inicio).total_seconds()), opcion),
                )[:3]
            )

        turno.estado = "reprogramado"
        nuevo_turno = TurnoModel(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            paciente_id=turno.paciente_id,
            profesional_id=profesional.id,
            profesional_usuario_id=profesional.usuario_id,
            prestacion_id=prestacion_id,
            inicio=inicio,
            fin=fin,
            estado="confirmado",
            origen="mostrador",
            sobreturno=False,
        )
        # C-12 (D4): arrastre de la seña acreditada; si la prestación nueva no
        # requiere seña, la seña queda como saldo a favor del paciente.
        # Fakes sin `repo.session` (contratos de C-07) conservan el legado.
        repo_session = getattr(self.repo, "session", None)
        if repo_session is not None:
            from app.modules.cobros.senias_service import SeniaService

            SeniaService(repo_session).arrastrar(
                turno_viejo=turno,
                turno_nuevo=nuevo_turno,
                prestacion_nueva=prestacion if prestacion_id is not None else None,
            )
        return turno, self.repo.create(nuevo_turno)

    def crear_turno(
        self,
        *,
        user: User,
        request,
        idempotency_key: str,
        ahora_utc: datetime,
    ) -> CreacionTurno:
        if not _puede_gestionar_agenda(user):
            raise AgendaError(
                "RN-AU-04",
                "No tenés permiso para crear turnos.",
                403,
            )
        key = idempotency_key.strip()
        if not key or len(key) > 255:
            raise AgendaError(
                "RN-GL-02",
                "La clave idempotente debe tener entre 1 y 255 caracteres.",
                422,
            )
        ahora = _a_utc(ahora_utc, "ahora_utc")
        inicio = _a_utc(request.inicio, "inicio")
        fin = _a_utc(request.fin, "fin")
        if fin <= inicio:
            raise AgendaError("RN-GL-02", "El fin debe ser posterior al inicio.", 422)

        existente = self.repo.get_by_idempotency_key(user.tenant_id, key)
        if existente is not None:
            return CreacionTurno(
                _validar_reintento(existente, request, inicio, fin), False
            )

        profesional = self.repo.lock_profesional(
            user.tenant_id, request.profesional_id
        )
        if profesional is None:
            raise AgendaError("RN-AU-01", "Profesional no encontrado.", 404)

        # Recheck dentro del lock para que dos reintentos concurrentes no creen
        # turnos distintos para el mismo profesional.
        existente = self.repo.get_by_idempotency_key(user.tenant_id, key)
        if existente is not None:
            return CreacionTurno(
                _validar_reintento(existente, request, inicio, fin), False
            )

        paciente = self.pacientes.get_by_id(user.tenant_id, request.paciente_id)
        if paciente is None:
            raise AgendaError("RN-AU-01", "Paciente no encontrado.", 404)

        prestacion = None
        if request.prestacion_id is not None:
            prestacion = self.prestaciones.get_by_id(
                user.tenant_id, request.prestacion_id
            )
            if prestacion is None or not prestacion.activa:
                raise AgendaError("RN-AU-01", "Prestación no encontrada.", 404)
            if fin - inicio != timedelta(minutes=prestacion.duracion_min):
                raise AgendaError(
                    "RN-AG-03",
                    "La duración del turno no coincide con la prestación.",
                    422,
                )

        motivo_sobreturno = request.sobreturno_motivo
        if request.sobreturno:
            if not _motivo_sobreturno_valido(motivo_sobreturno):
                raise AgendaError(
                    "RN-AG-04",
                    "El motivo del sobreturno es obligatorio (1 a 500 caracteres).",
                    422,
                )
        elif motivo_sobreturno is not None:
            raise AgendaError(
                "RN-AG-04",
                "El motivo solo se admite para un sobreturno explícito.",
                422,
            )

        colisiones = self.repo.list_solapados(
            tenant_id=user.tenant_id,
            profesional_id=request.profesional_id,
            inicio=inicio,
            fin=fin,
        )
        if colisiones and not request.sobreturno:
            disponibles = self.disponibilidad(
                tenant_id=user.tenant_id,
                profesional_id=request.profesional_id,
                prestacion_id=request.prestacion_id,
                desde=max(ahora, inicio - timedelta(days=30)),
                hasta=inicio + timedelta(days=30),
                ahora_utc=ahora,
            )
            alternativas = sorted(
                {_a_utc(opcion, "alternativa") for opcion in disponibles},
                key=lambda opcion: (abs((opcion - inicio).total_seconds()), opcion),
            )[:3]
            raise ColisionTurnoError(alternativas)

        turno = TurnoModel(
            id=str(uuid.uuid4()),
            tenant_id=user.tenant_id,
            paciente_id=request.paciente_id,
            profesional_id=profesional.id,
            profesional_usuario_id=profesional.usuario_id,
            prestacion_id=request.prestacion_id,
            inicio=inicio,
            fin=fin,
            estado="confirmado",
            origen="mostrador",
            idempotency_key=key,
            sobreturno=bool(request.sobreturno),
            sobreturno_motivo=(
                motivo_sobreturno.strip()
                if request.sobreturno and motivo_sobreturno is not None
                else None
            ),
            sobreturno_autorizado_por=user.id if request.sobreturno else None,
        )
        try:
            creado = self.repo.create(turno)
        except IntegrityError:
            self.repo.session.rollback()
            existente = self.repo.get_by_idempotency_key(user.tenant_id, key)
            if existente is None:
                raise
            return CreacionTurno(
                _validar_reintento(existente, request, inicio, fin), False
            )
        return CreacionTurno(creado, True)

    def _obtener_para_mutar(
        self, tenant_id: str, turno_id: str, user: User
    ) -> TurnoModel:
        if tenant_id != user.tenant_id:
            raise AgendaError("RN-AU-01", "Turno no encontrado.", 404)
        if not _puede_gestionar_agenda(user):
            raise AgendaError(
                "RN-AU-04",
                "No tenés permiso para modificar la agenda.",
                403,
            )
        turno = self.repo.get_for_update(tenant_id, turno_id)
        if turno is None:
            raise AgendaError("RN-AU-01", "Turno no encontrado.", 404)
        return turno


def _puede_gestionar_agenda(user: User) -> bool:
    return bool({"recepcion", "dueno"} & set(user.roles or ()))


def _motivo_sobreturno_valido(motivo: str | None) -> bool:
    return motivo is not None and 1 <= len(motivo.strip()) <= 500


def _transicion_invalida() -> AgendaError:
    return AgendaError(
        "RN-AG-08",
        "El estado del turno no permite esta acción.",
        409,
    )


def _turno_no_encontrado() -> AgendaError:
    return AgendaError("RN-AU-01", "Turno no encontrado.", 404)


def _a_utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AgendaError(
            "RN-GL-02",
            f"El campo {field} debe incluir zona horaria.",
            422,
        )
    return value.astimezone(timezone.utc)


def _validar_reintento(
    existente: TurnoModel,
    request,
    inicio: datetime,
    fin: datetime,
) -> TurnoModel:
    coincide = (
        existente.paciente_id == request.paciente_id
        and existente.profesional_id == request.profesional_id
        and existente.prestacion_id == request.prestacion_id
        and existente.inicio.astimezone(timezone.utc) == inicio
        and existente.fin.astimezone(timezone.utc) == fin
        and existente.sobreturno == bool(request.sobreturno)
        and existente.sobreturno_motivo
        == (
            request.sobreturno_motivo.strip()
            if request.sobreturno and request.sobreturno_motivo is not None
            else None
        )
    )
    if not coincide:
        raise AgendaError(
            "RN-AG-03",
            "La clave idempotente ya se usó para otro turno.",
            409,
        )
    return existente


__all__ = ["ColisionTurnoError", "CreacionTurno", "TurnosService"]

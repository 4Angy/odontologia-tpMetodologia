"""Servicio de dominio: cancelación de turnos (slice cancelar-turno-liberar-horario).

Puro: sin HTTP ni DB. Decisiones de `design.md`:
- Orden inmutable: tenant → existe → permiso → ya-cancelado → terminales →
  pasado → antelación → motivo.
- `resolver_antelacion(tenant, prestacion?)`: UNA global, ignora prestacion.
- Idempotencia por estado; concurrencia vía lock por turno.
- Seña: no-touch; solo flag `senia_pendiente_definicion` si había seña.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)

ESTADOS_CANCELABLES = frozenset({"confirmado", "pendiente_confirmacion"})
ESTADOS_TERMINALES = frozenset({"presente", "ausente", "reprogramado"})
ESTADO_CANCELADO = "cancelado"

FALLBACK_ANTELACION_HS = 24
MOTIVO_MAX_LEN = 500


@dataclass
class Turno:
    """Entidad mínima de dominio para cancelación (no es el modelo SQLAlchemy)."""

    id: str
    tenant_id: str
    profesional_id: str
    profesional_usuario_id: Optional[str]
    prestacion_id: Optional[str]
    inicio: datetime
    fin: datetime
    estado: str
    cancelled_by: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    motivo: Optional[str] = None
    senia_pendiente_definicion: bool = False


@dataclass(frozen=True)
class User:
    id: str
    tenant_id: str
    roles: tuple = field(default_factory=tuple)


def turno_activo(turno: Turno) -> bool:
    """Un turno cuenta como activo (ocupa slot) solo si es cancelable."""
    return turno.estado in ESTADOS_CANCELABLES


def tiene_permiso_agenda(user: User, turno: Turno) -> bool:
    """RBAC por unión (RN-AU-04): dueno todo, recepcion agenda,
    odontologo solo sus turnos. `profesional_usuario_id` null → odontologo no matchea."""
    roles = set(user.roles or ())
    if "dueno" in roles:
        return True
    if "recepcion" in roles:
        return True
    if "odontologo" in roles:
        if turno.profesional_usuario_id is None:
            return False
        return turno.profesional_usuario_id == user.id
    return False


def resolver_antelacion(
    get_config_hs: Callable[[str], Optional[int]],
    tenant_id: str,
    prestacion: Optional[str] = None,  # noqa: ARG001 - extensible sin cambio de contrato (PA-04)
) -> int:
    """UNA antelación global por tenant; hoy ignora `prestacion`.
    Config ausente → fallback 24h + log."""
    valor = get_config_hs(tenant_id)
    if valor is None:
        logger.warning(
            "config ausente para tenant %s: usando fallback de %sh",
            tenant_id, FALLBACK_ANTELACION_HS,
        )
        return FALLBACK_ANTELACION_HS
    return valor


class AgendaError(Exception):
    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class TurnoNotFoundError(AgendaError):
    def __init__(self) -> None:
        super().__init__(
            code="RN-AU-01",
            message="Turno no encontrado.",
            status=404,
        )


class ForbiddenError(AgendaError):
    def __init__(self, message: str = "No tenés permiso para cancelar este turno.") -> None:
        super().__init__(code="RN-AU-04", message=message, status=403)


class TerminalStateError(AgendaError):
    def __init__(self, estado: str) -> None:
        super().__init__(
            code="RN-AG-08",
            message=f"El turno está '{estado}' y ya no se puede cancelar.",
            status=409,
        )


class TurnoPasadoError(AgendaError):
    def __init__(self) -> None:
        super().__init__(
            code="RN-AG-09",
            message="El turno ya pasó y no se puede cancelar.",
            status=409,
        )


class FueraDeTerminoError(AgendaError):
    def __init__(self, antelacion_hs: int) -> None:
        super().__init__(
            code="RN-AG-01",
            message=(
                f"No se puede cancelar con menos de {antelacion_hs} h de antelación. "
                "Podés reprogramar el turno en otro horario disponible."
            ),
            status=409,
        )
        # Placeholder documentado: reprogramar es C-07.
        self.action = {
            "type": "reprogramar",
            "hint": (
                "La reprogramación automática aún no está disponible; "
                "coordiná manualmente un nuevo horario con el paciente."
            ),
        }


class MotivoInvalidoError(AgendaError):
    def __init__(self) -> None:
        super().__init__(
            code="RN-GL-02",
            message="El motivo es obligatorio (1 a 500 caracteres).",
            status=422,
        )


def _motivo_valido(motivo: Optional[str]) -> bool:
    return (
        motivo is not None
        and motivo.strip() != ""
        and 1 <= len(motivo.strip()) <= MOTIVO_MAX_LEN
    )


class AgendaCancelService:
    """Cancela turnos con el orden de validación inmutable del design."""

    def __init__(self) -> None:
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _lock_para(self, turno_id: str) -> threading.Lock:
        with self._locks_guard:
            lock = self._locks.get(turno_id)
            if lock is None:
                lock = threading.Lock()
                self._locks[turno_id] = lock
            return lock

    def cancel(
        self,
        *,
        tenant_id: str,
        turno: Optional[Turno],
        user: User,
        motivo: Optional[str],
        now_utc: datetime,
        antelacion_hs: int,
        tiene_senia: bool = False,
    ) -> Turno:
        # 1-2. tenant → existe (indistinguible: cross-tenant == inexistente).
        if turno is None or turno.tenant_id != tenant_id:
            raise TurnoNotFoundError()
        # 3. permiso (unión de roles RN-AU-04).
        if not tiene_permiso_agenda(user, turno):
            if "odontologo" in set(user.roles or ()) and turno.profesional_usuario_id is None:
                raise ForbiddenError(
                    "El profesional del turno no tiene usuario vinculado."
                )
            raise ForbiddenError()
        # Transición bajo lock por turno (condición de carrera → idempotencia).
        with self._lock_para(turno.id):
            # 4. ya cancelado → 200 idempotente, conserva primera auditoría.
            if turno.estado == ESTADO_CANCELADO:
                return turno
            # 5. terminales (`reprogramado` = turno viejo migrado, no cancelable).
            if turno.estado in ESTADOS_TERMINALES or turno.estado not in ESTADOS_CANCELABLES:
                raise TerminalStateError(turno.estado)
            # 5b. turno pasado.
            if turno.inicio < now_utc:
                raise TurnoPasadoError()
            # 6. antelación (UTC aware, límite inclusivo; 0 = hasta minuto cero).
            restante_hs = (turno.inicio - now_utc).total_seconds() / 3600.0
            if restante_hs < antelacion_hs:
                raise FueraDeTerminoError(antelacion_hs)
            # 7. motivo último (422; fuera-de-término precede a motivo).
            if not _motivo_valido(motivo):
                raise MotivoInvalidoError()
            # Transición + auditoría mínima (RN-GL-02) + flag de seña (no-touch).
            turno.estado = ESTADO_CANCELADO
            turno.cancelled_by = user.id
            turno.cancelled_at = now_utc
            turno.motivo = motivo.strip()  # type: ignore[union-attr]
            turno.senia_pendiente_definicion = bool(tiene_senia)
            return turno

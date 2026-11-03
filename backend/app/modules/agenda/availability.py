"""Cálculo reutilizable de candidatos para agenda y reserva pública."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.modules.agenda.models import (
    BloqueoModel,
    ConfigModel,
    HorarioProfesionalModel,
    PrestacionModel,
    ProfesionalModel,
    TenantModel,
    TurnoModel,
)
from app.modules.agenda.service import ESTADOS_CANCELABLES


@dataclass(frozen=True)
class HorarioSemanal:
    dia_semana: int
    inicio: time
    fin: time


@dataclass(frozen=True)
class IntervaloTiempo:
    inicio: datetime
    fin: datetime


def _require_aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} debe incluir zona horaria.")
    return value.astimezone(timezone.utc)


def _utc_desde_horario_local(
    horario_local: datetime,
    zona: ZoneInfo,
) -> datetime | None:
    aware = horario_local.replace(tzinfo=zona, fold=0)
    utc = aware.astimezone(timezone.utc)
    if utc.astimezone(zona).replace(tzinfo=None) != horario_local:
        return None
    return utc


def calcular_disponibilidad(
    *,
    horarios: list[HorarioSemanal],
    bloqueos: list[IntervaloTiempo],
    turnos_activos: list[IntervaloTiempo],
    desde: datetime,
    hasta: datetime,
    duracion_min: int,
    antelacion_reserva_hs: int,
    ahora_utc: datetime,
    zona_horaria: str,
) -> list[datetime]:
    """Devuelve inicios UTC a intervalos de 30 minutos, con duración completa."""
    desde_utc = _require_aware(desde, "desde")
    hasta_utc = _require_aware(hasta, "hasta")
    ahora = _require_aware(ahora_utc, "ahora_utc")
    if hasta_utc <= desde_utc:
        raise ValueError("La ventana de disponibilidad debe tener fin posterior al inicio.")
    if isinstance(duracion_min, bool) or not isinstance(duracion_min, int) or duracion_min <= 0:
        raise ValueError("La duración debe ser un entero positivo.")
    if (
        isinstance(antelacion_reserva_hs, bool)
        or not isinstance(antelacion_reserva_hs, int)
        or antelacion_reserva_hs < 0
    ):
        raise ValueError("La antelación de reserva debe ser un entero no negativo.")
    try:
        zona = ZoneInfo(zona_horaria)
    except ZoneInfoNotFoundError as error:
        raise ValueError("La zona horaria del tenant no es válida.") from error

    bloqueos_utc = [
        (_require_aware(item.inicio, "bloqueo.inicio"), _require_aware(item.fin, "bloqueo.fin"))
        for item in bloqueos
    ]
    turnos_utc = [
        (_require_aware(item.inicio, "turno.inicio"), _require_aware(item.fin, "turno.fin"))
        for item in turnos_activos
    ]
    limite_antelacion = ahora + timedelta(hours=antelacion_reserva_hs)
    duracion = timedelta(minutes=duracion_min)
    primera_fecha = desde_utc.astimezone(zona).date()
    ultima_fecha = hasta_utc.astimezone(zona).date()
    candidatos: set[datetime] = set()

    for dia in _fechas_inclusive(primera_fecha, ultima_fecha):
        for horario in horarios:
            if not 0 <= horario.dia_semana <= 6:
                raise ValueError("El día de semana debe estar entre 0 y 6.")
            if horario.dia_semana != dia.weekday():
                continue
            if (
                horario.inicio.tzinfo is not None
                or horario.fin.tzinfo is not None
                or horario.fin <= horario.inicio
            ):
                raise ValueError("El intervalo semanal local no es válido.")

            cierre_local = datetime.combine(dia, horario.fin)
            inicio_local = datetime.combine(dia, horario.inicio)
            candidato_local = inicio_local
            while candidato_local + duracion <= cierre_local:
                fin_local = candidato_local + duracion
                candidato_utc = _utc_desde_horario_local(candidato_local, zona)
                fin_utc = _utc_desde_horario_local(fin_local, zona)
                if (
                    candidato_utc is not None
                    and fin_utc is not None
                    and candidato_utc >= limite_antelacion
                    and candidato_utc >= desde_utc
                    and candidato_utc < hasta_utc
                    and fin_utc <= hasta_utc
                    and fin_utc > candidato_utc
                    and fin_utc - candidato_utc == duracion
                    and not _se_superpone(candidato_utc, fin_utc, bloqueos_utc)
                    and not _se_superpone(candidato_utc, fin_utc, turnos_utc)
                ):
                    candidatos.add(candidato_utc)
                candidato_local += timedelta(minutes=30)

    return sorted(candidatos)


def _fechas_inclusive(desde: date, hasta: date):
    dia = desde
    while dia <= hasta:
        yield dia
        dia += timedelta(days=1)


def _se_superpone(
    inicio: datetime,
    fin: datetime,
    intervalos: list[tuple[datetime, datetime]],
) -> bool:
    return any(inicio < fin_ocupado and fin > inicio_ocupado for inicio_ocupado, fin_ocupado in intervalos)


def candidatos_disponibles(
    session: Session,
    *,
    tenant_id: str,
    profesional_id: str,
    prestacion_id: str,
    desde: datetime,
    hasta: datetime,
    ahora_utc: datetime,
) -> list[datetime]:
    """Consulta datos tenant-scoped y calcula disponibilidad sin crear otro endpoint."""
    profesional = session.execute(
        select(ProfesionalModel).where(
            ProfesionalModel.tenant_id == tenant_id,
            ProfesionalModel.id == profesional_id,
            ProfesionalModel.activo.is_(True),
        )
    ).scalar_one_or_none()
    prestacion = session.execute(
        select(PrestacionModel).where(
            PrestacionModel.tenant_id == tenant_id,
            PrestacionModel.id == prestacion_id,
            PrestacionModel.activa.is_(True),
        )
    ).scalar_one_or_none()
    tenant = session.get(TenantModel, tenant_id)
    if profesional is None or prestacion is None or tenant is None:
        raise LookupError("Profesional o prestación no disponible.")

    desde_utc = _require_aware(desde, "desde")
    hasta_utc = _require_aware(hasta, "hasta")
    horarios = session.execute(
        select(HorarioProfesionalModel).where(
            HorarioProfesionalModel.tenant_id == tenant_id,
            HorarioProfesionalModel.profesional_id == profesional_id,
        )
    ).scalars().all()
    bloqueos = session.execute(
        select(BloqueoModel).where(
            and_(
                BloqueoModel.tenant_id == tenant_id,
                BloqueoModel.profesional_id == profesional_id,
                BloqueoModel.inicio < hasta_utc,
                BloqueoModel.fin > desde_utc,
            )
        )
    ).scalars().all()
    turnos = session.execute(
        select(TurnoModel).where(
            and_(
                TurnoModel.tenant_id == tenant_id,
                TurnoModel.profesional_id == profesional_id,
                TurnoModel.estado.in_(ESTADOS_CANCELABLES),
                TurnoModel.inicio < hasta_utc,
                TurnoModel.fin > desde_utc,
            )
        )
    ).scalars().all()
    config = session.get(ConfigModel, tenant_id)

    return calcular_disponibilidad(
        horarios=[
            HorarioSemanal(
                dia_semana=item.dia_semana,
                inicio=item.hora_inicio,
                fin=item.hora_fin,
            )
            for item in horarios
        ],
        bloqueos=[
            IntervaloTiempo(inicio=item.inicio, fin=item.fin) for item in bloqueos
        ],
        turnos_activos=[
            IntervaloTiempo(inicio=item.inicio, fin=item.fin) for item in turnos
        ],
        desde=desde_utc,
        hasta=hasta_utc,
        duracion_min=prestacion.duracion_min,
        antelacion_reserva_hs=config.antelacion_reserva_hs if config else 2,
        ahora_utc=ahora_utc,
        zona_horaria=tenant.tz,
    )


__all__ = [
    "HorarioSemanal",
    "IntervaloTiempo",
    "calcular_disponibilidad",
    "candidatos_disponibles",
]

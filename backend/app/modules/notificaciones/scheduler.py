"""Scheduler de recordatorios (C-09).

Encola envíos. El lock del tick se resuelve en `lock.py` y el sender los toma.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.agenda.models import TenantModel, TurnoModel
from app.modules.agenda.repository import ConfigRepository
from app.modules.pacientes.models import OptInModel, PacienteModel
from app.modules.notificaciones.models import NotificacionEnvioModel
from app.modules.notificaciones.repository import (
    NotificacionEnvioRepository,
    PlantillaRepository,
)
from app.modules.notificaciones.windows import (
    TICK_INTERVAL,
    Ventana,
    calcular_ventanas,
    ventana_debida,
)


ESTADOS_ACTIVOS = ("confirmado", "pendiente_confirmacion")


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def canal_para_paciente(session: Session, tenant_id: str, paciente_id: str) -> str | None:
    """Devuelve 'whatsapp' si hay opt-in vigente + teléfono E.164, 'email' si hay email, None si ninguno."""
    paciente = session.get(PacienteModel, paciente_id)
    if paciente is None or paciente.tenant_id != tenant_id:
        return None
    # tenant check via paciente
    if paciente.telefono:
        optin = session.execute(
            select(OptInModel).where(
                OptInModel.tenant_id == tenant_id,
                OptInModel.paciente_id == paciente_id,
                OptInModel.canal == "whatsapp",
            )
        ).scalar_one_or_none()
        if optin is not None and bool(optin.estado):
            return "whatsapp"
    if paciente.email:
        return "email"
    return None


class SchedulerService:
    def __init__(
        self,
        session: Session,
        *,
        enabled: bool,
        now: datetime,
        redis_client: object | None = None,
    ) -> None:
        self.session = session
        self.enabled = enabled
        self.now = _utc(now)
        self.redis_client = redis_client
        self.repo = NotificacionEnvioRepository(session)
        self.plantillas = PlantillaRepository(session)

    def ejecutar(self) -> list[NotificacionEnvioModel]:
        if not self.enabled:
            return []
        encolados: list[NotificacionEnvioModel] = []
        tenants = list(self.session.execute(select(TenantModel)).scalars().all())
        for tenant in tenants:
            config = ConfigRepository(self.session).get(tenant.id)
            encolados.extend(self.procesar_tenant(tenant.id, config, self.now))
        self.session.flush()
        return encolados

    def procesar_tenant(
        self, tenant_id: str, config, now: datetime
    ) -> list[NotificacionEnvioModel]:
        # turnos activos futuros cuyo envío cae en el intervalo.
        limite_inferior = now - timedelta(hours=72)
        stmt = select(TurnoModel).where(
            TurnoModel.tenant_id == tenant_id,
            TurnoModel.estado.in_(ESTADOS_ACTIVOS),
            TurnoModel.inicio > now,
        )
        turnos = list(self.session.execute(stmt).scalars().all())
        encolados: list[NotificacionEnvioModel] = []
        for turno in turnos:
            for ventana in calcular_ventanas(turno.inicio, config):
                if not ventana_debida(ventana, now):
                    continue
                canal = canal_para_paciente(
                    self.session, tenant_id, turno.paciente_id
                )
                if canal is None:
                    envio = self._crear_envio(
                        tenant_id=tenant_id,
                        turno=turno,
                        canal="whatsapp",
                        ventana=ventana,
                        estado="omitida",
                        motivo_code="RN-PA-01",
                        next_attempt_at=ventana.enviar_at,
                        plantilla_codigo="recordatorio",
                    )
                    if envio is not None:
                        encolados.append(envio)
                    continue
                # plantilla activa obligatoria (D15)
                plantilla = self.plantillas.get_activa(
                    tenant_id, "recordatorio", canal
                )
                if plantilla is None:
                    envio = self._crear_envio(
                        tenant_id=tenant_id,
                        turno=turno,
                        canal=canal,
                        ventana=ventana,
                        estado="omitida",
                        motivo_code="plantilla_inactiva",
                        next_attempt_at=ventana.enviar_at,
                        plantilla_codigo="recordatorio",
                    )
                    if envio is not None:
                        encolados.append(envio)
                    continue
                envio = self._crear_envio(
                    tenant_id=tenant_id,
                    turno=turno,
                    canal=canal,
                    ventana=ventana,
                    estado="encolada",
                    motivo_code=None,
                    next_attempt_at=ventana.enviar_at,
                    plantilla_codigo=plantilla.codigo,
                )
                if envio is not None:
                    encolados.append(envio)
        return encolados

    def _crear_envio(
        self,
        *,
        tenant_id: str,
        turno: TurnoModel,
        canal: str,
        ventana: Ventana,
        estado: str,
        motivo_code: str | None,
        next_attempt_at: datetime,
        plantilla_codigo: str,
    ) -> NotificacionEnvioModel | None:
        envio = NotificacionEnvioModel(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            paciente_id=turno.paciente_id,
            turno_id=turno.id,
            canal=canal,
            plantilla_codigo=plantilla_codigo,
            ventana=ventana.codigo,
            estado=estado,
            motivo_code=motivo_code,
            intentos=0,
            next_attempt_at=_utc(next_attempt_at),
            costo_estimado_centavos=0,
        )
        insertado = self.repo.insertar_si_no_existe(envio)
        if not insertado:
            return None
        return envio


__all__ = ["SchedulerService", "canal_para_paciente"]

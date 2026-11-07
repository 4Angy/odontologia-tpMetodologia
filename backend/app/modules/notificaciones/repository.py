"""Repositorios tenant-scoped del motor de notificaciones (R1)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

def _utc_now():
    return datetime.now(timezone.utc)

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.modules.agenda.models import ConfigModel
from app.modules.agenda.repository import ConfigRepository
from app.modules.notificaciones.models import (
    NotificacionEnvioModel,
    PlantillaModel,
)


class PlantillaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, tenant_id: str) -> list[PlantillaModel]:
        stmt = (
            select(PlantillaModel)
            .where(PlantillaModel.tenant_id == tenant_id)
            .order_by(PlantillaModel.codigo, PlantillaModel.canal)
        )
        return list(self.session.execute(stmt).scalars().all())

    def get(
        self, tenant_id: str, codigo: str, canal: str, idioma: str = "es-AR"
    ) -> Optional[PlantillaModel]:
        stmt = select(PlantillaModel).where(
            PlantillaModel.tenant_id == tenant_id,
            PlantillaModel.codigo == codigo,
            PlantillaModel.canal == canal,
            PlantillaModel.idioma == idioma,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_activa(
        self, tenant_id: str, codigo: str, canal: str, idioma: str = "es-AR"
    ) -> Optional[PlantillaModel]:
        plantilla = self.get(tenant_id, codigo, canal, idioma)
        if plantilla is None or not plantilla.activa:
            return None
        return plantilla

    def upsert(self, plantilla: PlantillaModel) -> PlantillaModel:
        self.session.add(plantilla)
        self.session.flush()
        return plantilla

    def seed_tenant(self, tenant_id: str) -> list[PlantillaModel]:
        """Siembra las cinco plantillas `es-AR` inactivas. Idempotente."""
        creadas: list[PlantillaModel] = []
        cuerpos = {
            ("recordatorio", "whatsapp"): "Hola {{paciente}}, te recordamos tu turno el {{fecha}}. Confirmá: {{link}}",
            ("recordatorio", "email"): "Hola {{paciente}}, te recordamos tu turno el {{fecha}}. Confirmá: {{link}}",
            ("confirmacion", "whatsapp"): "Hola {{paciente}}, tu turno del {{fecha}} está confirmado. {{link}}",
            ("confirmacion", "email"): "Hola {{paciente}}, tu turno del {{fecha}} está confirmado. {{link}}",
            ("cancelacion", "whatsapp"): "Hola {{paciente}}, tu turno del {{fecha}} fue cancelado.",
            ("cancelacion", "email"): "Hola {{paciente}}, tu turno del {{fecha}} fue cancelado.",
            ("lista_espera", "whatsapp"): "Hola {{paciente}}, hay un hueco disponible el {{fecha}}. {{link}}",
            ("lista_espera", "email"): "Hola {{paciente}}, hay un hueco disponible el {{fecha}}. {{link}}",
            ("senia", "whatsapp"): "Hola {{paciente}}, recordá la seña de tu turno del {{fecha}}. {{link}}",
            ("senia", "email"): "Hola {{paciente}}, recordá la seña de tu turno del {{fecha}}. {{link}}",
        }
        for codigo in (
            "recordatorio",
            "confirmacion",
            "cancelacion",
            "lista_espera",
            "senia",
        ):
            for canal in ("whatsapp", "email"):
                existente = self.get(tenant_id, codigo, canal)
                if existente is not None:
                    continue
                plantilla = PlantillaModel(
                    tenant_id=tenant_id,
                    codigo=codigo,
                    canal=canal,
                    idioma="es-AR",
                    cuerpo=cuerpos[(codigo, canal)],
                    activa=False,
                    asunto="Recordatorio" if canal == "email" else None,
                )
                self.session.add(plantilla)
                creadas.append(plantilla)
        self.session.flush()
        return creadas


class NotificacionEnvioRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, tenant_id: str, envio_id: str) -> Optional[NotificacionEnvioModel]:
        stmt = select(NotificacionEnvioModel).where(
            NotificacionEnvioModel.tenant_id == tenant_id,
            NotificacionEnvioModel.id == envio_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_for_tenant(
        self,
        tenant_id: str,
        *,
        estado: str | None = None,
        turno_id: str | None = None,
        limit: int = 200,
    ) -> list[NotificacionEnvioModel]:
        stmt = select(NotificacionEnvioModel).where(
            NotificacionEnvioModel.tenant_id == tenant_id
        )
        if estado is not None:
            stmt = stmt.where(NotificacionEnvioModel.estado == estado)
        if turno_id is not None:
            stmt = stmt.where(NotificacionEnvioModel.turno_id == turno_id)
        stmt = stmt.order_by(
            NotificacionEnvioModel.created_at.desc(), NotificacionEnvioModel.id.desc()
        ).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def buscar_por_provider_msg_id(
        self, provider_msg_id: str
    ) -> list[NotificacionEnvioModel]:
        # Excepción controlada (webhook): el proveedor no envía tenant, así que
        # la búsqueda se hace por el id externo, que es único por tenant.
        stmt = select(NotificacionEnvioModel).where(
            NotificacionEnvioModel.provider_msg_id == provider_msg_id
        )
        return list(self.session.execute(stmt).scalars().all())

    def insertar_si_no_existe(self, envio: NotificacionEnvioModel) -> bool:
        """Inserta con ON CONFLICT DO NOTHING. Devuelve True si insertó."""
        created_at = envio.created_at or _utc_now()
        updated_at = envio.updated_at or _utc_now()
        envio.created_at = created_at
        envio.updated_at = updated_at
        dialect = self.session.bind.dialect.name if self.session.bind is not None else ""
        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            stmt = (
                pg_insert(NotificacionEnvioModel)
                .values(
                    id=envio.id,
                    tenant_id=envio.tenant_id,
                    paciente_id=envio.paciente_id,
                    turno_id=envio.turno_id,
                    canal=envio.canal,
                    plantilla_codigo=envio.plantilla_codigo,
                    ventana=envio.ventana,
                    estado=envio.estado,
                    motivo_code=envio.motivo_code,
                    intentos=envio.intentos,
                    next_attempt_at=envio.next_attempt_at,
                    provider_msg_id=envio.provider_msg_id,
                    costo_estimado_centavos=envio.costo_estimado_centavos,
                    ultimo_error_code=envio.ultimo_error_code,
                    enviado_at=envio.enviado_at,
                    entregado_at=envio.entregado_at,
                    created_at=created_at,
                    updated_at=updated_at,
                )
                .on_conflict_do_nothing(
                    index_elements=["tenant_id", "turno_id", "ventana", "canal"]
                )
            )
        elif dialect == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert

            stmt = (
                sqlite_insert(NotificacionEnvioModel)
                .values(
                    id=envio.id,
                    tenant_id=envio.tenant_id,
                    paciente_id=envio.paciente_id,
                    turno_id=envio.turno_id,
                    canal=envio.canal,
                    plantilla_codigo=envio.plantilla_codigo,
                    ventana=envio.ventana,
                    estado=envio.estado,
                    motivo_code=envio.motivo_code,
                    intentos=envio.intentos,
                    next_attempt_at=envio.next_attempt_at,
                    provider_msg_id=envio.provider_msg_id,
                    costo_estimado_centavos=envio.costo_estimado_centavos,
                    ultimo_error_code=envio.ultimo_error_code,
                    enviado_at=envio.enviado_at,
                    entregado_at=envio.entregado_at,
                    created_at=created_at,
                    updated_at=updated_at,
                )
                .on_conflict_do_nothing(
                    index_elements=["tenant_id", "turno_id", "ventana", "canal"]
                )
            )
        else:
            # Motor desconocido: fallback conservador.
            self.session.add(envio)
            try:
                self.session.flush()
            except Exception:  # noqa: BLE001
                self.session.rollback()
                return False
            return True
        result = self.session.execute(stmt)
        self.session.flush()
        existe = self.session.get(NotificacionEnvioModel, envio.id) is not None
        return existe

    def reclamar_vencidos(
        self, tenant_id: str | None, now: datetime, limit: int
    ) -> list[NotificacionEnvioModel]:
        stmt = select(NotificacionEnvioModel).where(
            NotificacionEnvioModel.estado == "encolada",
            NotificacionEnvioModel.next_attempt_at <= now,
        )
        if tenant_id is not None:
            stmt = stmt.where(NotificacionEnvioModel.tenant_id == tenant_id)
        stmt = (
            stmt.order_by(NotificacionEnvioModel.next_attempt_at, NotificacionEnvioModel.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(self.session.execute(stmt).scalars().all())

    def consumo(
        self, tenant_id: str, desde: datetime, hasta: datetime
    ) -> list[dict]:
        stmt = (
            select(
                NotificacionEnvioModel.canal,
                NotificacionEnvioModel.estado,
                func.count().label("cantidad"),
                func.coalesce(func.sum(NotificacionEnvioModel.costo_estimado_centavos), 0).label("costo"),
            )
            .where(
                NotificacionEnvioModel.tenant_id == tenant_id,
                NotificacionEnvioModel.created_at >= desde,
                NotificacionEnvioModel.created_at < hasta,
            )
            .group_by(
                NotificacionEnvioModel.canal, NotificacionEnvioModel.estado
            )
            .order_by(NotificacionEnvioModel.canal, NotificacionEnvioModel.estado)
        )
        filas = self.session.execute(stmt).all()
        return [
            {
                "canal": f[0],
                "estado": f[1],
                "cantidad": int(f[2]),
                "costo_centavos": int(f[3]),
            }
            for f in filas
        ]


__all__ = ["NotificacionEnvioRepository", "PlantillaRepository"]

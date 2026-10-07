"""Repositorios: TODA query de negocio filtra por `tenant_id` (R1).

`get_for_update` usa SELECT … FOR UPDATE en PostgreSQL (no-op en SQLite);
el servicio además serializa por lock, y la transición es condicional por
estado (el segundo concurrente cae en idempotencia).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.agenda.models import ConfigModel, TurnoModel
from app.modules.agenda.service import ESTADOS_CANCELABLES


class TurnoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, tenant_id: str, turno_id: str) -> Optional[TurnoModel]:
        """R1: filtra por tenant; cross-tenant → None (404 indistinguible)."""
        stmt = select(TurnoModel).where(
            and_(TurnoModel.id == turno_id, TurnoModel.tenant_id == tenant_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_for_update(self, tenant_id: str, turno_id: str) -> Optional[TurnoModel]:
        stmt = (
            select(TurnoModel)
            .where(and_(TurnoModel.id == turno_id, TurnoModel.tenant_id == tenant_id))
            .with_for_update()
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_activos(
        self, tenant_id: str, profesional_id: str, desde: datetime, hasta: datetime
    ) -> list[TurnoModel]:
        """Slot libre = observable: cancelados/terminales ya no aparecen."""
        stmt = (
            select(TurnoModel)
            .where(
                and_(
                    TurnoModel.tenant_id == tenant_id,
                    TurnoModel.profesional_id == profesional_id,
                    TurnoModel.inicio >= desde,
                    TurnoModel.inicio < hasta,
                    TurnoModel.estado.in_(ESTADOS_CANCELABLES),
                )
            )
            .order_by(TurnoModel.inicio)
        )
        return list(self.session.execute(stmt).scalars().all())


class ConfigRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_hs(self, tenant_id: str) -> Optional[int]:
        cfg = self.session.get(ConfigModel, tenant_id)
        return cfg.antelacion_cancel_hs if cfg is not None else None

    def upsert(self, tenant_id: str, antelacion_cancel_hs: int) -> ConfigModel:
        if antelacion_cancel_hs < 0:
            raise IntegrityError(
                "antelacion_cancel_hs >= 0", params=None, orig=ValueError("negativo")
            )
        cfg = self.session.get(ConfigModel, tenant_id)
        if cfg is None:
            cfg = ConfigModel(
                tenant_id=tenant_id, antelacion_cancel_hs=antelacion_cancel_hs
            )
            self.session.add(cfg)
        else:
            cfg.antelacion_cancel_hs = antelacion_cancel_hs
        self.session.flush()
        return cfg

"""Repositorio tenant-scoped de lista de espera (R1)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.modules.lista_espera.models import ListaEsperaModel


class ListaEsperaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self, tenant_id: str, *, estado: str | None = None
    ) -> list[ListaEsperaModel]:
        stmt = select(ListaEsperaModel).where(ListaEsperaModel.tenant_id == tenant_id)
        if estado is not None:
            stmt = stmt.where(ListaEsperaModel.estado == estado)
        stmt = stmt.order_by(ListaEsperaModel.prioridad, ListaEsperaModel.created_at, ListaEsperaModel.id)
        return list(self.session.execute(stmt).scalars().all())

    def get_by_id(self, tenant_id: str, entry_id: str) -> Optional[ListaEsperaModel]:
        stmt = select(ListaEsperaModel).where(
            ListaEsperaModel.tenant_id == tenant_id,
            ListaEsperaModel.id == entry_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, entry: ListaEsperaModel) -> ListaEsperaModel:
        self.session.add(entry)
        self.session.flush()
        return entry

    def update(self, entry: ListaEsperaModel) -> ListaEsperaModel:
        self.session.flush()
        return entry

    def list_activas_compatibles(
        self, tenant_id: str, profesional_id: str, prestacion_id: str | None
    ) -> list[ListaEsperaModel]:
        stmt = select(ListaEsperaModel).where(
            ListaEsperaModel.tenant_id == tenant_id,
            ListaEsperaModel.estado == "activa",
        )
        # compatibilidad: profesional null o igual; prestacion null o igual
        # Se filtra en Python para manejar nulls correctamente.
        entries = list(self.session.execute(stmt).scalars().all())
        compatibles = []
        for e in entries:
            if e.profesional_id is not None and e.profesional_id != profesional_id:
                continue
            if e.prestacion_id is not None and e.prestacion_id != prestacion_id:
                continue
            compatibles.append(e)
        compatibles.sort(key=lambda e: (e.prioridad, e.created_at, e.id))
        return compatibles

    def list_ofrecidas_vencidas(
        self, now: datetime, tenant_id: str | None = None
    ) -> list[ListaEsperaModel]:
        stmt = select(ListaEsperaModel).where(
            ListaEsperaModel.estado == "ofrecida",
            ListaEsperaModel.expires_at.is_not(None),
            ListaEsperaModel.expires_at <= now,
        )
        if tenant_id is not None:
            stmt = stmt.where(ListaEsperaModel.tenant_id == tenant_id)
        stmt = stmt.order_by(ListaEsperaModel.expires_at, ListaEsperaModel.id)
        return list(self.session.execute(stmt).scalars().all())


__all__ = ["ListaEsperaRepository"]

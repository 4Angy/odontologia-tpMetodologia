from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cobros.models import CierreCajaModel, CobroModel


class CobroRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, cobro: CobroModel) -> CobroModel:
        self.session.add(cobro)
        self.session.flush()
        return cobro

    def get(self, tenant_id: str, cobro_id: str) -> CobroModel | None:
        return self.session.execute(
            select(CobroModel).where(
                CobroModel.tenant_id == tenant_id,
                CobroModel.id == cobro_id,
                CobroModel.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def list(
        self,
        tenant_id: str,
        *,
        paciente_id: str | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[CobroModel]:
        statement = select(CobroModel).where(
            CobroModel.tenant_id == tenant_id,
            CobroModel.deleted_at.is_(None),
        )
        if paciente_id is not None:
            statement = statement.where(CobroModel.paciente_id == paciente_id)
        if fecha_desde is not None:
            statement = statement.where(CobroModel.fecha >= fecha_desde)
        if fecha_hasta is not None:
            statement = statement.where(CobroModel.fecha < fecha_hasta)
        statement = statement.order_by(CobroModel.fecha.desc(), CobroModel.id.desc())
        return list(self.session.execute(statement).scalars())

    def delete(self, cobro: CobroModel) -> None:
        self.session.delete(cobro)


class CierreCajaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_fecha(self, tenant_id: str, fecha: datetime) -> CierreCajaModel | None:
        # Compara por día UTC: truncamos a fecha.
        inicio = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
        fin = inicio.replace(day=inicio.day + 1) if False else None
        from datetime import timedelta

        fin = inicio + timedelta(days=1)
        return self.session.execute(
            select(CierreCajaModel).where(
                CierreCajaModel.tenant_id == tenant_id,
                CierreCajaModel.fecha >= inicio,
                CierreCajaModel.fecha < fin,
                CierreCajaModel.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def create(self, cierre: CierreCajaModel) -> CierreCajaModel:
        self.session.add(cierre)
        self.session.flush()
        return cierre

    def list_recent(self, tenant_id: str, limit: int = 20) -> list[CierreCajaModel]:
        statement = (
            select(CierreCajaModel)
            .where(
                CierreCajaModel.tenant_id == tenant_id,
                CierreCajaModel.deleted_at.is_(None),
            )
            .order_by(CierreCajaModel.fecha.desc())
            .limit(limit)
        )
        return list(self.session.execute(statement).scalars())
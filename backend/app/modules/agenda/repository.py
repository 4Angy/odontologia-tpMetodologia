"""Repositorios: TODA query de negocio filtra por `tenant_id` (R1).

`get_for_update` usa SELECT … FOR UPDATE en PostgreSQL (no-op en SQLite);
el servicio además serializa por lock, y la transición es condicional por
estado (el segundo concurrente cae en idempotencia).
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.agenda.models import (
    BloqueoModel,
    ConfigModel,
    PublicTokenModel,
    PrestacionModel,
    ProfesionalModel,
    TurnoModel,
)
from app.modules.agenda.service import ESTADOS_CANCELABLES


class ProfesionalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, tenant_id: str) -> list[ProfesionalModel]:
        stmt = select(ProfesionalModel).where(ProfesionalModel.tenant_id == tenant_id).order_by(ProfesionalModel.nombre)
        return list(self.session.execute(stmt).scalars().all())

    def get_by_id(self, tenant_id: str, profesional_id: str) -> Optional[ProfesionalModel]:
        stmt = select(ProfesionalModel).where(
            ProfesionalModel.tenant_id == tenant_id,
            ProfesionalModel.id == profesional_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, profesional: ProfesionalModel) -> ProfesionalModel:
        self.session.add(profesional)
        self.session.flush()
        return profesional

    def update(self, profesional: ProfesionalModel) -> ProfesionalModel:
        self.session.flush()
        return profesional

    def delete(self, profesional: ProfesionalModel) -> None:
        self.session.delete(profesional)
        self.session.flush()


class PrestacionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, tenant_id: str) -> list[PrestacionModel]:
        stmt = select(PrestacionModel).where(PrestacionModel.tenant_id == tenant_id).order_by(PrestacionModel.nombre)
        return list(self.session.execute(stmt).scalars().all())

    def get_by_id(self, tenant_id: str, prestacion_id: str) -> Optional[PrestacionModel]:
        stmt = select(PrestacionModel).where(
            PrestacionModel.tenant_id == tenant_id,
            PrestacionModel.id == prestacion_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, prestacion: PrestacionModel) -> PrestacionModel:
        self.session.add(prestacion)
        self.session.flush()
        return prestacion

    def update(self, prestacion: PrestacionModel) -> PrestacionModel:
        self.session.flush()
        return prestacion

    def delete(self, prestacion: PrestacionModel) -> None:
        self.session.delete(prestacion)
        self.session.flush()


class BloqueoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, tenant_id: str) -> list[BloqueoModel]:
        stmt = select(BloqueoModel).where(BloqueoModel.tenant_id == tenant_id).order_by(BloqueoModel.inicio)
        return list(self.session.execute(stmt).scalars().all())

    def get_by_id(self, tenant_id: str, bloqueo_id: str) -> Optional[BloqueoModel]:
        stmt = select(BloqueoModel).where(
            BloqueoModel.tenant_id == tenant_id,
            BloqueoModel.id == bloqueo_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, bloqueo: BloqueoModel) -> BloqueoModel:
        self.session.add(bloqueo)
        self.session.flush()
        return bloqueo

    def update(self, bloqueo: BloqueoModel) -> BloqueoModel:
        self.session.flush()
        return bloqueo

    def delete(self, bloqueo: BloqueoModel) -> None:
        self.session.delete(bloqueo)
        self.session.flush()


class TurnoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def lock_profesional(
        self,
        tenant_id: str,
        profesional_id: str,
        *,
        require_active: bool = True,
    ) -> Optional[ProfesionalModel]:
        """Serializa escrituras de agenda por profesional dentro de su tenant."""
        stmt = select(ProfesionalModel).where(
            ProfesionalModel.tenant_id == tenant_id,
            ProfesionalModel.id == profesional_id,
        )
        if require_active:
            stmt = stmt.where(ProfesionalModel.activo.is_(True))
        stmt = stmt.with_for_update()
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_id(self, tenant_id: str, turno_id: str) -> Optional[TurnoModel]:
        """R1: filtra por tenant; cross-tenant → None (404 indistinguible)."""
        stmt = select(TurnoModel).where(
            and_(TurnoModel.id == turno_id, TurnoModel.tenant_id == tenant_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_idempotency_key(
        self, tenant_id: str, idempotency_key: str
    ) -> Optional[TurnoModel]:
        stmt = select(TurnoModel).where(
            TurnoModel.tenant_id == tenant_id,
            TurnoModel.idempotency_key == idempotency_key,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_for_update(self, tenant_id: str, turno_id: str) -> Optional[TurnoModel]:
        stmt = (
            select(TurnoModel)
            .where(and_(TurnoModel.id == turno_id, TurnoModel.tenant_id == tenant_id))
            .with_for_update()
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_for_agenda(
        self,
        *,
        tenant_id: str,
        desde: datetime,
        hasta: datetime,
        profesional_id: str | None = None,
        profesional_usuario_id: str | None = None,
    ) -> list[TurnoModel]:
        stmt = select(TurnoModel).where(
            TurnoModel.tenant_id == tenant_id,
            TurnoModel.inicio < hasta,
            TurnoModel.fin > desde,
        )
        if profesional_id is not None:
            stmt = stmt.where(TurnoModel.profesional_id == profesional_id)
        if profesional_usuario_id is not None:
            stmt = stmt.where(
                TurnoModel.profesional_usuario_id == profesional_usuario_id
            )
        stmt = stmt.order_by(TurnoModel.inicio, TurnoModel.id)
        return list(self.session.execute(stmt).scalars().all())


    def list_solapados(
        self,
        *,
        tenant_id: str,
        profesional_id: str,
        inicio: datetime,
        fin: datetime,
        excluir_turno_id: str | None = None,
    ) -> list[TurnoModel]:
        stmt = select(TurnoModel).where(
            TurnoModel.tenant_id == tenant_id,
            TurnoModel.profesional_id == profesional_id,
            TurnoModel.estado.in_(ESTADOS_CANCELABLES),
            TurnoModel.inicio < fin,
            TurnoModel.fin > inicio,
        )
        if excluir_turno_id is not None:
            stmt = stmt.where(TurnoModel.id != excluir_turno_id)
        stmt = stmt.order_by(TurnoModel.inicio, TurnoModel.id)
        return list(self.session.execute(stmt).scalars().all())

    def create(self, turno: TurnoModel) -> TurnoModel:
        self.session.add(turno)
        self.session.flush()
        return turno

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
                    TurnoModel.inicio < hasta,
                    TurnoModel.fin > desde,
                    TurnoModel.estado.in_(ESTADOS_CANCELABLES),
                )
            )
            .order_by(TurnoModel.inicio)
        )
        return list(self.session.execute(stmt).scalars().all())


class PublicTokenRepository:
    """Acceso tenant-scoped a tokens públicos sin aceptar tokens crudos."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_valid(
        self,
        *,
        tenant_id: str,
        raw_token: str,
        purpose: str,
        now: datetime,
    ) -> Optional[PublicTokenModel]:
        stmt = select(PublicTokenModel).where(
            PublicTokenModel.tenant_id == tenant_id,
            PublicTokenModel.token_hash == hashlib.sha256(
                raw_token.encode("utf-8")
            ).hexdigest(),
            PublicTokenModel.purpose == purpose,
            PublicTokenModel.revoked_at.is_(None),
            PublicTokenModel.expires_at > now,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_raw(
        self, *, tenant_id: str, raw_token: str, purpose: str
    ) -> Optional[PublicTokenModel]:
        stmt = select(PublicTokenModel).where(
            PublicTokenModel.tenant_id == tenant_id,
            PublicTokenModel.token_hash == hashlib.sha256(
                raw_token.encode("utf-8")
            ).hexdigest(),
            PublicTokenModel.purpose == purpose,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_for_turno(self, tenant_id: str, turno_id: str) -> list[PublicTokenModel]:
        stmt = select(PublicTokenModel).where(
            PublicTokenModel.tenant_id == tenant_id,
            PublicTokenModel.turno_id == turno_id,
        )
        return list(self.session.execute(stmt).scalars().all())

    def revoke_for_turno(
        self,
        *,
        tenant_id: str,
        turno_id: str,
        revoked_at: datetime,
        reason: str,
    ) -> int:
        tokens = self.list_for_turno(tenant_id, turno_id)
        changed = 0
        for token in tokens:
            if token.revoked_at is None:
                token.revoked_at = revoked_at
                token.revocation_reason = reason
                changed += 1
        self.session.flush()
        return changed


class ConfigRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, tenant_id: str) -> Optional[ConfigModel]:
        return self.session.get(ConfigModel, tenant_id)

    def get_hs(self, tenant_id: str) -> Optional[int]:
        cfg = self.get(tenant_id)
        return cfg.antelacion_cancel_hs if cfg is not None else None

    def upsert(
        self,
        tenant_id: str,
        antelacion_cancel_hs: int,
        antelacion_reserva_hs: int = 2,
        recordatorio_t_48h: bool | None = None,
        recordatorio_t_24h: bool | None = None,
        recordatorio_1_hs: int | None = None,
        recordatorio_2_hs: int | None = None,
        whatsapp_costo_centavos: int | None = None,
        lista_espera_ttl_hs: int | None = None,
        politica_devolucion_senia: str | None = None,
    ) -> ConfigModel:
        if antelacion_cancel_hs < 0:
            raise IntegrityError(
                "antelacion_cancel_hs >= 0", params=None, orig=ValueError("negativo")
            )
        if antelacion_reserva_hs < 0:
            raise IntegrityError(
                "antelacion_reserva_hs >= 0", params=None, orig=ValueError("negativo")
            )
        cfg = self.get(tenant_id)
        if cfg is None:
            cfg = ConfigModel(
                tenant_id=tenant_id,
                antelacion_cancel_hs=antelacion_cancel_hs,
                antelacion_reserva_hs=antelacion_reserva_hs,
            )
            if recordatorio_t_48h is not None:
                cfg.recordatorio_t_48h = recordatorio_t_48h
            if recordatorio_t_24h is not None:
                cfg.recordatorio_t_24h = recordatorio_t_24h
            if recordatorio_1_hs is not None:
                cfg.recordatorio_1_hs = recordatorio_1_hs
            if recordatorio_2_hs is not None:
                cfg.recordatorio_2_hs = recordatorio_2_hs
            if whatsapp_costo_centavos is not None:
                cfg.whatsapp_costo_centavos = whatsapp_costo_centavos
            if lista_espera_ttl_hs is not None:
                cfg.lista_espera_ttl_hs = lista_espera_ttl_hs
            if politica_devolucion_senia is not None:
                cfg.politica_devolucion_senia = politica_devolucion_senia
            self.session.add(cfg)
        else:
            cfg.antelacion_cancel_hs = antelacion_cancel_hs
            cfg.antelacion_reserva_hs = antelacion_reserva_hs
            if recordatorio_t_48h is not None:
                cfg.recordatorio_t_48h = recordatorio_t_48h
            if recordatorio_t_24h is not None:
                cfg.recordatorio_t_24h = recordatorio_t_24h
            if recordatorio_1_hs is not None:
                cfg.recordatorio_1_hs = recordatorio_1_hs
            if recordatorio_2_hs is not None:
                cfg.recordatorio_2_hs = recordatorio_2_hs
            if whatsapp_costo_centavos is not None:
                cfg.whatsapp_costo_centavos = whatsapp_costo_centavos
            if lista_espera_ttl_hs is not None:
                cfg.lista_espera_ttl_hs = lista_espera_ttl_hs
            if politica_devolucion_senia is not None:
                cfg.politica_devolucion_senia = politica_devolucion_senia
        self.session.flush()
        return cfg

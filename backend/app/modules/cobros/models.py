"""Modelos del módulo de cobros y caja (C-11)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.agenda.models import AuditMixin, AwareDateTime, TenantMixin

MEDIOS_PAGO = ("efectivo", "transferencia", "mp", "otro")

ESTADOS_SENIA = ("pendiente", "acreditada", "devuelta", "aplicada")


class CobroModel(TenantMixin, AuditMixin, Base):
    __tablename__ = "cobro"
    __table_args__ = (
        Index("ix_cobro_tenant_fecha", "tenant_id", "fecha"),
        Index("ix_cobro_tenant_paciente", "tenant_id", "paciente_id"),
        CheckConstraint("monto_cents >= 0", name="ck_cobro_monto_no_negativo"),
        CheckConstraint(
            "medio IN ('efectivo', 'transferencia', 'mp', 'otro')",
            name="ck_cobro_medio",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    paciente_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("paciente.id"), nullable=False, index=True
    )
    turno_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    monto_cents: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    medio: Mapped[str] = mapped_column(String(20), nullable=False)
    concepto: Mapped[str] = mapped_column(String(200), nullable=False)
    usuario_id: Mapped[str] = mapped_column(String(64), nullable=False)
    fecha: Mapped[datetime] = mapped_column(AwareDateTime(), nullable=False)


class SeniaModel(TenantMixin, AuditMixin, Base):
    """Seña de Mercado Pago por reserva pública (C-12).

    Estado: `pendiente` → `acreditada` (webhook MP) → `aplicada` (saldo a favor
    del paciente, arrastra al reprogramar o al cancelar en término) /
    `devuelta` (se pierde total o parcialmente según política RN-CO-03).
    """

    __tablename__ = "senia"
    __table_args__ = (
        Index("ix_senia_tenant_paciente", "tenant_id", "paciente_id"),
        Index("ix_senia_tenant_turno", "tenant_id", "turno_id"),
        UniqueConstraint("mp_preference_id", name="ux_senia_mp_preference_id"),
        UniqueConstraint("mp_payment_id", name="ux_senia_mp_payment_id"),
        CheckConstraint("monto_cents > 0", name="ck_senia_monto_positivo"),
        CheckConstraint(
            "estado IN ('pendiente', 'acreditada', 'devuelta', 'aplicada')",
            name="ck_senia_estado",
        ),
        CheckConstraint(
            "monto_afavor_cents IS NULL OR monto_afavor_cents <= monto_cents",
            name="ck_senia_afavor_no_supera_monto",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    turno_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    paciente_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("paciente.id"), nullable=False, index=True
    )
    monto_cents: Mapped[int] = mapped_column(Integer(), nullable=False)
    #: Crédito efectivo que resta del saldo derivado (NULL = monto completo).
    monto_afavor_cents: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    mp_preference_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mp_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    #: Fecha de acreditación (webhook) en UTC aware (R7).
    acreditada_at: Mapped[datetime | None] = mapped_column(
        AwareDateTime(), nullable=True
    )


class CierreCajaModel(TenantMixin, AuditMixin, Base):
    __tablename__ = "cierre_caja"
    __table_args__ = (
        UniqueConstraint("tenant_id", "fecha", name="ux_cierre_tenant_fecha"),
        Index("ix_cierre_tenant_fecha", "tenant_id", "fecha"),
        CheckConstraint("total_efectivo_cents >= 0", name="ck_cierre_efectivo_no_negativo"),
        CheckConstraint("total_transferencia_cents >= 0", name="ck_cierre_transferencia_no_negativo"),
        CheckConstraint("total_mp_cents >= 0", name="ck_cierre_mp_no_negativo"),
        CheckConstraint("total_otro_cents >= 0", name="ck_cierre_otro_no_negativo"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    fecha: Mapped[datetime] = mapped_column(AwareDateTime(), nullable=False)
    total_efectivo_cents: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    total_transferencia_cents: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    total_mp_cents: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    total_otro_cents: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    observaciones: Mapped[str | None] = mapped_column(Text(), nullable=True)
    usuario_id: Mapped[str] = mapped_column(String(64), nullable=False)


__all__ = ["CierreCajaModel", "CobroModel", "ESTADOS_SENIA", "MEDIOS_PAGO", "SeniaModel"]
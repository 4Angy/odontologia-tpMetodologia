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


__all__ = ["CierreCajaModel", "CobroModel", "MEDIOS_PAGO"]
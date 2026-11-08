"""Modelos del modulo lista de espera (C-10)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    TIMESTAMP,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.agenda.models import AuditMixin, AwareDateTime, TenantMixin


ESTADOS_LISTA_ESPERA = ("activa", "ofrecida", "convertida", "vencida")


class ListaEsperaModel(TenantMixin, AuditMixin, Base):
    __tablename__ = "lista_espera"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('activa', 'ofrecida', 'convertida', 'vencida')",
            name="ck_lista_espera_estado",
        ),
        Index("ix_lista_espera_tenant_estado_prioridad", "tenant_id", "estado", "prioridad"),
        Index("ix_lista_espera_tenant_estado_expires", "tenant_id", "estado", "expires_at"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    paciente_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("paciente.id"), nullable=False, index=True
    )
    profesional_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prestacion_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prioridad: Mapped[int] = mapped_column(Integer(), nullable=False, default=0, server_default="0")
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="activa", server_default="activa"
    )
    motivo_omision: Mapped[str | None] = mapped_column(String(40), nullable=True)
    hueco_profesional_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hueco_inicio: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)
    hueco_fin: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)
    hueco_prestacion_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ofrecido_at: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)


__all__ = ["ESTADOS_LISTA_ESPERA", "ListaEsperaModel"]

"""Modelos SQLAlchemy mínimos (seed de C-06/C-07).

Nota de extensión: C-06/C-07 agregan columnas/tablas SIN re-migrar lo creado
aquí. `tenant` es mínimo (solo PK para el FK de `turno`); C-02 lo extiende.
Dinero: no hay montos en este slice (R5 N/A). Datetimes UTC aware (R7).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    pass


class AwareDateTime(TypeDecorator):
    """Timestamptz portable: exige aware al guardar (R7); al leer SQLite
    (que devuelve naive) re-ancla a UTC en vez de perder la zona horaria."""

    impl = TIMESTAMP(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: ANN001, ANN202
        if value is not None and value.tzinfo is None:
            raise ValueError("datetime naive prohibido (R7): usar UTC aware")
        return value

    def process_result_value(self, value, dialect):  # noqa: ANN001, ANN202
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class TenantModel(Base):
    """Tenant mínimo: solo existe como destino del FK de turno. C-02 lo extiende."""

    __tablename__ = "tenant"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False, default="demo")


class TurnoModel(Base):
    __tablename__ = "turno"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenant.id"), nullable=False, index=True
    )
    paciente_id: Mapped[str] = mapped_column(String(64), nullable=False)
    profesional_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    profesional_usuario_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prestacion_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    inicio: Mapped[datetime] = mapped_column(AwareDateTime(), nullable=False)
    fin: Mapped[datetime] = mapped_column(AwareDateTime(), nullable=False)
    estado: Mapped[str] = mapped_column(String(32), nullable=False, default="confirmado")
    cancelled_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text(), nullable=True)
    senia_pendiente_definicion: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, default=False, server_default="false"
    )


class ConfigModel(Base):
    __tablename__ = "config"

    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenant.id"), primary_key=True
    )
    antelacion_cancel_hs: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=24, server_default="24"
    )

    __table_args__ = (
        CheckConstraint("antelacion_cancel_hs >= 0", name="ck_config_antelacion_ge_0"),
    )


# Re-export para compatibilidad con SQLite (DateTime sin tz real).
__all__ = ["Base", "TenantModel", "TurnoModel", "ConfigModel", "AwareDateTime"]

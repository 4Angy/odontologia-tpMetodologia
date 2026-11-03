from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.modules.agenda.models import AuditMixin, AwareDateTime, TenantMixin


class PacienteModel(TenantMixin, AuditMixin, Base):
    __tablename__ = "paciente"
    __table_args__ = (
        UniqueConstraint("tenant_id", "dni", name="ux_paciente_tenant_dni"),
        UniqueConstraint("tenant_id", "telefono", name="ux_paciente_tenant_telefono"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    dni: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fecha_nac: Mapped[str | None] = mapped_column(AwareDateTime(), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text(), nullable=True)
    saldo: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)

    optins: Mapped[list["OptInModel"]] = relationship(
        back_populates="paciente",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    evoluciones: Mapped[list["EvolucionModel"]] = relationship(
        back_populates="paciente",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    adjuntos: Mapped[list["AdjuntoModel"]] = relationship(
        back_populates="paciente",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    presupuestos: Mapped[list["PresupuestoModel"]] = relationship(
        back_populates="paciente",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OptInModel(TenantMixin, Base):
    __tablename__ = "optin"
    __table_args__ = (
        UniqueConstraint("tenant_id", "paciente_id", "canal", name="ux_optin_tenant_paciente_canal"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    paciente_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("paciente.id"), nullable=False, index=True
    )
    canal: Mapped[str] = mapped_column(String(20), nullable=False, default="whatsapp")
    estado: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    updated_at: Mapped[str] = mapped_column(AwareDateTime(), nullable=False)

    paciente: Mapped[PacienteModel] = relationship(back_populates="optins")


class EvolucionModel(TenantMixin, AuditMixin, Base):
    __tablename__ = "evolucion"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    paciente_id: Mapped[str] = mapped_column(String(64), ForeignKey("paciente.id"), nullable=False, index=True)
    odontologo_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    motivo: Mapped[str] = mapped_column(String(200), nullable=False)
    detalle: Mapped[str] = mapped_column(Text(), nullable=False)
    firma_simple: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    firma_timestamp: Mapped[str | None] = mapped_column(AwareDateTime(), nullable=True)

    paciente: Mapped[PacienteModel] = relationship(back_populates="evoluciones")


class AdjuntoModel(TenantMixin, AuditMixin, Base):
    __tablename__ = "adjunto"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    paciente_id: Mapped[str] = mapped_column(String(64), ForeignKey("paciente.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(100), nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    paciente: Mapped[PacienteModel] = relationship(back_populates="adjuntos")


class PresupuestoModel(TenantMixin, AuditMixin, Base):
    __tablename__ = "presupuesto"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    paciente_id: Mapped[str] = mapped_column(String(64), ForeignKey("paciente.id"), nullable=False, index=True)
    total_cents: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    estado: Mapped[str] = mapped_column(String(32), nullable=False, default="activo")
    notas: Mapped[str | None] = mapped_column(Text(), nullable=True)

    paciente: Mapped[PacienteModel] = relationship(back_populates="presupuestos")
    items: Mapped[list["PresupuestoItemModel"]] = relationship(
        back_populates="presupuesto",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PresupuestoItemModel(TenantMixin, AuditMixin, Base):
    __tablename__ = "presupuesto_item"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    presupuesto_id: Mapped[str] = mapped_column(String(64), ForeignKey("presupuesto.id"), nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)
    monto_cents: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)

    presupuesto: Mapped[PresupuestoModel] = relationship(back_populates="items")

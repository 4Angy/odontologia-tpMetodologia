"""Modelos SQLAlchemy del sistema multi-tenant.

Este módulo es la fuente de verdad del esquema de la base del monolito y
mantiene compatibilidad con los slices previos (`tenant`, `turno`, `config`).
"""
from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import datetime, time, timezone
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    SmallInteger,
    Text,
    TIMESTAMP,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy.types import TypeDecorator

from app.core.db import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_slug(value: str | None) -> str:
    """Normaliza un slug a kebab-case y valida el formato del dominio."""
    if value is None:
        raise ValueError("El slug no puede ser nulo.")
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError(
            "El slug debe ser kebab-case: solo minúsculas, números y guiones, sin espacios ni mayúsculas."
        )
    return slug


class AwareDateTime(TypeDecorator):
    """Timestamptz portable: exige aware al guardar y re-ancla a UTC cuando lee SQLite."""

    impl = TIMESTAMP(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: ANN001, ANN202
        if value is not None and value.tzinfo is None:
            raise ValueError("datetime naive prohibido (R7): usar UTC aware")
        return value

    def process_result_value(self, value, dialect):  # noqa: ANN001, ANN202
        if value is None:
            return None
        if getattr(value, "tzinfo", None) is None:
            return value.replace(tzinfo=timezone.utc)
        # Postgres devuelve timestamptz en la zona horaria del servidor. La API
        # debe serializar siempre UTC (R7), independientemente de esa config.
        return value.astimezone(timezone.utc)


class UsuarioRoles(str, Enum):
    RECEPCION = "recepcion"
    ODONTOLOGO = "odontologo"
    DUENO = "dueno"


class EnumArrayType(TypeDecorator):
    """TypeDecorator compatible con un ARRAY de enum en Postgres y con texto en SQLite."""

    impl = Text
    cache_ok = True

    def __init__(self, enum_cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_cls = enum_cls

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        valores = []
        for item in value:
            if isinstance(item, Enum):
                valores.append(item.value)
            else:
                valores.append(str(item))
        # La columna es Text: se normaliza SIEMPRE a lista separada por comas,
        # para que el driver no la serialize como literal de array PG ({a,b}).
        return ",".join(valores)

    def process_result_value(self, value, dialect):
        if value in (None, ""):
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        texto = str(value).strip()
        if texto.startswith("{") and texto.endswith("}"):
            texto = texto[1:-1]  # literal de array PG que quedó guardado en Text
        return [item.strip() for item in texto.split(",") if item.strip()]


class TenantMixin:
    """Todo modelo de negocio filtra datos por tenant_id. El mixin lo hace explícito."""

    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenant.id"), nullable=False, index=True
    )


class AuditMixin:
    """Auditoría mínima en toda mutación del dominio."""

    created_at: Mapped[datetime] = mapped_column(
        AwareDateTime(), nullable=False, default=_utc_now, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        AwareDateTime(), nullable=False, default=_utc_now, onupdate=_utc_now, server_default=text("CURRENT_TIMESTAMP")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)


class TenantModel(Base):
    """Tenant. El slug es global y kebab-case; se normaliza antes de persistir."""

    __tablename__ = "tenant"
    __table_args__ = (UniqueConstraint("slug", name="ux_tenant_slug"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False, default="demo")
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    email_contacto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tz: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="America/Argentina/Buenos_Aires",
        server_default="America/Argentina/Buenos_Aires",
    )
    created_at: Mapped[datetime] = mapped_column(
        AwareDateTime(), nullable=False, default=_utc_now, server_default=text("CURRENT_TIMESTAMP")
    )

    def __init__(self, **kwargs):
        if "slug" not in kwargs:
            base = kwargs.get("slug") or kwargs.get("nombre") or kwargs.get("id") or "tenant"
            kwargs["slug"] = normalize_slug(str(base))
        super().__init__(**kwargs)

    @validates("slug")
    def _validate_slug(self, key, value):
        return normalize_slug(value)


class UsuarioModel(TenantMixin, AuditMixin, Base):
    __tablename__ = "usuario"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="ux_usuario_tenant_email"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenant.id"), nullable=False, index=True
    )
    nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="true")
    roles: Mapped[list[str]] = mapped_column(
        EnumArrayType(UsuarioRoles),
        nullable=False,
        default=list,
        server_default="{}",
    )


class ProfesionalModel(TenantMixin, AuditMixin, Base):
    __tablename__ = "profesional"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    color_agenda: Mapped[str | None] = mapped_column(String(16), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="true")


class PrestacionModel(TenantMixin, AuditMixin, Base):
    __tablename__ = "prestacion"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    duracion_min: Mapped[int] = mapped_column(Integer(), nullable=False, default=30)
    precio_ref: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="true")


class BloqueoModel(TenantMixin, AuditMixin, Base):
    __tablename__ = "bloqueo"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    profesional_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    inicio: Mapped[datetime] = mapped_column(AwareDateTime(), nullable=False)
    fin: Mapped[datetime] = mapped_column(AwareDateTime(), nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text(), nullable=True)


class HorarioProfesionalModel(TenantMixin, AuditMixin, Base):
    __tablename__ = "horario_profesional"
    __table_args__ = (
        CheckConstraint(
            "dia_semana >= 0 AND dia_semana <= 6",
            name="ck_horario_profesional_dia_semana",
        ),
        CheckConstraint(
            "hora_fin > hora_inicio",
            name="ck_horario_profesional_rango",
        ),
        UniqueConstraint(
            "tenant_id",
            "profesional_id",
            "dia_semana",
            "hora_inicio",
            name="ux_horario_profesional_inicio",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    profesional_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dia_semana: Mapped[int] = mapped_column(SmallInteger(), nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time(), nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time(), nullable=False)


class TurnoModel(Base):
    __tablename__ = "turno"
    __table_args__ = (
        Index(
            "ix_turno_tenant_profesional_inicio",
            "tenant_id",
            "profesional_id",
            "inicio",
        ),
        Index("ix_turno_tenant_inicio", "tenant_id", "inicio"),
        Index("ux_turno_token_publico", "token_publico", unique=True),
        Index(
            "ux_turno_tenant_idempotency_key",
            "tenant_id",
            "idempotency_key",
            unique=True,
        ),
    )

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
    token_publico: Mapped[str | None] = mapped_column(String(128), nullable=True)
    origen: Mapped[str] = mapped_column(
        String(32), nullable=False, default="mostrador", server_default="mostrador"
    )
    senia_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sobreturno: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, default=False, server_default="false"
    )
    sobreturno_motivo: Mapped[str | None] = mapped_column(Text(), nullable=True)
    sobreturno_autorizado_por: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )


class ConfigModel(Base):
    __tablename__ = "config"

    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenant.id"), primary_key=True
    )
    antelacion_cancel_hs: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=24, server_default="24"
    )
    antelacion_reserva_hs: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=2, server_default="2"
    )
    senia_requerida: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, default=False, server_default="false"
    )
    recordatorio_t_48h: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, default=True, server_default="true"
    )
    recordatorio_t_24h: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, default=True, server_default="true"
    )

    __table_args__ = (
        CheckConstraint("antelacion_cancel_hs >= 0", name="ck_config_antelacion_ge_0"),
        CheckConstraint("antelacion_reserva_hs >= 0", name="ck_config_reserva_antelacion_ge_0"),
    )


__all__ = [
    "AuditMixin",
    "AwareDateTime",
    "Base",
    "BloqueoModel",
    "ConfigModel",
    "EnumArrayType",
    "HorarioProfesionalModel",
    "PrestacionModel",
    "ProfesionalModel",
    "TenantMixin",
    "TenantModel",
    "TurnoModel",
    "UsuarioModel",
    "UsuarioRoles",
    "normalize_slug",
]

"""Modelos del motor de notificaciones (C-09).

La cola durable es la tabla `notificacion_envio` (D2): el scheduler inserta la
intención y el sender la reclama con `FOR UPDATE SKIP LOCKED`. Redis solo
coordina el tick, nunca guarda estado de negocio.

Reglas duras que estos modelos materializan:
- R1: toda fila cuelga de `tenant_id` y los repositorios filtran por él.
- R5: el costo es un entero en centavos, jamás `float`.
- R7: los instantes son `AwareDateTime` (UTC aware).
- R8: `provider_msg_id` es único por tenant para la idempotencia del webhook.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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

#: Canales soportados por el motor.
CANALES = ("whatsapp", "email")

#: Estados de la máquina monotónica de D8.
ESTADOS_ENVIO = (
    "encolada",
    "enviada",
    "entregada",
    "fallida",
    "omitida",
    "cancelada",
)

#: Ventanas configurables por tenant (D10).
VENTANAS = ("t-48h", "t-24h")

#: Códigos de plantilla sembrados (D15).
CODIGOS_PLANTILLA = (
    "recordatorio",
    "confirmacion",
    "cancelacion",
    "lista_espera",
    "senia",
)


class PlantillaModel(TenantMixin, AuditMixin, Base):
    """Plantilla por tenant, canal e idioma. Nace inactiva (D15)."""

    __tablename__ = "plantilla"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "codigo",
            "canal",
            "idioma",
            name="ux_plantilla_tenant_codigo_canal_idioma",
        ),
        CheckConstraint(
            "canal IN ('whatsapp', 'email')",
            name="ck_plantilla_canal",
        ),
        CheckConstraint(
            "codigo IN ('recordatorio', 'confirmacion', 'cancelacion', 'lista_espera', 'senia')",
            name="ck_plantilla_codigo",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    codigo: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    canal: Mapped[str] = mapped_column(String(20), nullable=False)
    idioma: Mapped[str] = mapped_column(
        String(10), nullable=False, default="es-AR", server_default="es-AR"
    )
    asunto: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cuerpo: Mapped[str] = mapped_column(Text(), nullable=False)
    activa: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, default=False, server_default="false"
    )


class NotificacionEnvioModel(TenantMixin, AuditMixin, Base):
    """Intención de envío durable. Es la cola y también la evidencia auditable."""

    __tablename__ = "notificacion_envio"
    __table_args__ = (
        # Anti-spam de RN-PA-03 e idempotencia del scheduler (D4).
        UniqueConstraint(
            "tenant_id",
            "turno_id",
            "ventana",
            "canal",
            name="ux_notif_tenant_turno_ventana_canal",
        ),
        # Idempotencia del webhook (R8). Índice parcial: el nulo no colisiona.
        Index(
            "ux_notif_tenant_provider_msg",
            "tenant_id",
            "provider_msg_id",
            unique=True,
            postgresql_where=text("provider_msg_id IS NOT NULL"),
            sqlite_where=text("provider_msg_id IS NOT NULL"),
        ),
        # Reclamación del sender.
        Index("ix_notif_tenant_estado_next", "tenant_id", "estado", "next_attempt_at"),
        # Panel de consumo (D12).
        Index("ix_notif_tenant_created", "tenant_id", "created_at"),
        CheckConstraint(
            "canal IN ('whatsapp', 'email')", name="ck_notif_canal"
        ),
        CheckConstraint(
            "estado IN ('encolada', 'enviada', 'entregada', 'fallida', 'omitida', 'cancelada')",
            name="ck_notif_estado",
        ),
        CheckConstraint(
            "costo_estimado_centavos >= 0", name="ck_notif_costo_no_negativo"
        ),
        CheckConstraint("intentos >= 0", name="ck_notif_intentos_no_negativos"),
        CheckConstraint(
            "ventana IS NULL OR ventana IN ('t-48h', 't-24h')",
            name="ck_notif_ventana",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    paciente_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("paciente.id"), nullable=False, index=True
    )
    turno_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    canal: Mapped[str] = mapped_column(String(20), nullable=False)
    plantilla_codigo: Mapped[str] = mapped_column(String(60), nullable=False)
    ventana: Mapped[str | None] = mapped_column(String(10), nullable=True)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="encolada", server_default="encolada"
    )
    motivo_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    intentos: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=0, server_default="0"
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        AwareDateTime(), nullable=False
    )
    provider_msg_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    costo_estimado_centavos: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=0, server_default="0"
    )
    ultimo_error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    enviado_at: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)
    entregado_at: Mapped[datetime | None] = mapped_column(
        AwareDateTime(), nullable=True
    )


__all__ = [
    "CANALES",
    "CODIGOS_PLANTILLA",
    "ESTADOS_ENVIO",
    "NotificacionEnvioModel",
    "PlantillaModel",
    "VENTANAS",
]

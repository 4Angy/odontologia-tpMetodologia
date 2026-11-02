"""Modelo SQLAlchemy de tokens de sesión (task 1.1).

Una sola tabla `auth_token` guarda el estado de las familias de refresh
(proposito='refresh') y los tokens de reset (proposito='reset') — design
`c-03-auth-rbac-multirole`, decisión 1 (estado duradero en Postgres).
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.agenda.models import AwareDateTime, AuditMixin, TenantMixin


class PropositoToken(str, enum.Enum):
    """Propósito de un token registrado en `auth_token`."""

    REFRESH = "refresh"
    RESET = "reset"


class AuthTokenModel(TenantMixin, AuditMixin, Base):
    """Fila de estado de un token (jti).

    PK global por `id` (= jti): el token de sesión es único en todo el
    sistema, no por (tenant, jti).
    """

    __tablename__ = "auth_token"
    __table_args__ = (
        CheckConstraint(
            "proposito IN ('refresh','reset')", name="ck_auth_token_proposito"
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("usuario.id"), nullable=False, index=True
    )
    familia_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    proposito: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PropositoToken.REFRESH.value
    )
    revoked: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    used_at: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)
    expira: Mapped[datetime] = mapped_column(AwareDateTime(), nullable=False)

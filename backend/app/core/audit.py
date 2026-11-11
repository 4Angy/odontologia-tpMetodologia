from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, JSON, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base
from app.modules.agenda.models import AwareDateTime


class AuditEventModel(Base):
    __tablename__ = "audit_event"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenant.id"), nullable=False, index=True
    )
    actor_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("usuario.id"), nullable=False, index=True
    )
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    recurso: Mapped[str] = mapped_column(String(80), nullable=False)
    recurso_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    campos: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    consentimiento_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    rol_activo: Mapped[str | None] = mapped_column(String(32), nullable=True)
    invalidated_destination_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ocurrido_at: Mapped[datetime] = mapped_column(
        AwareDateTime(), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )


def registrar_auditoria(
    session: Session,
    *,
    tenant_id: str,
    actor_id: str,
    accion: str,
    recurso: str,
    recurso_id: str,
    campos: list[str],
    consentimiento_version: str | None = None,
    invalidated_destination_hash: str | None = None,
    rol_activo: str | None = None,
) -> AuditEventModel:
    if rol_activo is None and actor_id:
        try:
            from app.modules.agenda.models import UsuarioModel

            usuario = session.get(UsuarioModel, actor_id)
            if usuario is not None and getattr(usuario, "roles", None):
                roles = usuario.roles
                if isinstance(roles, (list, tuple)) and roles:
                    rol_activo = roles[0]
        except Exception:  # noqa: BLE001 - auditoría no debe fallar por lookup de rol
            rol_activo = None
    event = AuditEventModel(
        tenant_id=tenant_id,
        actor_id=actor_id,
        accion=accion,
        recurso=recurso,
        recurso_id=recurso_id,
        campos=sorted(set(campos)),
        consentimiento_version=consentimiento_version,
        invalidated_destination_hash=invalidated_destination_hash,
        rol_activo=rol_activo,
        ocurrido_at=datetime.now(timezone.utc),
    )
    session.add(event)
    return event


def listar_auditoria(session: Session, tenant_id: str, limit: int) -> list[AuditEventModel]:
    statement = (
        select(AuditEventModel)
        .where(AuditEventModel.tenant_id == tenant_id)
        .order_by(AuditEventModel.ocurrido_at.desc(), AuditEventModel.id.desc())
        .limit(limit)
    )
    return list(session.execute(statement).scalars().all())


__all__ = ["AuditEventModel", "listar_auditoria", "registrar_auditoria"]

"""Router de auditoría a nivel de app (C-13).

Expone `/auditoria` para el dueño del tenant, sin acoplamiento a un módulo
de dominio. Reutiliza `listar_auditoria` de `app.core.audit`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import deps
from app.core.audit import listar_auditoria
from app.core.security import require_roles
from app.modules.pacientes.schemas import AuditoriaResponse

audit_router = APIRouter(tags=["auditoria"])


@audit_router.get("/auditoria", response_model=list[AuditoriaResponse])
def consultar_auditoria(
    limit: int = Query(default=50, ge=1, le=100),
    user=Depends(require_roles("dueno")),
    session: Session = Depends(deps.get_session),
):
    return listar_auditoria(session, user.tenant_id, limit)
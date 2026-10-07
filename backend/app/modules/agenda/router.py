"""Router del slice: POST /turnos/:id/cancelar + GET/PUT /config.

Adaptador HTTP fino: el router resuelve tenant del JWT (R2), valida DTOs y
mapea errores de dominio a `{code, message, action?}` (R9, RN-GL-01).
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import AuthUser, require_auth, require_roles
from app import deps
from app.modules.agenda import service as domain
from app.modules.agenda.models import TurnoModel
from app.modules.agenda.repository import ConfigRepository, TurnoRepository
from app.modules.agenda.schemas import (
    CancelarTurnoRequest,
    ConfigResponse,
    ConfigUpdateRequest,
    TurnoResponse,
)

router = APIRouter()


def _now_utc() -> datetime:  # referencia (la app usa deps.get_now inyectable)
    return datetime.now(timezone.utc)


def _a_dominio(t: TurnoModel) -> domain.Turno:
    return domain.Turno(
        id=t.id,
        tenant_id=t.tenant_id,
        profesional_id=t.profesional_id,
        profesional_usuario_id=t.profesional_usuario_id,
        prestacion_id=t.prestacion_id,
        inicio=t.inicio,
        fin=t.fin,
        estado=t.estado,
        cancelled_by=t.cancelled_by,
        cancelled_at=t.cancelled_at,
        motivo=t.motivo,
        senia_pendiente_definicion=t.senia_pendiente_definicion,
    )


def _a_respuesta(t: domain.Turno) -> TurnoResponse:
    return TurnoResponse(
        id=t.id,
        estado=t.estado,
        cancelled_by=t.cancelled_by,
        cancelled_at=t.cancelled_at,
        motivo=t.motivo,
        senia_pendiente_definicion=t.senia_pendiente_definicion,
    )


def _error(e: domain.AgendaError) -> HTTPException:
    body: dict = {"code": e.code, "message": e.message}
    action = getattr(e, "action", None)
    if action:
        body["action"] = action
    return HTTPException(status_code=e.status, detail=body)


@router.post("/turnos/{turno_id}/cancelar", response_model=TurnoResponse)
def cancelar_turno(
    turno_id: str,
    payload: CancelarTurnoRequest,
    user: AuthUser = Depends(require_auth),
    session: Session = Depends(deps.get_session),
    now_utc: datetime = Depends(deps.get_now),
) -> TurnoResponse:
    repo = TurnoRepository(session)
    # Lock de fila en PG; transición condicional por estado en el servicio.
    fila = repo.get_for_update(user.tenant_id, turno_id)
    if fila is None:  # inexistente o cross-tenant → 404 indistinguible (RN-AU-01)
        raise HTTPException(
            status_code=404,
            detail={"code": "RN-AU-01", "message": "Turno no encontrado."},
        )
    turno = _a_dominio(fila)
    antelacion = domain.resolver_antelacion(
        lambda tid: ConfigRepository(session).get_hs(tid), user.tenant_id
    )
    svc = domain.AgendaCancelService()
    try:
        resultado = svc.cancel(
            tenant_id=user.tenant_id,  # R2: del JWT, nunca del frontend
            turno=turno,
            user=domain.User(id=user.id, tenant_id=user.tenant_id, roles=user.roles),
            motivo=payload.motivo,
            now_utc=now_utc,
            antelacion_hs=antelacion,
            # Este slice no tiene tabla de señas: C-12 cablea la lectura real.
            tiene_senia=False,
        )
    except domain.AgendaError as e:
        raise _error(e) from None
    # Persistir transición + auditoría (R1: la fila ya viene filtrada por tenant).
    fila.estado = resultado.estado
    fila.cancelled_by = resultado.cancelled_by
    fila.cancelled_at = resultado.cancelled_at
    fila.motivo = resultado.motivo
    fila.senia_pendiente_definicion = resultado.senia_pendiente_definicion
    session.commit()
    return _a_respuesta(resultado)


@router.get("/config", response_model=ConfigResponse)
def get_config(
    user: AuthUser = Depends(require_auth),
    session: Session = Depends(deps.get_session),
) -> ConfigResponse:
    hs = ConfigRepository(session).get_hs(user.tenant_id)
    if hs is None:
        hs = domain.FALLBACK_ANTELACION_HS
    return ConfigResponse(antelacion_cancel_hs=hs)


@router.put("/config", response_model=ConfigResponse)
def put_config(
    payload: ConfigUpdateRequest,
    user: AuthUser = Depends(require_roles("dueno")),
    session: Session = Depends(deps.get_session),
) -> ConfigResponse:
    cfg = ConfigRepository(session).upsert(user.tenant_id, payload.antelacion_cancel_hs)
    session.commit()
    return ConfigResponse(antelacion_cancel_hs=cfg.antelacion_cancel_hs)

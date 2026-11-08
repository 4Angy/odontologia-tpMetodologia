"""Router de lista de espera (C-10)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import deps
from app.core.security import AuthUser, require_auth, require_roles
from app.modules.agenda.models import TurnoModel
from app.modules.lista_espera.models import ListaEsperaModel
from app.modules.lista_espera.schemas import (
    ListaEsperaCreate,
    ListaEsperaResponse,
    OfrecerManualRequest,
)
from app.modules.lista_espera.service import ListaEsperaError, ListaEsperaService, Hueco

router = APIRouter()


def _a_respuesta(entry: ListaEsperaModel) -> ListaEsperaResponse:
    return ListaEsperaResponse(
        id=entry.id,
        tenant_id=entry.tenant_id,
        paciente_id=entry.paciente_id,
        profesional_id=entry.profesional_id,
        prestacion_id=entry.prestacion_id,
        prioridad=entry.prioridad,
        estado=entry.estado,
        motivo_omision=entry.motivo_omision,
        hueco_profesional_id=entry.hueco_profesional_id,
        hueco_inicio=entry.hueco_inicio,
        hueco_fin=entry.hueco_fin,
        hueco_prestacion_id=entry.hueco_prestacion_id,
        ofrecido_at=entry.ofrecido_at,
        expires_at=entry.expires_at,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _error(exc: ListaEsperaError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})


@router.post("/lista-espera", response_model=ListaEsperaResponse, status_code=201)
def crear_lista_espera(
    payload: ListaEsperaCreate,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
    now: datetime = Depends(deps.get_now),
) -> ListaEsperaResponse:
    from app.modules.lista_espera.models import ListaEsperaModel

    entry = ListaEsperaModel(
        tenant_id=user.tenant_id,
        paciente_id=payload.paciente_id,
        profesional_id=payload.profesional_id,
        prestacion_id=payload.prestacion_id,
        prioridad=payload.prioridad,
    )
    session.add(entry)
    session.flush()
    return _a_respuesta(entry)


@router.get("/lista-espera", response_model=list[ListaEsperaResponse])
def listar_lista_espera(
    estado: str | None = Query(default=None),
    user: AuthUser = Depends(require_roles("recepcion", "dueno", "odontologo")),
    session: Session = Depends(deps.get_session),
) -> list[ListaEsperaResponse]:
    from app.modules.lista_espera.repository import ListaEsperaRepository

    repo = ListaEsperaRepository(session)
    entries = repo.list(user.tenant_id, estado=estado)
    return [_a_respuesta(e) for e in entries]


@router.post("/lista-espera/{entry_id}/ofrecer", response_model=ListaEsperaResponse)
def ofrecer_manual(
    entry_id: str,
    payload: OfrecerManualRequest,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
    now: datetime = Depends(deps.get_now),
) -> ListaEsperaResponse:
    from app.modules.lista_espera.repository import ListaEsperaRepository

    repo = ListaEsperaRepository(session)
    entry = repo.get_by_id(user.tenant_id, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Entrada no encontrada."})
    if entry.estado != "activa":
        raise HTTPException(status_code=409, detail={"code": "RN-AG-08", "message": "La entrada no esta activa."})
    # marcar como activa compatible forzando hueco
    svc = ListaEsperaService(session, now)
    hueco = Hueco(
        profesional_id=payload.hueco.profesional_id,
        inicio=payload.hueco.inicio,
        fin=payload.hueco.fin,
        prestacion_id=payload.hueco.prestacion_id,
    )
    offered = svc.ofrecer_por_hueco(user.tenant_id, hueco, now)
    if offered is None or offered.id != entry.id:
        # si se ofrecio otra entrada, devolver la original sin cambios
        session.rollback()
        raise HTTPException(status_code=409, detail={"code": "RN-AG-03", "message": "No se pudo ofrecer esta entrada."})
    session.commit()
    return _a_respuesta(offered)


# --- Endpoints publicos (aceptar/declinar por token) ---

from app.modules.agenda.public_booking import PUBLIC_RATE_LIMITER


def _check_rate(key: str, limit: int, window_seconds: int) -> None:
    result = PUBLIC_RATE_LIMITER.check(key, limit=limit, window_seconds=window_seconds)
    if not result.allowed:
        raise HTTPException(
            status_code=429,
            headers={"Retry-After": str(result.retry_after or 1)},
            detail={"code": "RN-GL-03", "message": "Demasiados intentos. Proba mas tarde."},
        )


@router.post("/public/lista-espera/{token}/aceptar")
def public_aceptar(
    token: str,
    tenant_slug: str | None = Query(default=None, alias="tenant_slug"),
    session: Session = Depends(deps.get_session),
    now: datetime = Depends(deps.get_now),
):
    _check_rate(f"wa:{token}", 20, 60)
    from app.modules.lista_espera.service import ListaEsperaService

    svc = ListaEsperaService(session, now)
    try:
        entry, turno = svc.aceptar(token, tenant_slug, now)
    except Exception as exc:
        session.rollback()
        if isinstance(exc, ListaEsperaError):
            raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
        raise
    session.commit()
    return {"turno_id": turno.id, "estado": turno.estado}


@router.post("/public/lista-espera/{token}/declinar")
def public_declinar(
    token: str,
    tenant_slug: str | None = Query(default=None, alias="tenant_slug"),
    session: Session = Depends(deps.get_session),
    now: datetime = Depends(deps.get_now),
):
    _check_rate(f"wa:{token}", 20, 60)
    from app.modules.lista_espera.service import ListaEsperaService

    svc = ListaEsperaService(session, now)
    try:
        entry = svc.declinar(token, tenant_slug, now)
    except Exception as exc:
        session.rollback()
        if isinstance(exc, ListaEsperaError):
            raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
        raise
    session.commit()
    return {"estado": entry.estado}

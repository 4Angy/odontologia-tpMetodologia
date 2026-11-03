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
from app.modules.agenda.models import (
    BloqueoModel,
    PrestacionModel,
    ProfesionalModel,
    TurnoModel,
)
from app.modules.agenda.repository import (
    BloqueoRepository,
    ConfigRepository,
    PrestacionRepository,
    ProfesionalRepository,
    TurnoRepository,
)
from app.modules.agenda.schemas import (
    BloqueoCreate,
    BloqueoResponse,
    CancelarTurnoRequest,
    ConfigResponse,
    ConfigUpdateRequest,
    PrestacionCreate,
    PrestacionResponse,
    ProfesionalCreate,
    ProfesionalResponse,
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


def _as_profesional_response(item: ProfesionalModel) -> ProfesionalResponse:
    return ProfesionalResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        nombre=item.nombre,
        usuario_id=item.usuario_id,
        color_agenda=item.color_agenda,
        activo=item.activo,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _as_prestacion_response(item: PrestacionModel) -> PrestacionResponse:
    return PrestacionResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        nombre=item.nombre,
        duracion_min=item.duracion_min,
        precio_ref=item.precio_ref,
        activa=item.activa,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _as_bloqueo_response(item: BloqueoModel) -> BloqueoResponse:
    return BloqueoResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        profesional_id=item.profesional_id,
        inicio=item.inicio,
        fin=item.fin,
        motivo=item.motivo,
        created_at=item.created_at,
        updated_at=item.updated_at,
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


@router.get("/profesionales", response_model=list[ProfesionalResponse])
def listar_profesionales(
    user: AuthUser = Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
) -> list[ProfesionalResponse]:
    repo = ProfesionalRepository(session)
    return [_as_profesional_response(item) for item in repo.list(user.tenant_id)]


@router.post("/profesionales", response_model=ProfesionalResponse, status_code=201)
def crear_profesional(
    payload: ProfesionalCreate,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
) -> ProfesionalResponse:
    item = ProfesionalModel(
        tenant_id=user.tenant_id,
        nombre=payload.nombre.strip(),
        usuario_id=payload.usuario_id.strip() if payload.usuario_id else None,
        color_agenda=payload.color_agenda.strip() if payload.color_agenda else None,
        activo=payload.activo,
    )
    repo = ProfesionalRepository(session)
    repo.create(item)
    session.commit()
    return _as_profesional_response(item)


@router.get("/profesionales/{profesional_id}", response_model=ProfesionalResponse)
def obtener_profesional(
    profesional_id: str,
    user: AuthUser = Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
) -> ProfesionalResponse:
    item = ProfesionalRepository(session).get_by_id(user.tenant_id, profesional_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Profesional no encontrado."})
    return _as_profesional_response(item)


@router.put("/profesionales/{profesional_id}", response_model=ProfesionalResponse)
def actualizar_profesional(
    profesional_id: str,
    payload: ProfesionalCreate,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
) -> ProfesionalResponse:
    item = ProfesionalRepository(session).get_by_id(user.tenant_id, profesional_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Profesional no encontrado."})
    item.nombre = payload.nombre.strip()
    item.usuario_id = payload.usuario_id.strip() if payload.usuario_id else None
    item.color_agenda = payload.color_agenda.strip() if payload.color_agenda else None
    item.activo = payload.activo
    session.commit()
    return _as_profesional_response(item)


@router.delete("/profesionales/{profesional_id}", status_code=204)
def borrar_profesional(
    profesional_id: str,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
) -> None:
    item = ProfesionalRepository(session).get_by_id(user.tenant_id, profesional_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Profesional no encontrado."})
    ProfesionalRepository(session).delete(item)
    session.commit()


@router.get("/prestaciones", response_model=list[PrestacionResponse])
def listar_prestaciones(
    user: AuthUser = Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
) -> list[PrestacionResponse]:
    repo = PrestacionRepository(session)
    return [_as_prestacion_response(item) for item in repo.list(user.tenant_id)]


@router.post("/prestaciones", response_model=PrestacionResponse, status_code=201)
def crear_prestacion(
    payload: PrestacionCreate,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
) -> PrestacionResponse:
    item = PrestacionModel(
        tenant_id=user.tenant_id,
        nombre=payload.nombre.strip(),
        duracion_min=payload.duracion_min,
        precio_ref=payload.precio_ref,
        activa=payload.activa,
    )
    PrestacionRepository(session).create(item)
    session.commit()
    return _as_prestacion_response(item)


@router.get("/prestaciones/{prestacion_id}", response_model=PrestacionResponse)
def obtener_prestacion(
    prestacion_id: str,
    user: AuthUser = Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
) -> PrestacionResponse:
    item = PrestacionRepository(session).get_by_id(user.tenant_id, prestacion_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Prestación no encontrada."})
    return _as_prestacion_response(item)


@router.put("/prestaciones/{prestacion_id}", response_model=PrestacionResponse)
def actualizar_prestacion(
    prestacion_id: str,
    payload: PrestacionCreate,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
) -> PrestacionResponse:
    item = PrestacionRepository(session).get_by_id(user.tenant_id, prestacion_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Prestación no encontrada."})
    item.nombre = payload.nombre.strip()
    item.duracion_min = payload.duracion_min
    item.precio_ref = payload.precio_ref
    item.activa = payload.activa
    session.commit()
    return _as_prestacion_response(item)


@router.delete("/prestaciones/{prestacion_id}", status_code=204)
def borrar_prestacion(
    prestacion_id: str,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
) -> None:
    item = PrestacionRepository(session).get_by_id(user.tenant_id, prestacion_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Prestación no encontrada."})
    PrestacionRepository(session).delete(item)
    session.commit()


@router.get("/bloqueos", response_model=list[BloqueoResponse])
def listar_bloqueos(
    user: AuthUser = Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
) -> list[BloqueoResponse]:
    repo = BloqueoRepository(session)
    return [_as_bloqueo_response(item) for item in repo.list(user.tenant_id)]


@router.post("/bloqueos", response_model=BloqueoResponse, status_code=201)
def crear_bloqueo(
    payload: BloqueoCreate,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
) -> BloqueoResponse:
    if payload.fin <= payload.inicio:
        raise HTTPException(status_code=422, detail={"code": "RN-GL-02", "message": "El rango del bloqueo es inválido."})
    item = BloqueoModel(
        tenant_id=user.tenant_id,
        profesional_id=payload.profesional_id,
        inicio=payload.inicio,
        fin=payload.fin,
        motivo=payload.motivo.strip() if payload.motivo else None,
    )
    BloqueoRepository(session).create(item)
    session.commit()
    return _as_bloqueo_response(item)


@router.get("/bloqueos/{bloqueo_id}", response_model=BloqueoResponse)
def obtener_bloqueo(
    bloqueo_id: str,
    user: AuthUser = Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
) -> BloqueoResponse:
    item = BloqueoRepository(session).get_by_id(user.tenant_id, bloqueo_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Bloqueo no encontrado."})
    return _as_bloqueo_response(item)


@router.put("/bloqueos/{bloqueo_id}", response_model=BloqueoResponse)
def actualizar_bloqueo(
    bloqueo_id: str,
    payload: BloqueoCreate,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
) -> BloqueoResponse:
    item = BloqueoRepository(session).get_by_id(user.tenant_id, bloqueo_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Bloqueo no encontrado."})
    if payload.fin <= payload.inicio:
        raise HTTPException(status_code=422, detail={"code": "RN-GL-02", "message": "El rango del bloqueo es inválido."})
    item.profesional_id = payload.profesional_id
    item.inicio = payload.inicio
    item.fin = payload.fin
    item.motivo = payload.motivo.strip() if payload.motivo else None
    session.commit()
    return _as_bloqueo_response(item)


@router.delete("/bloqueos/{bloqueo_id}", status_code=204)
def borrar_bloqueo(
    bloqueo_id: str,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
) -> None:
    item = BloqueoRepository(session).get_by_id(user.tenant_id, bloqueo_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Bloqueo no encontrado."})
    BloqueoRepository(session).delete(item)
    session.commit()


@router.get("/config", response_model=ConfigResponse)
def get_config(
    user: AuthUser = Depends(require_auth),
    session: Session = Depends(deps.get_session),
) -> ConfigResponse:
    cfg = ConfigRepository(session).get(user.tenant_id)
    if cfg is None:
        return ConfigResponse(
            antelacion_cancel_hs=domain.FALLBACK_ANTELACION_HS,
            antelacion_reserva_hs=2,
            recordatorio_t_48h=True,
            recordatorio_t_24h=True,
        )
    return ConfigResponse(
        antelacion_cancel_hs=cfg.antelacion_cancel_hs,
        antelacion_reserva_hs=cfg.antelacion_reserva_hs,
        recordatorio_t_48h=cfg.recordatorio_t_48h,
        recordatorio_t_24h=cfg.recordatorio_t_24h,
    )


@router.put("/config", response_model=ConfigResponse)
def put_config(
    payload: ConfigUpdateRequest,
    user: AuthUser = Depends(require_roles("dueno")),
    session: Session = Depends(deps.get_session),
) -> ConfigResponse:
    cfg = ConfigRepository(session).upsert(
        user.tenant_id,
        payload.antelacion_cancel_hs,
        payload.antelacion_reserva_hs,
        payload.recordatorio_t_48h,
        payload.recordatorio_t_24h,
    )
    session.commit()
    return ConfigResponse(
        antelacion_cancel_hs=cfg.antelacion_cancel_hs,
        antelacion_reserva_hs=cfg.antelacion_reserva_hs,
        recordatorio_t_48h=cfg.recordatorio_t_48h,
        recordatorio_t_24h=cfg.recordatorio_t_24h,
    )

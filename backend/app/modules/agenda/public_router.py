from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app import deps
from app.modules.agenda.public_booking import (
    PublicActionRequest,
    PublicActionResponse,
    PublicAvailabilityResponse,
    PublicBookingRequest,
    PublicBookingResponse,
    PublicBookingService,
    PublicRescheduleRequest,
    PublicSlotConflictError,
    PUBLIC_RATE_LIMITER,
)
from app.modules.agenda.models import ConfigModel
from app.modules.agenda.router import _a_dominio
from app.modules.agenda.service import AgendaCancelService, AgendaError, User

router = APIRouter(tags=["reserva-publica"])


def _service(session: Session) -> PublicBookingService:
    return PublicBookingService(session, rate_limiter=PUBLIC_RATE_LIMITER)


def _check_rate(key: str, limit: int, window_seconds: int) -> None:
    result = PUBLIC_RATE_LIMITER.check(key, limit=limit, window_seconds=window_seconds)
    if not result.allowed:
        raise HTTPException(
            status_code=429,
            headers={"Retry-After": str(result.retry_after or 1)},
            detail={"code": "RN-GL-03", "message": "Demasiados intentos. Probá más tarde."},
        )


def _public_error(error: Exception) -> HTTPException:
    if isinstance(error, AgendaError):
        detail: dict[str, object] = {
            "code": error.code,
            "message": error.message,
        }
        action = getattr(error, "action", None)
        if action is not None:
            detail["action"] = action
        return HTTPException(status_code=error.status, detail=detail)
    if isinstance(error, LookupError):
        return HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Consultorio no encontrado."})
    if isinstance(error, RuntimeError):
        detail: dict[str, object] = {
            "code": "RN-AG-03",
            "message": "El horario ya no está disponible.",
        }
        alternatives = getattr(error, "alternatives", None)
        if alternatives is not None:
            detail["alternativas"] = [option.isoformat() for option in alternatives]
        return HTTPException(status_code=409, detail=detail)
    if isinstance(error, PermissionError):
        return HTTPException(status_code=401, detail={"code": "RN-AU-03", "message": "El enlace no es válido o venció."})
    return HTTPException(status_code=409, detail={"code": "RN-GL-02", "message": str(error)})


@router.get("/r/{tenant_slug}", response_model=PublicAvailabilityResponse)
def public_availability(
    tenant_slug: str,
    request: Request,
    profesional_id: str | None = None,
    prestacion_id: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    session: Session = Depends(deps.get_session),
    now: datetime = Depends(deps.get_now),
) -> PublicAvailabilityResponse:
    _check_rate(
        f"availability:{request.client.host if request.client else 'unknown'}:{tenant_slug}",
        limit=60,
        window_seconds=60,
    )
    ahora_utc = now.astimezone(timezone.utc)
    desde = desde or ahora_utc
    hasta = hasta or (ahora_utc + timedelta(days=14))
    try:
        result = _service(session).availability(
            slug=tenant_slug,
            profesional_id=profesional_id,
            prestacion_id=prestacion_id,
            desde=desde,
            hasta=hasta,
            ahora=now,
        )
        session.commit()
        return result
    except (LookupError, ValueError) as error:
        session.rollback()
        raise _public_error(error) from error


@router.post("/public/reservar", response_model=PublicBookingResponse, status_code=201)
def public_book(
    payload: PublicBookingRequest,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    session: Session = Depends(deps.get_session),
    now: datetime = Depends(deps.get_now),
) -> PublicBookingResponse:
    service = _service(session)
    _check_rate(
        f"booking:{request.client.host if request.client else 'unknown'}:{payload.tenant_slug}",
        limit=10,
        window_seconds=60,
    )
    try:
        result = service.create(payload, idempotency_key, now)
        session.commit()
        return result
    except (LookupError, ValueError, RuntimeError) as error:
        session.rollback()
        raise _public_error(error) from error


@router.post("/public/turnos/{token}/confirmar", response_model=PublicActionResponse)
def public_confirm(token: str, payload: PublicActionRequest, request: Request, session: Session = Depends(deps.get_session), now: datetime = Depends(deps.get_now)) -> PublicActionResponse:
    _check_rate(f"action:{request.client.host if request.client else 'unknown'}:{payload.tenant_slug}", 20, 60)
    try:
        turno = _service(session).action(token, "confirm", payload.tenant_slug, now)
        turno = _service(session).confirm(turno)
        session.commit()
        return PublicActionResponse(turno_id=turno.id, estado=turno.estado)
    except (LookupError, PermissionError, ValueError, AgendaError) as error:
        session.rollback()
        if isinstance(error, PermissionError):
            try:
                _service(session).record_rejection(
                    slug=payload.tenant_slug,
                    action="confirm",
                    outcome=str(error),
                )
                session.commit()
            except LookupError:
                session.rollback()
        raise _public_error(error) from error


@router.post("/public/turnos/{token}/cancelar", response_model=PublicActionResponse)
def public_cancel(token: str, payload: PublicActionRequest, request: Request, session: Session = Depends(deps.get_session), now: datetime = Depends(deps.get_now)) -> PublicActionResponse:
    _check_rate(f"action:{request.client.host if request.client else 'unknown'}:{payload.tenant_slug}", 20, 60)
    try:
        turno = _service(session).action(token, "cancel", payload.tenant_slug, now)
        config = session.get(ConfigModel, turno.tenant_id)
        antelacion = config.antelacion_cancel_hs if config else 24
        user = User(id="public", tenant_id=turno.tenant_id, roles=("recepcion",))
        result = AgendaCancelService().cancel(
            tenant_id=turno.tenant_id,
            turno=_a_dominio(turno),
            user=user,
            motivo="Cancelación solicitada por paciente",
            now_utc=now,
            antelacion_hs=antelacion,
        )
        turno.estado, turno.cancelled_by, turno.cancelled_at, turno.motivo = result.estado, result.cancelled_by, result.cancelled_at, result.motivo
        session.commit()
        return PublicActionResponse(turno_id=turno.id, estado=turno.estado)
    except (LookupError, PermissionError, ValueError, AgendaError) as error:
        session.rollback()
        if isinstance(error, PermissionError):
            try:
                _service(session).record_rejection(
                    slug=payload.tenant_slug,
                    action="cancel",
                    outcome=str(error),
                )
                session.commit()
            except LookupError:
                session.rollback()
        raise _public_error(error) from error


@router.post("/public/turnos/{token}/reprogramar", response_model=PublicBookingResponse)
def public_reschedule(token: str, payload: PublicRescheduleRequest, request: Request, session: Session = Depends(deps.get_session), now: datetime = Depends(deps.get_now)) -> PublicBookingResponse:
    _check_rate(f"action:{request.client.host if request.client else 'unknown'}:{payload.tenant_slug}", 20, 60)
    try:
        turno = _service(session).action(token, "reschedule", payload.tenant_slug, now)
        if turno.estado not in {"confirmado", "pendiente_confirmacion"}:
            raise ValueError("El turno ya no puede reprogramarse.")
        result = _service(session).reschedule(
            turno,
            profesional_id=payload.profesional_id,
            prestacion_id=payload.prestacion_id,
            inicio=payload.inicio,
            now=now,
        )
        session.commit()
        return result
    except (LookupError, PermissionError, ValueError, RuntimeError, AgendaError) as error:
        session.rollback()
        if isinstance(error, PermissionError):
            try:
                _service(session).record_rejection(
                    slug=payload.tenant_slug,
                    action="reschedule",
                    outcome=str(error),
                )
                session.commit()
            except LookupError:
                session.rollback()
        raise _public_error(error) from error

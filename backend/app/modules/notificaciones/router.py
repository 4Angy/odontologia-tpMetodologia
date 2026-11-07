"""Router HTTP del motor de notificaciones (C-09)."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app import deps
from app.core.security import AuthUser, require_auth, require_roles
from app.modules.agenda.models import TenantModel
from app.modules.agenda.repository import ConfigRepository
from app.modules.notificaciones import schemas as dto
from app.modules.notificaciones.models import NotificacionEnvioModel
from app.modules.notificaciones.repository import NotificacionEnvioRepository, PlantillaRepository
from app.modules.notificaciones.scheduler import SchedulerService
from app.modules.notificaciones.sender import SenderService
from app.modules.notificaciones.webhook import WebhookService, verify_signature, verify_token
from app.modules.notificaciones.whatsapp import WhatsAppClient, CloudApiClient, FakeClient
from app.modules.notificaciones.email import EmailClient, SmtpEmailClient, FakeEmailClient
from app.core.config import get_settings

router = APIRouter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _a_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _tenant_tz(session: Session, tenant_id: str) -> ZoneInfo:
    tenant = session.get(TenantModel, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Consultorio no encontrado."})
    try:
        return ZoneInfo(tenant.tz)
    except ZoneInfoNotFoundError:
        raise HTTPException(status_code=500, detail={"code": "RN-GL-02", "message": "Zona horaria inválida."})


@router.get("/notificaciones/consumo", response_model=dto.ConsumoResponse)
def consumo(
    desde: date = Query(...),
    hasta: date = Query(...),
    user: AuthUser = Depends(require_roles("dueno")),
    session: Session = Depends(deps.get_session),
) -> dto.ConsumoResponse:
    if hasta < desde:
        raise HTTPException(status_code=422, detail={"code": "RN-GL-02", "message": "El rango es inválido."})
    tz = _tenant_tz(session, user.tenant_id)
    desde_utc = datetime.combine(desde, time.min, tzinfo=tz).astimezone(timezone.utc)
    hasta_utc = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=tz).astimezone(timezone.utc)
    repo = NotificacionEnvioRepository(session)
    items = repo.consumo(user.tenant_id, desde_utc, hasta_utc)
    return dto.ConsumoResponse(
        desde=desde_utc,
        hasta=hasta_utc,
        items=[dto.ConsumoItem(**item) for item in items],
    )


@router.get("/notificaciones/envios", response_model=list[dto.NotificacionEnvioResponse])
def listar_envios(
    estado: str | None = Query(default=None),
    turno_id: str | None = Query(default=None),
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
) -> list[dto.NotificacionEnvioResponse]:
    repo = NotificacionEnvioRepository(session)
    envios = repo.list_for_tenant(user.tenant_id, estado=estado, turno_id=turno_id)
    return [_a_respuesta(e) for e in envios]


@router.post("/notificaciones/envios/{envio_id}/reintentar", response_model=dto.ReintentarResponse)
def reintentar(
    envio_id: str,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
    now: datetime = Depends(deps.get_now),
) -> dto.ReintentarResponse:
    repo = NotificacionEnvioRepository(session)
    envio = repo.get_by_id(user.tenant_id, envio_id)
    if envio is None:
        raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Envío no encontrado."})
    if envio.estado != "fallida":
        raise HTTPException(
            status_code=409,
            detail={"code": "RN-GL-02", "message": "Solo se puede reintentar un envío fallido."},
        )
    envio.estado = "encolada"
    envio.intentos = 0
    envio.next_attempt_at = _a_utc(now)
    envio.ultimo_error_code = None
    session.flush()
    return dto.ReintentarResponse(id=envio.id, estado=envio.estado)


@router.post("/notificaciones/test", response_model=dto.NotificacionTestResponse)
def enviar_test(
    payload: dto.NotificacionTestRequest,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
    now: datetime = Depends(deps.get_now),
) -> dto.NotificacionTestResponse:
    from app.modules.pacientes.repository import PacienteRepository

    paciente = PacienteRepository(session).get_by_id(user.tenant_id, payload.paciente_id)
    if paciente is None:
        raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Paciente no encontrado."})
    canal = payload.canal or ("whatsapp" if paciente.telefono else "email")
    if canal not in ("whatsapp", "email"):
        raise HTTPException(status_code=422, detail={"code": "RN-GL-02", "message": "Canal inválido."})
    # verificar opt-in para whatsapp
    if canal == "whatsapp":
        from app.modules.pacientes.models import OptInModel
        from sqlalchemy import select

        optin = session.execute(
            select(OptInModel).where(
                OptInModel.tenant_id == user.tenant_id,
                OptInModel.paciente_id == paciente.id,
                OptInModel.canal == "whatsapp",
            )
        ).scalar_one_or_none()
        if optin is None or not bool(optin.estado):
            raise HTTPException(
                status_code=409,
                detail={"code": "RN-PA-01", "message": "El paciente no tiene opt-in de WhatsApp."},
            )
    envio = NotificacionEnvioModel(
        tenant_id=user.tenant_id,
        paciente_id=paciente.id,
        turno_id=None,
        canal=canal,
        plantilla_codigo="recordatorio",
        ventana=None,
        estado="encolada",
        motivo_code=None,
        intentos=0,
        next_attempt_at=_a_utc(now),
        costo_estimado_centavos=0,
    )
    session.add(envio)
    session.flush()
    # audit
    from app.core.audit import registrar_auditoria

    registrar_auditoria(
        session,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        accion="notificaciones.test.enviado",
        recurso="notificacion_envio",
        recurso_id=envio.id,
        campos=["paciente_id", "canal"],
    )
    session.commit()
    return dto.NotificacionTestResponse(id=envio.id, estado=envio.estado, canal=envio.canal)


@router.get("/webhooks/whatsapp")
def webhook_challenge(request: Request) -> dict:
    settings = get_settings()
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    expected = settings.whatsapp_verify_token.get_secret_value() if settings.whatsapp_verify_token else None
    if mode == "subscribe" and verify_token(token, expected) and challenge is not None:
        return PlainTextResponse(content=challenge)
    raise HTTPException(status_code=403, detail={"code": "RN-AU-03", "message": "Verificación fallida."})


@router.post("/webhooks/whatsapp")
async def webhook_event(request: Request, session: Session = Depends(deps.get_session), now: datetime = Depends(deps.get_now)) -> dict:
    settings = get_settings()
    raw = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    app_secret = settings.whatsapp_app_secret.get_secret_value() if settings.whatsapp_app_secret else None
    if not verify_signature(raw, signature, app_secret):
        raise HTTPException(status_code=401, detail={"code": "RN-AU-03", "message": "Firma inválida."})
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except json.JSONDecodeError:
        payload = {}
    svc = WebhookService(session, now)
    actualizados = svc.procesar(payload)
    session.commit()
    return {"ok": True, "actualizados": actualizados}


@router.get("/webhooks/whatsapp/challenge")
def _challenge_alias(request: Request) -> dict:
    return webhook_challenge(request)


def _a_respuesta(envio: NotificacionEnvioModel) -> dto.NotificacionEnvioResponse:
    return dto.NotificacionEnvioResponse(
        id=envio.id,
        tenant_id=envio.tenant_id,
        paciente_id=envio.paciente_id,
        turno_id=envio.turno_id,
        canal=envio.canal,
        plantilla_codigo=envio.plantilla_codigo,
        ventana=envio.ventana,
        estado=envio.estado,
        motivo_code=envio.motivo_code,
        intentos=envio.intentos,
        next_attempt_at=envio.next_attempt_at,
        provider_msg_id=envio.provider_msg_id,
        costo_estimado_centavos=envio.costo_estimado_centavos,
        ultimo_error_code=envio.ultimo_error_code,
        enviado_at=envio.enviado_at,
        entregado_at=envio.entregado_at,
    )


__all__ = ["router"]

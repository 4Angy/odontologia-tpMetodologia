"""Router del slice: POST /turnos/:id/cancelar + GET/PUT /config.

Adaptador HTTP fino: el router resuelve tenant del JWT (R2), valida DTOs y
mapea errores de dominio a `{code, message, action?}` (R9, RN-GL-01).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import registrar_auditoria
from app.core.security import AuthUser, require_auth, require_roles
from app import deps
from app.modules.agenda import service as domain
from app.modules.agenda.availability import candidatos_disponibles
from app.modules.agenda.models import (
    BloqueoModel,
    HorarioProfesionalModel,
    PrestacionModel,
    ProfesionalModel,
    TenantModel,
    TurnoModel,
)
from app.modules.agenda.turnos_service import TurnosService
from app.modules.agenda.repository import (
    BloqueoRepository,
    ConfigRepository,
    PrestacionRepository,
    ProfesionalRepository,
    TurnoRepository,
)
from app.modules.pacientes.repository import PacienteRepository
from app.modules.agenda.schemas import (
    BloqueoCreate,
    BloqueoResponse,
    CancelarTurnoRequest,
    ConfigResponse,
    ConfigUpdateRequest,
    HorarioSemanalResponse,
    HorariosSemanaResponse,
    HorariosSemanaUpdate,
    PrestacionCreate,
    PrestacionResponse,
    ProfesionalCreate,
    ProfesionalResponse,
    ReprogramarTurnoResponse,
    TurnoResponse,
    TurnoAgendaResponse,
    TurnoCreateRequest,
    TurnoReprogramarRequest,
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
        senia_requerida=item.senia_requerida,
        senia_monto_cents=item.senia_monto_cents,
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


def _commit_audit(
    session: Session,
    user: AuthUser,
    *,
    accion: str,
    recurso: str,
    recurso_id: str,
    campos: list[str],
) -> None:
    registrar_auditoria(
        session,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        accion=accion,
        recurso=recurso,
        recurso_id=recurso_id,
        campos=campos,
    )
    session.commit()


def _bloqueo_intervalo_utc(
    inicio: datetime,
    fin: datetime,
) -> tuple[datetime, datetime]:
    if (
        inicio.tzinfo is None
        or inicio.utcoffset() is None
        or fin.tzinfo is None
        or fin.utcoffset() is None
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "RN-GL-02",
                "message": "El inicio y el fin deben incluir zona horaria.",
            },
        )
    inicio_utc = inicio.astimezone(timezone.utc)
    fin_utc = fin.astimezone(timezone.utc)
    if fin_utc <= inicio_utc:
        raise HTTPException(
            status_code=422,
            detail={"code": "RN-GL-02", "message": "El rango del bloqueo es inválido."},
        )
    return inicio_utc, fin_utc


def _require_profesional(
    session: Session,
    tenant_id: str,
    profesional_id: str,
) -> ProfesionalModel:
    profesional = ProfesionalRepository(session).get_by_id(tenant_id, profesional_id)
    if profesional is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "RN-AU-01", "message": "Profesional no encontrado."},
        )
    return profesional


def _validate_horarios(horarios) -> None:
    por_dia: dict[int, list[tuple[time, time]]] = {}
    for horario in horarios:
        if horario.fin <= horario.inicio:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "RN-GL-02",
                    "message": "El fin debe ser posterior al inicio del horario.",
                },
            )
        por_dia.setdefault(horario.dia_semana, []).append(
            (horario.inicio, horario.fin)
        )

    for intervalos in por_dia.values():
        ordenados = sorted(intervalos)
        if any(
            actual[0] < anterior[1]
            for anterior, actual in zip(ordenados, ordenados[1:])
        ):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "RN-GL-02",
                    "message": "Los horarios de un mismo día no pueden superponerse.",
                },
            )


def _horarios_response(
    session: Session,
    tenant_id: str,
    profesional_id: str,
) -> HorariosSemanaResponse:
    tenant = session.get(TenantModel, tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "RN-AU-01", "message": "Consultorio no encontrado."},
        )
    try:
        ZoneInfo(tenant.tz)
    except ZoneInfoNotFoundError:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "RN-GL-02",
                "message": "La zona horaria configurada para el consultorio no es válida.",
            },
        ) from None
    horarios = session.execute(
        select(HorarioProfesionalModel)
        .where(
            HorarioProfesionalModel.tenant_id == tenant_id,
            HorarioProfesionalModel.profesional_id == profesional_id,
        )
        .order_by(
            HorarioProfesionalModel.dia_semana,
            HorarioProfesionalModel.hora_inicio,
        )
    ).scalars().all()
    return HorariosSemanaResponse(
        profesional_id=profesional_id,
        zona_horaria=tenant.tz,
        horarios=[
            HorarioSemanalResponse(
                id=horario.id,
                dia_semana=horario.dia_semana,
                inicio=horario.hora_inicio,
                fin=horario.hora_fin,
            )
            for horario in horarios
        ],
    )


def _error(e: domain.AgendaError) -> HTTPException:
    body: dict = {"code": e.code, "message": e.message}
    action = getattr(e, "action", None)
    if action:
        body["action"] = action
    alternativas = getattr(e, "alternativas", None)
    if alternativas is not None:
        body["alternativas"] = [opcion.isoformat() for opcion in alternativas]
    return HTTPException(status_code=e.status, detail=body)


def _turnos_service(session: Session) -> TurnosService:
    return TurnosService(
        repo=TurnoRepository(session),
        pacientes=PacienteRepository(session),
        prestaciones=PrestacionRepository(session),
        disponibilidad=lambda **kwargs: (
            candidatos_disponibles(session, **kwargs)
            if kwargs["prestacion_id"] is not None
            else []
        ),
    )


def _agenda_response(turno: TurnoModel) -> TurnoAgendaResponse:
    return TurnoAgendaResponse(
        id=turno.id,
        paciente_id=turno.paciente_id,
        profesional_id=turno.profesional_id,
        profesional_usuario_id=turno.profesional_usuario_id,
        prestacion_id=turno.prestacion_id,
        inicio=turno.inicio,
        fin=turno.fin,
        estado=turno.estado,
        origen=turno.origen,
        sobreturno=turno.sobreturno,
        sobreturno_motivo=turno.sobreturno_motivo,
        sobreturno_autorizado_por=turno.sobreturno_autorizado_por,
        senia_id=turno.senia_id,
        cancelled_by=turno.cancelled_by,
        cancelled_at=turno.cancelled_at,
        motivo=turno.motivo,
    )


def _agenda_ventana(
    session: Session,
    tenant_id: str,
    desde: date,
    hasta: date,
) -> tuple[datetime, datetime]:
    tenant = session.get(TenantModel, tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "RN-AU-01", "message": "Consultorio no encontrado."},
        )
    try:
        zona = ZoneInfo(tenant.tz)
    except ZoneInfoNotFoundError:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "RN-GL-02",
                "message": "La zona horaria configurada para el consultorio no es válida.",
            },
        ) from None
    inicio_local = datetime.combine(desde, time.min, tzinfo=zona)
    fin_local = datetime.combine(hasta, time.min, tzinfo=zona)
    return inicio_local.astimezone(timezone.utc), fin_local.astimezone(timezone.utc)


def _listar_agenda(
    session: Session,
    user: AuthUser,
    desde: date,
    hasta: date,
    profesional_id: str | None,
) -> list[TurnoAgendaResponse]:
    inicio_utc, fin_utc = _agenda_ventana(session, user.tenant_id, desde, hasta)
    solo_mis_turnos = (
        "odontologo" in user.roles
        and not {"recepcion", "dueno"}.intersection(user.roles)
    )
    turnos = TurnoRepository(session).list_for_agenda(
        tenant_id=user.tenant_id,
        desde=inicio_utc,
        hasta=fin_utc,
        profesional_id=profesional_id,
        profesional_usuario_id=user.id if solo_mis_turnos else None,
    )
    return [_agenda_response(turno) for turno in turnos]


def _domain_user(user: AuthUser) -> domain.User:
    return domain.User(id=user.id, tenant_id=user.tenant_id, roles=user.roles)


@router.post("/turnos", response_model=TurnoAgendaResponse, status_code=201)
def crear_turno(
    payload: TurnoCreateRequest,
    idempotency_key: str = Header(
        alias="Idempotency-Key", min_length=1, max_length=255
    ),
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
    now_utc: datetime = Depends(deps.get_now),
) -> TurnoAgendaResponse:
    try:
        resultado = _turnos_service(session).crear_turno(
            user=_domain_user(user),
            request=payload,
            idempotency_key=idempotency_key,
            ahora_utc=now_utc,
        )
    except domain.AgendaError as error:
        raise _error(error) from None
    if resultado.creado:
        _commit_audit(
            session,
            user,
            accion="agenda.turno.creado",
            recurso="turno",
            recurso_id=resultado.turno.id,
            campos=[
                "paciente_id",
                "profesional_id",
                "prestacion_id",
                "inicio",
                "fin",
                "sobreturno",
            ],
        )
    else:
        session.commit()
    return _agenda_response(resultado.turno)


@router.post(
    "/turnos/{turno_id}/confirmar", response_model=TurnoAgendaResponse
)
def confirmar_turno(
    turno_id: str,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
) -> TurnoAgendaResponse:
    try:
        turno = _turnos_service(session).confirmar_turno(
            tenant_id=user.tenant_id, turno_id=turno_id, user=_domain_user(user)
        )
    except domain.AgendaError as error:
        raise _error(error) from None
    _commit_audit(
        session,
        user,
        accion="agenda.turno.confirmado",
        recurso="turno",
        recurso_id=turno.id,
        campos=["estado"],
    )
    return _agenda_response(turno)


@router.post("/turnos/{turno_id}/presente", response_model=TurnoAgendaResponse)
def marcar_turno_presente(
    turno_id: str,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
) -> TurnoAgendaResponse:
    try:
        turno = _turnos_service(session).marcar_presente(
            tenant_id=user.tenant_id, turno_id=turno_id, user=_domain_user(user)
        )
    except domain.AgendaError as error:
        raise _error(error) from None
    _commit_audit(
        session,
        user,
        accion="agenda.turno.presente",
        recurso="turno",
        recurso_id=turno.id,
        campos=["estado"],
    )
    return _agenda_response(turno)


@router.post("/turnos/{turno_id}/ausente", response_model=TurnoAgendaResponse)
def marcar_turno_ausente(
    turno_id: str,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
    now_utc: datetime = Depends(deps.get_now),
) -> TurnoAgendaResponse:
    try:
        turno = _turnos_service(session).marcar_ausente(
            tenant_id=user.tenant_id,
            turno_id=turno_id,
            user=_domain_user(user),
            ahora_utc=now_utc,
        )
    except domain.AgendaError as error:
        raise _error(error) from None
    _commit_audit(
        session,
        user,
        accion="agenda.turno.ausente",
        recurso="turno",
        recurso_id=turno.id,
        campos=["estado"],
    )
    return _agenda_response(turno)


@router.post(
    "/turnos/{turno_id}/reprogramar",
    response_model=ReprogramarTurnoResponse,
)
def reprogramar_turno(
    turno_id: str,
    payload: TurnoReprogramarRequest,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
    now_utc: datetime = Depends(deps.get_now),
) -> ReprogramarTurnoResponse:
    try:
        anterior, nuevo = _turnos_service(session).reprogramar_turno(
            tenant_id=user.tenant_id,
            turno_id=turno_id,
            user=_domain_user(user),
            request=payload,
            ahora_utc=now_utc,
        )
    except domain.AgendaError as error:
        raise _error(error) from None
    registrar_auditoria(
        session,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        accion="agenda.turno.reprogramado",
        recurso="turno",
        recurso_id=anterior.id,
        campos=["estado"],
    )
    registrar_auditoria(
        session,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        accion="agenda.turno.creado_por_reprogramacion",
        recurso="turno",
        recurso_id=nuevo.id,
        campos=["paciente_id", "profesional_id", "prestacion_id", "inicio", "fin"],
    )
    session.commit()
    return ReprogramarTurnoResponse(
        turno_anterior=_agenda_response(anterior),
        turno_nuevo=_agenda_response(nuevo),
    )


@router.get("/agenda/dia", response_model=list[TurnoAgendaResponse])
def consultar_agenda_dia(
    fecha: date,
    profesional_id: str | None = None,
    user: AuthUser = Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
) -> list[TurnoAgendaResponse]:
    return _listar_agenda(
        session, user, fecha, fecha + timedelta(days=1), profesional_id
    )


@router.get("/agenda/semana", response_model=list[TurnoAgendaResponse])
def consultar_agenda_semana(
    fecha: date,
    profesional_id: str | None = None,
    user: AuthUser = Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
) -> list[TurnoAgendaResponse]:
    inicio_semana = fecha - timedelta(days=fecha.weekday())
    return _listar_agenda(
        session,
        user,
        inicio_semana,
        inicio_semana + timedelta(days=7),
        profesional_id,
    )


@router.get("/agenda/disponibilidad", response_model=list[datetime])
def consultar_disponibilidad_agenda(
    profesional_id: str,
    prestacion_id: str,
    desde: datetime,
    hasta: datetime,
    user: AuthUser = Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
    now_utc: datetime = Depends(deps.get_now),
) -> list[datetime]:
    if (
        desde.tzinfo is None
        or desde.utcoffset() is None
        or hasta.tzinfo is None
        or hasta.utcoffset() is None
        or hasta <= desde
        or hasta - desde > timedelta(days=31)
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "RN-GL-02",
                "message": "El período debe incluir zona horaria, ser válido y no superar 31 días.",
            },
        )
    solo_odontologo = (
        "odontologo" in user.roles
        and not {"recepcion", "dueno"}.intersection(user.roles)
    )
    profesional = ProfesionalRepository(session).get_by_id(
        user.tenant_id, profesional_id
    )
    if profesional is None or (
        solo_odontologo and profesional.usuario_id != user.id
    ):
        raise HTTPException(
            status_code=404,
            detail={"code": "RN-AU-01", "message": "Profesional no encontrado."},
        )
    try:
        return candidatos_disponibles(
            session,
            tenant_id=user.tenant_id,
            profesional_id=profesional_id,
            prestacion_id=prestacion_id,
            desde=desde,
            hasta=hasta,
            ahora_utc=now_utc,
        )
    except LookupError:
        raise HTTPException(
            status_code=404,
            detail={"code": "RN-AU-01", "message": "Profesional o prestación no disponible."},
        ) from None
    except ValueError:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "RN-GL-02",
                "message": "No se pudo calcular la disponibilidad del consultorio.",
            },
        ) from None


@router.get("/turnos/{turno_id}", response_model=TurnoAgendaResponse)
def obtener_turno(
    turno_id: str,
    user: AuthUser = Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
) -> TurnoAgendaResponse:
    turno = TurnoRepository(session).get_by_id(user.tenant_id, turno_id)
    solo_odontologo = (
        "odontologo" in user.roles
        and not {"recepcion", "dueno"}.intersection(user.roles)
    )
    if turno is None or (
        solo_odontologo and turno.profesional_usuario_id != user.id
    ):
        raise HTTPException(
            status_code=404,
            detail={"code": "RN-AU-01", "message": "Turno no encontrado."},
        )
    return _agenda_response(turno)


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
    estado_anterior = fila.estado
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
    # C-12 / RN-CO-03: devolución de la seña según política configurada.
    if estado_anterior != resultado.estado and fila.senia_id:
        from app.modules.cobros.senias_service import SeniaService

        SeniaService(session).aplicar_politica_cancelacion(fila)
    # C-10: disparar oferta de lista de espera si el turno se cancelo en termino.
    if estado_anterior != resultado.estado and resultado.estado == "cancelado":
        from app.modules.lista_espera.service import Hueco, ListaEsperaService

        hueco = Hueco(
            profesional_id=fila.profesional_id,
            inicio=fila.inicio,
            fin=fila.fin,
            prestacion_id=fila.prestacion_id,
        )
        svc_le = ListaEsperaService(session, now_utc)
        svc_le.ofrecer_por_hueco(user.tenant_id, hueco, now_utc)
    if estado_anterior != resultado.estado:
        _commit_audit(
            session,
            user,
            accion="agenda.turno.cancelado",
            recurso="turno",
            recurso_id=fila.id,
            campos=["estado", "cancelled_by", "cancelled_at", "motivo"],
        )
    else:
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
    _commit_audit(
        session,
        user,
        accion="agenda.profesional.creado",
        recurso="profesional",
        recurso_id=item.id,
        campos=["nombre", "usuario_id", "color_agenda", "activo"],
    )
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


@router.get(
    "/profesionales/{profesional_id}/horarios",
    response_model=HorariosSemanaResponse,
)
def listar_horarios_profesional(
    profesional_id: str,
    user: AuthUser = Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
) -> HorariosSemanaResponse:
    _require_profesional(session, user.tenant_id, profesional_id)
    return _horarios_response(session, user.tenant_id, profesional_id)


@router.put(
    "/profesionales/{profesional_id}/horarios",
    response_model=HorariosSemanaResponse,
)
def reemplazar_horarios_profesional(
    profesional_id: str,
    payload: HorariosSemanaUpdate,
    user: AuthUser = Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
) -> HorariosSemanaResponse:
    _require_profesional(session, user.tenant_id, profesional_id)
    _validate_horarios(payload.horarios)
    current = session.execute(
        select(HorarioProfesionalModel)
        .where(
            HorarioProfesionalModel.tenant_id == user.tenant_id,
            HorarioProfesionalModel.profesional_id == profesional_id,
        )
        .order_by(
            HorarioProfesionalModel.dia_semana,
            HorarioProfesionalModel.hora_inicio,
        )
    ).scalars().all()
    current_values = [
        (item.dia_semana, item.hora_inicio, item.hora_fin) for item in current
    ]
    new_values = sorted(
        (item.dia_semana, item.inicio, item.fin) for item in payload.horarios
    )
    if current_values != new_values:
        for item in current:
            session.delete(item)
        session.flush()
        session.add_all(
            [
                HorarioProfesionalModel(
                    tenant_id=user.tenant_id,
                    profesional_id=profesional_id,
                    dia_semana=item.dia_semana,
                    hora_inicio=item.inicio,
                    hora_fin=item.fin,
                )
                for item in payload.horarios
            ]
        )
        session.flush()
        _commit_audit(
            session,
            user,
            accion="agenda.horario_profesional.actualizado",
            recurso="profesional",
            recurso_id=profesional_id,
            campos=["horarios"],
        )
    else:
        session.commit()
    return _horarios_response(session, user.tenant_id, profesional_id)


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
    cambios: list[str] = []
    valores = {
        "nombre": payload.nombre.strip(),
        "usuario_id": payload.usuario_id.strip() if payload.usuario_id else None,
        "color_agenda": payload.color_agenda.strip() if payload.color_agenda else None,
        "activo": payload.activo,
    }
    for campo, valor in valores.items():
        if getattr(item, campo) != valor:
            setattr(item, campo, valor)
            cambios.append(campo)
    if cambios:
        _commit_audit(
            session,
            user,
            accion="agenda.profesional.actualizado",
            recurso="profesional",
            recurso_id=item.id,
            campos=cambios,
        )
    else:
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
    _commit_audit(
        session,
        user,
        accion="agenda.profesional.eliminado",
        recurso="profesional",
        recurso_id=item.id,
        campos=["eliminado"],
    )


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
        senia_requerida=payload.senia_requerida,
        senia_monto_cents=payload.senia_monto_cents,
    )
    PrestacionRepository(session).create(item)
    _commit_audit(
        session,
        user,
        accion="agenda.prestacion.creada",
        recurso="prestacion",
        recurso_id=item.id,
        campos=["nombre", "duracion_min", "precio_ref", "activa", "senia_requerida", "senia_monto_cents"],
    )
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
    cambios: list[str] = []
    valores = {
        "nombre": payload.nombre.strip(),
        "duracion_min": payload.duracion_min,
        "precio_ref": payload.precio_ref,
        "activa": payload.activa,
        "senia_requerida": payload.senia_requerida,
        "senia_monto_cents": payload.senia_monto_cents,
    }
    for campo, valor in valores.items():
        if getattr(item, campo) != valor:
            setattr(item, campo, valor)
            cambios.append(campo)
    if cambios:
        _commit_audit(
            session,
            user,
            accion="agenda.prestacion.actualizada",
            recurso="prestacion",
            recurso_id=item.id,
            campos=cambios,
        )
    else:
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
    _commit_audit(
        session,
        user,
        accion="agenda.prestacion.eliminada",
        recurso="prestacion",
        recurso_id=item.id,
        campos=["eliminado"],
    )


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
    inicio_utc, fin_utc = _bloqueo_intervalo_utc(payload.inicio, payload.fin)
    _require_profesional(session, user.tenant_id, payload.profesional_id)
    item = BloqueoModel(
        tenant_id=user.tenant_id,
        profesional_id=payload.profesional_id,
        inicio=inicio_utc,
        fin=fin_utc,
        motivo=payload.motivo.strip() if payload.motivo else None,
    )
    BloqueoRepository(session).create(item)
    _commit_audit(
        session,
        user,
        accion="agenda.bloqueo.creado",
        recurso="bloqueo",
        recurso_id=item.id,
        campos=["profesional_id", "inicio", "fin", "motivo"],
    )
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
    inicio_utc, fin_utc = _bloqueo_intervalo_utc(payload.inicio, payload.fin)
    _require_profesional(session, user.tenant_id, payload.profesional_id)
    cambios: list[str] = []
    valores = {
        "profesional_id": payload.profesional_id,
        "inicio": inicio_utc,
        "fin": fin_utc,
        "motivo": payload.motivo.strip() if payload.motivo else None,
    }
    for campo, valor in valores.items():
        if getattr(item, campo) != valor:
            setattr(item, campo, valor)
            cambios.append(campo)
    if cambios:
        _commit_audit(
            session,
            user,
            accion="agenda.bloqueo.actualizado",
            recurso="bloqueo",
            recurso_id=item.id,
            campos=cambios,
        )
    else:
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
    _commit_audit(
        session,
        user,
        accion="agenda.bloqueo.eliminado",
        recurso="bloqueo",
        recurso_id=item.id,
        campos=["eliminado"],
    )


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
            recordatorio_1_hs=48,
            recordatorio_2_hs=24,
            whatsapp_costo_centavos=0,
            politica_devolucion_senia="devuelve_100",
        )
    return ConfigResponse(
        antelacion_cancel_hs=cfg.antelacion_cancel_hs,
        antelacion_reserva_hs=cfg.antelacion_reserva_hs,
        recordatorio_t_48h=cfg.recordatorio_t_48h,
        recordatorio_t_24h=cfg.recordatorio_t_24h,
        recordatorio_1_hs=cfg.recordatorio_1_hs,
        recordatorio_2_hs=cfg.recordatorio_2_hs,
        whatsapp_costo_centavos=cfg.whatsapp_costo_centavos,
        politica_devolucion_senia=cfg.politica_devolucion_senia,
    )


@router.put("/config", response_model=ConfigResponse)
def put_config(
    payload: ConfigUpdateRequest,
    user: AuthUser = Depends(require_roles("dueno")),
    session: Session = Depends(deps.get_session),
) -> ConfigResponse:
    existing = ConfigRepository(session).get(user.tenant_id)
    cfg = ConfigRepository(session).upsert(
        user.tenant_id,
        payload.antelacion_cancel_hs,
        payload.antelacion_reserva_hs,
        payload.recordatorio_t_48h,
        payload.recordatorio_t_24h,
        payload.recordatorio_1_hs,
        payload.recordatorio_2_hs,
        payload.whatsapp_costo_centavos,
        politica_devolucion_senia=payload.politica_devolucion_senia,
    )
    cambios: list[str] = []
    for campo in (
        "antelacion_cancel_hs",
        "antelacion_reserva_hs",
        "recordatorio_t_48h",
        "recordatorio_t_24h",
    ):
        before = getattr(existing, campo) if existing is not None else None
        if before != getattr(cfg, campo):
            cambios.append(campo)
    if cambios:
        _commit_audit(
            session,
            user,
            accion="agenda.configuracion.actualizada",
            recurso="config",
            recurso_id=user.tenant_id,
            campos=cambios,
        )
    else:
        session.commit()
    return ConfigResponse(
        antelacion_cancel_hs=cfg.antelacion_cancel_hs,
        antelacion_reserva_hs=cfg.antelacion_reserva_hs,
        recordatorio_t_48h=cfg.recordatorio_t_48h,
        recordatorio_t_24h=cfg.recordatorio_t_24h,
        recordatorio_1_hs=cfg.recordatorio_1_hs,
        recordatorio_2_hs=cfg.recordatorio_2_hs,
        whatsapp_costo_centavos=cfg.whatsapp_costo_centavos,
        politica_devolucion_senia=cfg.politica_devolucion_senia,
    )

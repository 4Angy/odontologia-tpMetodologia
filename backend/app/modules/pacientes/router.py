from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app import deps
from app.core.audit import listar_auditoria
from app.core.security import require_auth, require_roles
from app.modules.pacientes.attachment_storage import (
    AttachmentStorage,
    AttachmentStorageError,
    PRESIGNED_URL_TTL_SECONDS,
    get_attachment_storage,
)
from app.modules.pacientes.schemas import (
    AdjuntoDownloadResponse,
    AdjuntoResponse,
    AuditoriaResponse,
    EvolucionCreate,
    EvolucionResponse,
    ImportacionResponse,
    OptInResponse,
    OptInUpsert,
    PacienteCreate,
    PacienteResponse,
    PacienteUpdate,
    PresupuestoCreate,
    PresupuestoEstadoUpdate,
    PresupuestoItemResponse,
    PresupuestoResponse,
    PresupuestoUpdate,
)
from app.modules.pacientes.service import (
    MAX_ADJUNTO_BYTES,
    MAX_IMPORT_BYTES,
    PacienteService,
)

router = APIRouter(prefix="/pacientes", tags=["pacientes"])
export_router = APIRouter(tags=["exportacion"])
audit_router = APIRouter(tags=["auditoria"])


def _as_response(paciente, saldo: int) -> PacienteResponse:
    return PacienteResponse(
        id=paciente.id,
        tenant_id=paciente.tenant_id,
        nombre=paciente.nombre,
        apellido=paciente.apellido,
        dni=paciente.dni,
        telefono=paciente.telefono,
        email=paciente.email,
        fecha_nac=paciente.fecha_nac,
        notas=paciente.notas,
        saldo=saldo,
        created_at=paciente.created_at,
        updated_at=paciente.updated_at,
    )


def _as_optin_response(optin) -> OptInResponse:
    return OptInResponse(
        id=optin.id,
        paciente_id=optin.paciente_id,
        tenant_id=optin.tenant_id,
        canal=optin.canal,
        estado=optin.estado,
        updated_at=optin.updated_at,
        consentimiento_version=optin.consentimiento_version,
        consentimiento_actor_id=optin.consentimiento_actor_id,
        consentimiento_at=optin.consentimiento_at,
    )


def _as_evolucion_response(evolucion) -> EvolucionResponse:
    return EvolucionResponse(
        id=evolucion.id,
        paciente_id=evolucion.paciente_id,
        tenant_id=evolucion.tenant_id,
        profesional_id=evolucion.profesional_id,
        fecha=evolucion.fecha,
        motivo=evolucion.motivo,
        detalle=evolucion.detalle,
        pieza_fdi_slot=evolucion.pieza_fdi_slot,
        pieza_fdi_numero=evolucion.pieza_fdi_numero,
        odontograma_ref=evolucion.odontograma_ref,
        firma_simple=evolucion.firma_simple,
        firmado_at=evolucion.firmado_at,
        alcance_firma="La firma simple no constituye firma digital según la Ley 25.506.",
        updated_at=evolucion.updated_at,
    )


def _as_adjunto_response(adjunto) -> AdjuntoResponse:
    return AdjuntoResponse(
        id=adjunto.id,
        paciente_id=adjunto.paciente_id,
        tenant_id=adjunto.tenant_id,
        nombre=adjunto.nombre,
        tipo=adjunto.tipo,
        tamano_bytes=adjunto.tamano_bytes,
        created_at=adjunto.created_at,
        updated_at=adjunto.updated_at,
    )


def _as_presupuesto_item_response(item) -> PresupuestoItemResponse:
    return PresupuestoItemResponse(
        id=item.id,
        presupuesto_id=item.presupuesto_id,
        descripcion=item.descripcion,
        monto_cents=item.monto_cents,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _as_presupuesto_response(presupuesto) -> PresupuestoResponse:
    return PresupuestoResponse(
        id=presupuesto.id,
        paciente_id=presupuesto.paciente_id,
        tenant_id=presupuesto.tenant_id,
        total_cents=presupuesto.total_cents,
        estado=presupuesto.estado,
        notas=presupuesto.notas,
        items=[_as_presupuesto_item_response(item) for item in (presupuesto.items or [])],
        created_at=presupuesto.created_at,
        updated_at=presupuesto.updated_at,
    )


@router.get("", response_model=list[PacienteResponse])
def listar_pacientes(
    q: str | None = Query(default=None, alias="q"),
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    servicio = PacienteService(session)
    return [
        _as_response(p, servicio.saldo_derivado(user.tenant_id, p.id))
        for p in servicio.listar(user.tenant_id, q)
    ]


@router.post("", response_model=PacienteResponse, status_code=201)
def crear_paciente(
    payload: PacienteCreate,
    user=Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
):
    paciente = PacienteService(session).crear(user.tenant_id, user.id, payload)
    servicio = PacienteService(session)
    return _as_response(paciente, servicio.saldo_derivado(user.tenant_id, paciente.id))


@router.get("/{paciente_id}", response_model=PacienteResponse)
def obtener_paciente(
    paciente_id: str,
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    paciente = PacienteService(session).obtener(user.tenant_id, paciente_id)
    servicio = PacienteService(session)
    return _as_response(paciente, servicio.saldo_derivado(user.tenant_id, paciente.id))


@router.put("/{paciente_id}", response_model=PacienteResponse)
def actualizar_paciente(
    paciente_id: str,
    payload: PacienteUpdate,
    user=Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
):
    paciente = PacienteService(session).actualizar(
        user.tenant_id, user.id, paciente_id, payload
    )
    servicio = PacienteService(session)
    return _as_response(paciente, servicio.saldo_derivado(user.tenant_id, paciente.id))


@router.delete("/{paciente_id}", status_code=204)
def borrar_paciente(
    paciente_id: str,
    user=Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
):
    PacienteService(session).borrar(user.tenant_id, user.id, paciente_id)
    return Response(status_code=204)


@router.get("/{paciente_id}/optins", response_model=list[OptInResponse])
def listar_optins(
    paciente_id: str,
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    optins = PacienteService(session).listar_optins(user.tenant_id, paciente_id)
    return [_as_optin_response(o) for o in optins]


@router.put("/{paciente_id}/optins", response_model=OptInResponse)
def upsert_optin(
    paciente_id: str,
    payload: OptInUpsert,
    user=Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
):
    optin = PacienteService(session).upsert_optin(
        user.tenant_id, user.id, paciente_id, payload
    )
    return _as_optin_response(optin)


@router.get("/{paciente_id}/evoluciones", response_model=list[EvolucionResponse])
def listar_evoluciones(
    paciente_id: str,
    user=Depends(require_roles("odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    evoluciones = PacienteService(session).listar_evoluciones(
        user.tenant_id, paciente_id, user.id, user.roles
    )
    return [_as_evolucion_response(e) for e in evoluciones]


@router.post("/{paciente_id}/evoluciones", response_model=EvolucionResponse, status_code=201)
def crear_evolucion(
    paciente_id: str,
    payload: EvolucionCreate,
    user=Depends(require_roles("odontologo")),
    session: Session = Depends(deps.get_session),
):
    evolucion = PacienteService(session).crear_evolucion(
        user.tenant_id, paciente_id, user.id, payload
    )
    return _as_evolucion_response(evolucion)


@router.put(
    "/{paciente_id}/evoluciones/{evolucion_id}",
    response_model=EvolucionResponse,
)
def actualizar_evolucion(
    paciente_id: str,
    evolucion_id: str,
    payload: EvolucionCreate,
    user=Depends(require_roles("odontologo")),
    session: Session = Depends(deps.get_session),
):
    evolucion = PacienteService(session).actualizar_evolucion(
        user.tenant_id, paciente_id, evolucion_id, user.id, payload
    )
    return _as_evolucion_response(evolucion)


@router.post("/{paciente_id}/adjuntos", response_model=AdjuntoResponse, status_code=201)
async def crear_adjunto(
    paciente_id: str,
    request: Request,
    user=Depends(require_roles("odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
    storage: AttachmentStorage = Depends(get_attachment_storage),
):
    nombre = request.headers.get("x-filename", "")
    tipo = request.headers.get("content-type", "").split(";", maxsplit=1)[0].strip().lower()
    contenido = bytearray()
    async for bloque in request.stream():
        if len(contenido) + len(bloque) > MAX_ADJUNTO_BYTES:
            raise HTTPException(
                status_code=413,
                detail={
                    "code": "RN-PA-03",
                    "message": "El adjunto no puede superar 10 MiB.",
                },
            )
        contenido.extend(bloque)
    adjunto = PacienteService(session).crear_adjunto(
        user.tenant_id,
        paciente_id,
        user.id,
        nombre,
        tipo,
        bytes(contenido),
        storage,
    )
    return _as_adjunto_response(adjunto)


@router.get(
    "/{paciente_id}/adjuntos",
    response_model=list[AdjuntoResponse],
)
def listar_adjuntos(
    paciente_id: str,
    user=Depends(require_roles("odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    adjuntos = PacienteService(session).listar_adjuntos(user.tenant_id, paciente_id)
    return [_as_adjunto_response(adjunto) for adjunto in adjuntos]


@router.get(
    "/{paciente_id}/adjuntos/{adjunto_id}/descarga",
    response_model=AdjuntoDownloadResponse,
)
def descargar_adjunto(
    paciente_id: str,
    adjunto_id: str,
    user=Depends(require_roles("odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
    storage: AttachmentStorage = Depends(get_attachment_storage),
):
    adjunto = PacienteService(session).obtener_adjunto(
        user.tenant_id, paciente_id, adjunto_id
    )
    if adjunto.storage_key is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "RN-AU-01", "message": "Adjunto no encontrado."},
        )
    try:
        url = storage.presign_get(adjunto.storage_key, adjunto.nombre)
    except AttachmentStorageError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "RN-PA-03",
                "message": "No se pudo generar el enlace temporal del adjunto.",
            },
        ) from exc
    return AdjuntoDownloadResponse(
        url=url, expires_in_seconds=PRESIGNED_URL_TTL_SECONDS
    )


@router.get("/{paciente_id}/presupuestos", response_model=list[PresupuestoResponse])
def listar_presupuestos(
    paciente_id: str,
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    presupuestos = PacienteService(session).listar_presupuestos(user.tenant_id, paciente_id)
    return [_as_presupuesto_response(p) for p in presupuestos]


@router.post("/{paciente_id}/presupuestos", response_model=PresupuestoResponse, status_code=201)
def crear_presupuesto(
    paciente_id: str,
    payload: PresupuestoCreate,
    user=Depends(require_roles("odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    presupuesto = PacienteService(session).crear_presupuesto(
        user.tenant_id, paciente_id, user.id, payload
    )
    return _as_presupuesto_response(presupuesto)


@router.put(
    "/{paciente_id}/presupuestos/{presupuesto_id}",
    response_model=PresupuestoResponse,
)
def actualizar_presupuesto(
    paciente_id: str,
    presupuesto_id: str,
    payload: PresupuestoUpdate,
    user=Depends(require_roles("odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    presupuesto = PacienteService(session).actualizar_presupuesto(
        user.tenant_id, paciente_id, presupuesto_id, user.id, payload
    )
    return _as_presupuesto_response(presupuesto)


@router.patch(
    "/{paciente_id}/presupuestos/{presupuesto_id}/estado",
    response_model=PresupuestoResponse,
)
def actualizar_estado_presupuesto(
    paciente_id: str,
    presupuesto_id: str,
    payload: PresupuestoEstadoUpdate,
    user=Depends(require_roles("odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    presupuesto = PacienteService(session).actualizar_estado_presupuesto(
        user.tenant_id, paciente_id, presupuesto_id, user.id, payload
    )
    return _as_presupuesto_response(presupuesto)


@router.delete(
    "/{paciente_id}/presupuestos/{presupuesto_id}",
    status_code=204,
)
def eliminar_presupuesto(
    paciente_id: str,
    presupuesto_id: str,
    user=Depends(require_roles("odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    PacienteService(session).eliminar_presupuesto(
        user.tenant_id, paciente_id, presupuesto_id, user.id
    )
    return Response(status_code=204)


@router.post("/import-csv", response_model=ImportacionResponse)
async def importar_csv(
    request: Request,
    user=Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
):
    contenido = bytearray()
    async for bloque in request.stream():
        if len(contenido) + len(bloque) > MAX_IMPORT_BYTES:
            raise HTTPException(
                status_code=413,
                detail={"code": "RN-PA-01", "message": "El CSV supera el límite de 5 MiB."},
            )
        contenido.extend(bloque)
    return PacienteService(session).importar_csv(
        user.tenant_id, user.id, bytes(contenido)
    )


@export_router.get("/export/pacientes.csv")
@export_router.get("/export/pacientes")
def exportar_csv(
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    csv_data = PacienteService(session).exportar_csv(user.tenant_id)
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="pacientes.csv"'},
    )


@audit_router.get("/auditoria", response_model=list[AuditoriaResponse])
def consultar_auditoria(
    limit: int = Query(default=50, ge=1, le=100),
    user=Depends(require_roles("dueno")),
    session: Session = Depends(deps.get_session),
):
    return listar_auditoria(session, user.tenant_id, limit)

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app import deps
from app.core.security import require_auth, require_roles
from app.modules.pacientes.schemas import (
    AdjuntoCreate,
    AdjuntoResponse,
    EvolucionCreate,
    EvolucionResponse,
    OptInResponse,
    OptInUpsert,
    PacienteCreate,
    PacienteResponse,
    PacienteUpdate,
    PresupuestoCreate,
    PresupuestoItemResponse,
    PresupuestoResponse,
)
from app.modules.pacientes.service import PacienteService

router = APIRouter(prefix="/pacientes", tags=["pacientes"])
export_router = APIRouter(tags=["exportacion"])


def _as_response(paciente) -> PacienteResponse:
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
        saldo=paciente.saldo,
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
    )


def _as_evolucion_response(evolucion) -> EvolucionResponse:
    return EvolucionResponse(
        id=evolucion.id,
        paciente_id=evolucion.paciente_id,
        tenant_id=evolucion.tenant_id,
        motivo=evolucion.motivo,
        detalle=evolucion.detalle,
        firma_simple=evolucion.firma_simple,
        firma_timestamp=evolucion.firma_timestamp,
        created_at=evolucion.created_at,
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
        url=adjunto.url,
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
    return [_as_response(p) for p in PacienteService(session).listar(user.tenant_id, q)]


@router.post("", response_model=PacienteResponse, status_code=201)
def crear_paciente(
    payload: PacienteCreate,
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    paciente = PacienteService(session).crear(user.tenant_id, payload)
    return _as_response(paciente)


@router.get("/{paciente_id}", response_model=PacienteResponse)
def obtener_paciente(
    paciente_id: str,
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    paciente = PacienteService(session).obtener(user.tenant_id, paciente_id)
    return _as_response(paciente)


@router.put("/{paciente_id}", response_model=PacienteResponse)
def actualizar_paciente(
    paciente_id: str,
    payload: PacienteUpdate,
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    paciente = PacienteService(session).actualizar(user.tenant_id, paciente_id, payload)
    return _as_response(paciente)


@router.delete("/{paciente_id}", status_code=204)
def borrar_paciente(
    paciente_id: str,
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    PacienteService(session).borrar(user.tenant_id, paciente_id)
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
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    optin = PacienteService(session).upsert_optin(user.tenant_id, paciente_id, payload)
    return _as_optin_response(optin)


@router.get("/{paciente_id}/evoluciones", response_model=list[EvolucionResponse])
def listar_evoluciones(
    paciente_id: str,
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    evoluciones = PacienteService(session).listar_evoluciones(user.tenant_id, paciente_id)
    return [_as_evolucion_response(e) for e in evoluciones]


@router.post("/{paciente_id}/evoluciones", response_model=EvolucionResponse, status_code=201)
def crear_evolucion(
    paciente_id: str,
    payload: EvolucionCreate,
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    evolucion = PacienteService(session).crear_evolucion(user.tenant_id, paciente_id, payload)
    return _as_evolucion_response(evolucion)


@router.post("/{paciente_id}/adjuntos", response_model=AdjuntoResponse, status_code=201)
def crear_adjunto(
    paciente_id: str,
    payload: AdjuntoCreate,
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    adjunto = PacienteService(session).crear_adjunto(user.tenant_id, paciente_id, payload)
    return _as_adjunto_response(adjunto)


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
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    presupuesto = PacienteService(session).crear_presupuesto(user.tenant_id, paciente_id, payload)
    return _as_presupuesto_response(presupuesto)


@router.post("/import-csv")
def importar_csv(
    texto: str = Body(..., embed=False),
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    return PacienteService(session).importar_csv(user.tenant_id, texto)


@export_router.get("/export/{recurso}.csv")
@export_router.get("/export/{recurso}")
def exportar_csv(
    recurso: str,
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    recurso_base = recurso.removesuffix(".csv")
    csv_data = PacienteService(session).exportar_csv(user.tenant_id, recurso_base)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{recurso_base}.csv"'},
    )

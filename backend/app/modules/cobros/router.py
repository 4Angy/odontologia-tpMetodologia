from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app import deps
from app.core.security import require_auth, require_roles
from app.modules.cobros.schemas import (
    AjusteCreate,
    CierreCajaCreate,
    CierreCajaResponse,
    CobroCreate,
    CobroResponse,
    CobroUpdate,
    DeudaResponse,
    SeniaResponse,
)
from app.modules.cobros.service import CobroService
from app.modules.cobros.senias_service import SeniaService

router = APIRouter(tags=["cobros"])


def _as_cobro_response(cobro) -> CobroResponse:
    return CobroResponse(
        id=cobro.id,
        tenant_id=cobro.tenant_id,
        paciente_id=cobro.paciente_id,
        turno_id=cobro.turno_id,
        monto_cents=cobro.monto_cents,
        medio=cobro.medio,
        concepto=cobro.concepto,
        usuario_id=cobro.usuario_id,
        fecha=cobro.fecha,
        created_at=cobro.created_at,
        updated_at=cobro.updated_at,
    )


def _as_cierre_response(cierre, cobros=None) -> CierreCajaResponse:
    return CierreCajaResponse(
        id=cierre.id,
        tenant_id=cierre.tenant_id,
        fecha=cierre.fecha,
        total_efectivo_cents=cierre.total_efectivo_cents,
        total_transferencia_cents=cierre.total_transferencia_cents,
        total_mp_cents=cierre.total_mp_cents,
        total_otro_cents=cierre.total_otro_cents,
        observaciones=cierre.observaciones,
        usuario_id=cierre.usuario_id,
        cobros=[_as_cobro_response(c) for c in (cobros or [])],
        created_at=cierre.created_at,
        updated_at=cierre.updated_at,
    )


@router.get("/cobros", response_model=list[CobroResponse])
def listar_cobros(
    paciente_id: str | None = Query(default=None),
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    servicio = CobroService(session)
    cobros = servicio.listar(user.tenant_id, paciente_id=paciente_id)
    return [_as_cobro_response(c) for c in cobros]


@router.post("/cobros", response_model=CobroResponse, status_code=201)
def crear_cobro(
    payload: CobroCreate,
    user=Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
):
    cobro = CobroService(session).crear(user.tenant_id, user.id, payload)
    return _as_cobro_response(cobro)


@router.get("/cobros/{cobro_id}", response_model=CobroResponse)
def obtener_cobro(
    cobro_id: str,
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    cobro = CobroService(session).obtener(user.tenant_id, cobro_id)
    return _as_cobro_response(cobro)


@router.put("/cobros/{cobro_id}", response_model=CobroResponse)
def actualizar_cobro(
    cobro_id: str,
    payload: CobroUpdate,
    user=Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
):
    cobro = CobroService(session).actualizar(
        user.tenant_id, user.id, cobro_id, payload
    )
    return _as_cobro_response(cobro)


@router.delete("/cobros/{cobro_id}", status_code=204)
def borrar_cobro(
    cobro_id: str,
    user=Depends(require_roles("recepcion", "dueno")),
    session: Session = Depends(deps.get_session),
):
    CobroService(session).borrar(user.tenant_id, user.id, cobro_id)
    return Response(status_code=204)


@router.get("/deudas", response_model=list[DeudaResponse])
def listar_deudas(
    orden: Literal["antiguedad", "monto"] = Query(default="antiguedad"),
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    return CobroService(session).listar_deudas(user.tenant_id, orden=orden)


@router.post("/caja/cierre-dia", response_model=CierreCajaResponse, status_code=201)
def cerrar_caja(
    payload: CierreCajaCreate,
    user=Depends(require_roles("dueno")),
    session: Session = Depends(deps.get_session),
):
    cierre = CobroService(session).cierre_dia(user.tenant_id, user.id, payload)
    # incluir cobros del día para conciliación
    from datetime import timedelta

    inicio = cierre.fecha
    fin = inicio + timedelta(days=1)
    cobros = CobroService(session).listar(user.tenant_id)
    cobros_dia = [c for c in cobros if inicio <= c.fecha < fin]
    return _as_cierre_response(cierre, cobros_dia)


@router.get("/caja/cierre-dia", response_model=CierreCajaResponse)
def obtener_cierre(
    fecha: datetime | None = Query(default=None),
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    f = fecha or datetime.now(timezone.utc)
    cierre = CobroService(session).obtener_cierre(user.tenant_id, f)
    from datetime import timedelta

    inicio = cierre.fecha
    fin = inicio + timedelta(days=1)
    cobros = [c for c in CobroService(session).listar(user.tenant_id) if inicio <= c.fecha < fin]
    return _as_cierre_response(cierre, cobros)


@router.post("/caja/ajuste", status_code=204)
def ajustar_caja(
    payload: AjusteCreate,
    user=Depends(require_roles("dueno")),
    session: Session = Depends(deps.get_session),
):
    CobroService(session).ajuste(user.tenant_id, user.id, payload)
    return Response(status_code=204)


# ---------- Señas Mercado Pago (C-12) ----------


def _as_senia_response(senia) -> SeniaResponse:
    return SeniaResponse(
        id=senia.id,
        tenant_id=senia.tenant_id,
        turno_id=senia.turno_id,
        paciente_id=senia.paciente_id,
        monto_cents=senia.monto_cents,
        monto_afavor_cents=senia.monto_afavor_cents,
        estado=senia.estado,
        mp_preference_id=senia.mp_preference_id,
        mp_payment_id=senia.mp_payment_id,
        checkout_url=None,
        acreditada_at=senia.acreditada_at,
        created_at=senia.created_at,
        updated_at=senia.updated_at,
    )


@router.get("/senias", response_model=list[SeniaResponse])
def listar_senias(
    turno_id: str | None = Query(default=None),
    paciente_id: str | None = Query(default=None),
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    servicio = SeniaService(session)
    if turno_id is not None:
        lista = [servicio.get_by_turno(user.tenant_id, turno_id)]
        if lista[0] is None:
            return []
    elif paciente_id is not None:
        from sqlalchemy import select

        from app.modules.cobros.models import SeniaModel

        lista = list(
            session.execute(
                select(SeniaModel).where(
                    SeniaModel.tenant_id == user.tenant_id,
                    SeniaModel.paciente_id == paciente_id,
                    SeniaModel.deleted_at.is_(None),
                )
            ).scalars()
        )
    else:
        return []
    return [_as_senia_response(s) for s in lista if s is not None]


@router.get("/senias/{senia_id}", response_model=SeniaResponse)
def obtener_senia(
    senia_id: str,
    user=Depends(require_roles("recepcion", "odontologo", "dueno")),
    session: Session = Depends(deps.get_session),
):
    senia = SeniaService(session).get(user.tenant_id, senia_id)
    if senia is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "RN-AU-01", "message": "Seña no encontrada."},
        )
    return _as_senia_response(senia)
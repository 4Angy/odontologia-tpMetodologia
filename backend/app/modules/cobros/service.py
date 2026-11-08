from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.audit import registrar_auditoria
from app.modules.agenda.models import TenantModel
from app.modules.cobros.models import CierreCajaModel, CobroModel
from app.modules.cobros.repository import CierreCajaRepository, CobroRepository
from app.modules.cobros.schemas import (
    AjusteCreate,
    CierreCajaCreate,
    CobroCreate,
    CobroUpdate,
    DeudaResponse,
)
from app.modules.pacientes.models import PacienteModel, PresupuestoModel

MAX_MONTO_CENTS = 2_147_483_647


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _day_bounds(fecha: datetime) -> tuple[datetime, datetime]:
    inicio = fecha.astimezone(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return inicio, inicio + timedelta(days=1)


class CobroService:
    def __init__(self, session) -> None:
        self.session = session
        self.cobros = CobroRepository(session)
        self.cierres = CierreCajaRepository(session)

    # ---------- Cobro CRUD ----------

    def crear(
        self, tenant_id: str, actor_id: str, payload: CobroCreate
    ) -> CobroModel:
        paciente = self._obtener_paciente(tenant_id, payload.paciente_id)
        fecha = payload.fecha or _utc_now()
        cobro = CobroModel(
            tenant_id=tenant_id,
            paciente_id=paciente.id,
            turno_id=payload.turno_id,
            monto_cents=payload.monto_cents,
            medio=payload.medio,
            concepto=payload.concepto.strip(),
            usuario_id=actor_id,
            fecha=fecha,
        )
        self.cobros.create(cobro)
        registrar_auditoria(
            self.session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="cobro.creado",
            recurso="cobro",
            recurso_id=cobro.id,
            campos=["paciente_id", "turno_id", "monto_cents", "medio", "concepto", "fecha"],
        )
        self.session.commit()
        return cobro

    def obtener(self, tenant_id: str, cobro_id: str) -> CobroModel:
        cobro = self.cobros.get(tenant_id, cobro_id)
        if cobro is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "RN-AU-01", "message": "Cobro no encontrado."},
            )
        return cobro

    def listar(
        self, tenant_id: str, paciente_id: str | None = None
    ) -> list[CobroModel]:
        return self.cobros.list(tenant_id, paciente_id=paciente_id)

    def actualizar(
        self, tenant_id: str, actor_id: str, cobro_id: str, payload: CobroUpdate
    ) -> CobroModel:
        cobro = self.obtener(tenant_id, cobro_id)
        campos: list[str] = []
        if payload.paciente_id is not None and payload.paciente_id != cobro.paciente_id:
            self._obtener_paciente(tenant_id, payload.paciente_id)
            cobro.paciente_id = payload.paciente_id
            campos.append("paciente_id")
        if payload.turno_id is not None and payload.turno_id != cobro.turno_id:
            cobro.turno_id = payload.turno_id
            campos.append("turno_id")
        if payload.monto_cents is not None and payload.monto_cents != cobro.monto_cents:
            cobro.monto_cents = payload.monto_cents
            campos.append("monto_cents")
        if payload.medio is not None and payload.medio != cobro.medio:
            cobro.medio = payload.medio
            campos.append("medio")
        if payload.concepto is not None and payload.concepto.strip() != cobro.concepto:
            cobro.concepto = payload.concepto.strip()
            campos.append("concepto")
        if payload.fecha is not None and payload.fecha != cobro.fecha:
            cobro.fecha = payload.fecha
            campos.append("fecha")
        if campos:
            registrar_auditoria(
                self.session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                accion="cobro.actualizado",
                recurso="cobro",
                recurso_id=cobro.id,
                campos=campos,
            )
            self.session.commit()
        return cobro

    def borrar(self, tenant_id: str, actor_id: str, cobro_id: str) -> None:
        cobro = self.obtener(tenant_id, cobro_id)
        ahora = _utc_now()
        cobro.deleted_at = ahora
        cobro.updated_at = ahora
        registrar_auditoria(
            self.session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="cobro.eliminado",
            recurso="cobro",
            recurso_id=cobro.id,
            campos=["deleted_at"],
        )
        self.session.commit()

    # ---------- Saldo / deudas ----------

    def _pagos_del_paciente(self, tenant_id: str, paciente_id: str) -> int:
        value = self.session.execute(
            select(func.coalesce(func.sum(CobroModel.monto_cents), 0)).where(
                CobroModel.tenant_id == tenant_id,
                CobroModel.paciente_id == paciente_id,
                CobroModel.deleted_at.is_(None),
            )
        ).scalar_one()
        return int(value)

    def saldo_derivado(self, tenant_id: str, paciente_id: str) -> int:
        cargos = self.session.execute(
            select(func.coalesce(func.sum(PresupuestoModel.total_cents), 0)).where(
                PresupuestoModel.tenant_id == tenant_id,
                PresupuestoModel.paciente_id == paciente_id,
                PresupuestoModel.estado.in_(("aprobado", "aceptado")),
                PresupuestoModel.deleted_at.is_(None),
            )
        ).scalar_one()
        return int(cargos) - self._pagos_del_paciente(tenant_id, paciente_id)

    def listar_deudas(
        self, tenant_id: str, orden: Literal["antiguedad", "monto"] = "antiguedad"
    ) -> list[DeudaResponse]:
        pacientes = list(
            self.session.execute(
                select(PacienteModel).where(
                    PacienteModel.tenant_id == tenant_id,
                    PacienteModel.deleted_at.is_(None),
                )
            ).scalars()
        )
        items: list[tuple[PacienteModel, int, datetime]] = []
        for paciente in pacientes:
            saldo = self.saldo_derivado(tenant_id, paciente.id)
            if saldo <= 0:
                continue
            # antigüedad: fecha del cargo más antiguo pendiente
            fecha_cargo = self.session.execute(
                select(func.min(PresupuestoModel.created_at)).where(
                    PresupuestoModel.tenant_id == tenant_id,
                    PresupuestoModel.paciente_id == paciente.id,
                    PresupuestoModel.estado.in_(("aprobado", "aceptado")),
                    PresupuestoModel.deleted_at.is_(None),
                )
            ).scalar_one()
            antiguedad = fecha_cargo or paciente.created_at
            items.append((paciente, saldo, antiguedad))

        if orden == "monto":
            items.sort(key=lambda x: x[1], reverse=True)
        else:
            items.sort(key=lambda x: x[2])

        return [
            DeudaResponse(
                paciente_id=p.id,
                nombre=p.nombre,
                apellido=p.apellido,
                saldo_cents=saldo,
            )
            for p, saldo, _ in items
        ]

    # ---------- Cierre de caja ----------

    def cierre_dia(
        self, tenant_id: str, actor_id: str, payload: CierreCajaCreate
    ) -> CierreCajaModel:
        fecha = payload.fecha or _utc_now()
        existente = self.cierres.get_by_fecha(tenant_id, fecha)
        if existente is not None:
            raise HTTPException(
                status_code=409,
                detail={"code": "RN-CO-04", "message": "La caja de ese día ya está cerrada."},
            )
        inicio, fin = _day_bounds(fecha)
        cobros = self.cobros.list(tenant_id, fecha_desde=inicio, fecha_hasta=fin)
        totales = {
            "efectivo": 0,
            "transferencia": 0,
            "mp": 0,
            "otro": 0,
        }
        for cobro in cobros:
            if cobro.medio in totales:
                totales[cobro.medio] += cobro.monto_cents
        cierre = CierreCajaModel(
            tenant_id=tenant_id,
            fecha=inicio,
            total_efectivo_cents=totales["efectivo"],
            total_transferencia_cents=totales["transferencia"],
            total_mp_cents=totales["mp"],
            total_otro_cents=totales["otro"],
            observaciones=(payload.observaciones.strip() if payload.observaciones else None),
            usuario_id=actor_id,
        )
        self.cierres.create(cierre)
        registrar_auditoria(
            self.session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="caja.cierre_dia",
            recurso="cierre_caja",
            recurso_id=cierre.id,
            campos=["fecha", "totales", "observaciones"],
        )
        self.session.commit()
        return cierre

    def obtener_cierre(self, tenant_id: str, fecha: datetime | None = None) -> CierreCajaModel:
        fecha = fecha or _utc_now()
        cierre = self.cierres.get_by_fecha(tenant_id, fecha)
        if cierre is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "RN-CO-04", "message": "No hay cierre para esa fecha."},
            )
        return cierre

    def ajuste(self, tenant_id: str, actor_id: str, payload: AjusteCreate) -> None:
        cierre = self.session.execute(
            select(CierreCajaModel).where(
                CierreCajaModel.tenant_id == tenant_id,
                CierreCajaModel.id == payload.cierre_id,
                CierreCajaModel.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if cierre is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "RN-CO-04", "message": "Cierre de caja no encontrado."},
            )
        campos = ["nota"]
        if payload.monto_cents is not None:
            campos.append("monto_cents")
        registrar_auditoria(
            self.session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="caja.ajuste",
            recurso="cierre_caja",
            recurso_id=cierre.id,
            campos=campos,
        )
        self.session.commit()

    # ---------- helpers ----------

    def _obtener_paciente(self, tenant_id: str, paciente_id: str):
        from app.modules.pacientes.models import PacienteModel

        paciente = self.session.execute(
            select(PacienteModel).where(
                PacienteModel.tenant_id == tenant_id,
                PacienteModel.id == paciente_id,
                PacienteModel.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if paciente is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "RN-AU-01", "message": "Paciente no encontrado."},
            )
        return paciente


__all__ = ["CobroService"]
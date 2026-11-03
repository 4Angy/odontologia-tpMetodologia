from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import HTTPException

from app.modules.pacientes.models import (
    AdjuntoModel,
    EvolucionModel,
    OptInModel,
    PacienteModel,
    PresupuestoItemModel,
    PresupuestoModel,
)
from app.modules.pacientes.repository import OptInRepository, PacienteRepository
from app.modules.pacientes.schemas import (
    AdjuntoCreate,
    EvolucionCreate,
    OptInUpsert,
    PacienteCreate,
    PacienteUpdate,
    PresupuestoCreate,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _valid_e164(value: str | None) -> bool:
    if value is None:
        return True
    return value.startswith("+") and value[1:].isdigit() and len(value) >= 8 and len(value) <= 16


class PacienteService:
    def __init__(self, session) -> None:
        self.session = session
        self.pacientes = PacienteRepository(session)
        self.optins = OptInRepository(session)

    def listar(self, tenant_id: str, q: str | None = None):
        return self.pacientes.list(tenant_id, q)

    def obtener(self, tenant_id: str, paciente_id: str):
        paciente = self.pacientes.get_by_id(tenant_id, paciente_id)
        if paciente is None:
            raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Paciente no encontrado."})
        return paciente

    def crear(self, tenant_id: str, payload: PacienteCreate) -> PacienteModel:
        if payload.telefono is not None and not _valid_e164(payload.telefono):
            raise HTTPException(
                status_code=422,
                detail={"code": "RN-PA-01", "message": "El telefono debe ser un número E.164 válido."},
            )
        paciente = PacienteModel(
            tenant_id=tenant_id,
            nombre=payload.nombre.strip(),
            apellido=payload.apellido.strip(),
            dni=payload.dni.strip() if payload.dni else None,
            telefono=payload.telefono.strip() if payload.telefono else None,
            email=payload.email.strip() if payload.email else None,
            fecha_nac=payload.fecha_nac,
            notas=payload.notas,
        )
        self.pacientes.create(paciente)
        self.session.commit()
        return paciente

    def actualizar(self, tenant_id: str, paciente_id: str, payload: PacienteUpdate) -> PacienteModel:
        paciente = self.obtener(tenant_id, paciente_id)
        if payload.nombre is not None:
            paciente.nombre = payload.nombre.strip()
        if payload.apellido is not None:
            paciente.apellido = payload.apellido.strip()
        if payload.dni is not None:
            paciente.dni = payload.dni.strip()
        if payload.telefono is not None:
            if not _valid_e164(payload.telefono):
                raise HTTPException(
                    status_code=422,
                    detail={"code": "RN-PA-01", "message": "El telefono debe ser un número E.164 válido."},
                )
            paciente.telefono = payload.telefono.strip()
        if payload.email is not None:
            paciente.email = payload.email.strip()
        if payload.fecha_nac is not None:
            paciente.fecha_nac = payload.fecha_nac
        if payload.notas is not None:
            paciente.notas = payload.notas
        self.session.commit()
        return paciente

    def borrar(self, tenant_id: str, paciente_id: str) -> None:
        paciente = self.obtener(tenant_id, paciente_id)
        self.pacientes.delete(paciente)
        self.session.commit()

    def listar_optins(self, tenant_id: str, paciente_id: str):
        self.obtener(tenant_id, paciente_id)
        return self.optins.list_for_paciente(tenant_id, paciente_id)

    def upsert_optin(self, tenant_id: str, paciente_id: str, payload: OptInUpsert) -> OptInModel:
        paciente = self.obtener(tenant_id, paciente_id)
        if payload.canal == "whatsapp" and payload.estado and (
            not paciente.telefono or not _valid_e164(paciente.telefono)
        ):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "RN-PA-01",
                    "message": "El telefono es obligatorio para activar el opt-in de WhatsApp.",
                },
            )
        existe = self.optins.get_for_canal(tenant_id, paciente_id, payload.canal)
        if existe is None:
            nuevo = OptInModel(
                tenant_id=tenant_id,
                paciente_id=paciente.id,
                canal=payload.canal,
                estado=payload.estado,
                updated_at=_utc_now(),
            )
            self.optins.save(nuevo)
            self.session.commit()
            return nuevo
        existe.estado = payload.estado
        existe.updated_at = _utc_now()
        self.session.commit()
        return existe

    def importar_csv(self, tenant_id: str, csv_texto: str) -> dict:
        if not csv_texto or not csv_texto.strip():
            raise HTTPException(
                status_code=422,
                detail={"code": "RN-GL-02", "message": "El CSV está vacío."},
            )

        filas = list(csv.DictReader(io.StringIO(csv_texto)))
        if not filas:
            return {"importadas": 0, "duplicadas": 0, "fallidas": 0}

        importadas = 0
        duplicadas = 0
        fallidas = 0

        for fila in filas:
            try:
                row = {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in fila.items() if k is not None}
                nombre = (row.get("nombre") or "").strip()
                apellido = (row.get("apellido") or "").strip()
                telefono = (row.get("telefono") or "").strip() or None
                dni = (row.get("dni") or "").strip() or None
                email = (row.get("email") or "").strip() or None

                if not nombre or not apellido:
                    fallidas += 1
                    continue

                if telefono is not None and not _valid_e164(telefono):
                    fallidas += 1
                    continue

                existing = self.session.query(PacienteModel).filter(
                    PacienteModel.tenant_id == tenant_id,
                    (PacienteModel.dni == dni) if dni else False,
                ).first()
                if existing is None and telefono:
                    existing = self.session.query(PacienteModel).filter(
                        PacienteModel.tenant_id == tenant_id,
                        PacienteModel.telefono == telefono,
                    ).first()
                if existing is not None:
                    duplicadas += 1
                    continue

                paciente = PacienteModel(
                    tenant_id=tenant_id,
                    nombre=nombre,
                    apellido=apellido,
                    dni=dni,
                    telefono=telefono,
                    email=email,
                )
                self.pacientes.create(paciente)
                importadas += 1
            except Exception:
                fallidas += 1

        self.session.commit()
        return {"importadas": importadas, "duplicadas": duplicadas, "fallidas": fallidas}

    def listar_evoluciones(self, tenant_id: str, paciente_id: str):
        self.obtener(tenant_id, paciente_id)
        return (
            self.session.query(EvolucionModel)
            .filter(EvolucionModel.tenant_id == tenant_id, EvolucionModel.paciente_id == paciente_id)
            .order_by(EvolucionModel.created_at.desc())
            .all()
        )

    def crear_evolucion(self, tenant_id: str, paciente_id: str, payload: EvolucionCreate) -> EvolucionModel:
        paciente = self.obtener(tenant_id, paciente_id)
        evolucion = EvolucionModel(
            tenant_id=tenant_id,
            paciente_id=paciente.id,
            motivo=payload.motivo.strip(),
            detalle=payload.detalle.strip(),
            firma_simple=payload.firma_simple,
            firma_timestamp=_utc_now() if payload.firma_simple else None,
        )
        self.session.add(evolucion)
        self.session.commit()
        return evolucion

    def crear_adjunto(self, tenant_id: str, paciente_id: str, payload: AdjuntoCreate) -> AdjuntoModel:
        self.obtener(tenant_id, paciente_id)
        if payload.tamano_bytes > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=422,
                detail={"code": "RN-PA-03", "message": "El archivo supera el límite de 10 MB."},
            )
        adjunto = AdjuntoModel(
            tenant_id=tenant_id,
            paciente_id=paciente_id,
            nombre=payload.nombre.strip(),
            tipo=payload.tipo.strip(),
            tamano_bytes=payload.tamano_bytes,
            url=payload.url.strip() if payload.url else None,
        )
        self.session.add(adjunto)
        self.session.commit()
        return adjunto

    def listar_presupuestos(self, tenant_id: str, paciente_id: str):
        self.obtener(tenant_id, paciente_id)
        return (
            self.session.query(PresupuestoModel)
            .filter(PresupuestoModel.tenant_id == tenant_id, PresupuestoModel.paciente_id == paciente_id)
            .order_by(PresupuestoModel.created_at.desc())
            .all()
        )

    def crear_presupuesto(self, tenant_id: str, paciente_id: str, payload: PresupuestoCreate) -> PresupuestoModel:
        paciente = self.obtener(tenant_id, paciente_id)
        total_cents = sum(item.monto_cents for item in payload.items)
        presupuesto = PresupuestoModel(
            tenant_id=tenant_id,
            paciente_id=paciente.id,
            total_cents=total_cents,
            estado="activo",
            notas=payload.notas.strip() if payload.notas else None,
        )
        self.session.add(presupuesto)
        self.session.flush()

        for item in payload.items:
            detalle = PresupuestoItemModel(
                tenant_id=tenant_id,
                presupuesto_id=presupuesto.id,
                descripcion=item.descripcion.strip(),
                monto_cents=item.monto_cents,
            )
            self.session.add(detalle)

        paciente.saldo = (paciente.saldo or 0) + total_cents
        self.session.commit()
        return presupuesto

    def exportar_csv(self, tenant_id: str, recurso: str) -> str:
        if recurso not in {"pacientes", "turnos", "cobros"}:
            raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Recurso no encontrado."})
        if recurso == "pacientes":
            rows = self.pacientes.list(tenant_id)
            fieldnames = ["id", "tenant_id", "nombre", "apellido", "dni", "telefono", "email", "fecha_nac", "notas", "saldo"]
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for paciente in rows:
                writer.writerow({
                    "id": paciente.id,
                    "tenant_id": paciente.tenant_id,
                    "nombre": paciente.nombre,
                    "apellido": paciente.apellido,
                    "dni": paciente.dni or "",
                    "telefono": paciente.telefono or "",
                    "email": paciente.email or "",
                    "fecha_nac": paciente.fecha_nac.isoformat() if paciente.fecha_nac else "",
                    "notas": paciente.notas or "",
                    "saldo": paciente.saldo,
                })
            return output.getvalue()
        raise HTTPException(status_code=501, detail={"code": "RN-GL-02", "message": "Exportación de este recurso aún no está implementada."})

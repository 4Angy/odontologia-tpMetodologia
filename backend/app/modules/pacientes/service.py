from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import datetime, timezone
from pathlib import PurePath
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.audit import registrar_auditoria
from app.modules.agenda.models import ProfesionalModel
from app.modules.pacientes.models import (
    AdjuntoModel,
    EvolucionModel,
    OptInModel,
    PacienteModel,
    PresupuestoItemModel,
    PresupuestoModel,
)
from app.modules.pacientes.attachment_storage import (
    AttachmentStorage,
    AttachmentStorageError,
)
from app.modules.pacientes.repository import OptInRepository, PacienteRepository
from app.modules.pacientes.schemas import (
    EvolucionCreate,
    OptInUpsert,
    PacienteCreate,
    PacienteUpdate,
    PresupuestoCreate,
    PresupuestoEstadoUpdate,
    PresupuestoUpdate,
)

MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 5_000
CSV_REQUIRED_HEADERS = frozenset({"nombre", "apellido"})
CSV_ALLOWED_HEADERS = frozenset({"nombre", "apellido", "dni", "telefono", "email"})
_E164 = re.compile(r"^\+[1-9]\d{1,14}$")
MAX_ADJUNTO_BYTES = 10 * 1024 * 1024
MAX_MONTO_CENTS = 2_147_483_647
_MIME_SIGNATURES = {
    "image/jpeg": lambda content: content.startswith(b"\xff\xd8\xff"),
    "image/png": lambda content: content.startswith(b"\x89PNG\r\n\x1a\n"),
    "application/pdf": lambda content: content.startswith(b"%PDF-"),
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _valid_e164(value: str | None) -> bool:
    if value is None:
        return True
    return _E164.fullmatch(value) is not None


class PacienteService:
    def __init__(self, session) -> None:
        self.session = session
        self.pacientes = PacienteRepository(session)
        self.optins = OptInRepository(session)

    def listar(self, tenant_id: str, q: str | None = None) -> list[PacienteModel]:
        return self.pacientes.list(tenant_id, q)

    def obtener(self, tenant_id: str, paciente_id: str) -> PacienteModel:
        paciente = self.pacientes.get_by_id(tenant_id, paciente_id)
        if paciente is None:
            raise HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Paciente no encontrado."})
        return paciente

    def crear(
        self, tenant_id: str, actor_id: str, payload: PacienteCreate
    ) -> PacienteModel:
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
        registrar_auditoria(
            self.session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="paciente.creado",
            recurso="paciente",
            recurso_id=paciente.id,
            campos=["nombre", "apellido", "dni", "telefono", "email", "fecha_nac", "notas"],
        )
        self.session.commit()
        return paciente

    def actualizar(
        self,
        tenant_id: str,
        actor_id: str,
        paciente_id: str,
        payload: PacienteUpdate,
    ) -> PacienteModel:
        paciente = self.obtener(tenant_id, paciente_id)
        fields = payload.model_fields_set
        campos_modificados: list[str] = []
        numero_anterior = paciente.telefono

        for field in ("nombre", "apellido", "dni", "telefono", "email", "fecha_nac", "notas"):
            if field not in fields:
                continue
            value = getattr(payload, field)
            if field in {"nombre", "apellido"} and value is None:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "RN-PA-01", "message": "Nombre y apellido son obligatorios."},
                )
            if field == "telefono" and value is not None and not _valid_e164(value.strip()):
                raise HTTPException(
                    status_code=422,
                    detail={"code": "RN-PA-01", "message": "El telefono debe ser un número E.164 válido."},
                )
            if isinstance(value, str):
                value = value.strip()
            if getattr(paciente, field) != value:
                setattr(paciente, field, value)
                campos_modificados.append(field)

        telefono_cambio = "telefono" in campos_modificados
        hash_destino_anterior = (
            hashlib.sha256(numero_anterior.encode("utf-8")).hexdigest()
            if telefono_cambio and numero_anterior
            else None
        )
        if telefono_cambio:
            optin = self.optins.get_for_canal(tenant_id, paciente_id, "whatsapp")
            if optin is not None and optin.estado:
                optin.estado = False
                optin.updated_at = _utc_now()
                campos_modificados.append("optin_whatsapp.estado")

        if campos_modificados:
            registrar_auditoria(
                self.session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                accion=(
                    "paciente.telefono_cambiado"
                    if telefono_cambio
                    else "paciente.actualizado"
                ),
                recurso="paciente",
                recurso_id=paciente.id,
                campos=campos_modificados,
                invalidated_destination_hash=hash_destino_anterior,
            )
        self.session.commit()
        return paciente

    def borrar(self, tenant_id: str, actor_id: str, paciente_id: str) -> None:
        paciente = self.obtener(tenant_id, paciente_id)
        ahora = _utc_now()
        paciente.deleted_at = ahora
        paciente.updated_at = ahora
        for optin in self.optins.list_for_paciente(tenant_id, paciente_id):
            if optin.estado:
                optin.estado = False
                optin.updated_at = ahora
        registrar_auditoria(
            self.session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="paciente.baja_logica",
            recurso="paciente",
            recurso_id=paciente.id,
            campos=["deleted_at", "optins.estado"],
        )
        self.session.commit()

    def listar_optins(self, tenant_id: str, paciente_id: str):
        self.obtener(tenant_id, paciente_id)
        return self.optins.list_for_paciente(tenant_id, paciente_id)

    def upsert_optin(
        self,
        tenant_id: str,
        actor_id: str,
        paciente_id: str,
        payload: OptInUpsert,
    ) -> OptInModel:
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
        version_texto = payload.version_texto.strip() if payload.version_texto else None
        if payload.estado and not version_texto:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "RN-PA-01",
                    "message": "Indicá la versión del texto de consentimiento presentado.",
                },
            )
        existe = self.optins.get_for_canal(tenant_id, paciente_id, payload.canal)
        ahora = _utc_now()
        if existe is None:
            nuevo = OptInModel(
                tenant_id=tenant_id,
                paciente_id=paciente.id,
                canal=payload.canal,
                estado=payload.estado,
                updated_at=ahora,
                consentimiento_version=version_texto if payload.estado else None,
                consentimiento_actor_id=actor_id if payload.estado else None,
                consentimiento_at=ahora if payload.estado else None,
            )
            self.optins.save(nuevo)
            existe = nuevo
        else:
            existe.estado = payload.estado
            existe.updated_at = ahora
            if payload.estado:
                existe.consentimiento_version = version_texto
                existe.consentimiento_actor_id = actor_id
                existe.consentimiento_at = ahora

        registrar_auditoria(
            self.session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion=(
                "paciente.optin_activado"
                if payload.estado
                else "paciente.optin_revocado"
            ),
            recurso="optin",
            recurso_id=existe.id,
            campos=["canal", "estado", "consentimiento_version"],
            consentimiento_version=version_texto if payload.estado else None,
        )
        self.session.commit()
        return existe

    def importar_csv(self, tenant_id: str, actor_id: str, contenido: bytes) -> dict:
        if len(contenido) > MAX_IMPORT_BYTES:
            raise HTTPException(
                status_code=413,
                detail={"code": "RN-PA-01", "message": "El CSV supera el límite de 5 MiB."},
            )
        try:
            csv_texto = contenido.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=422,
                detail={"code": "RN-PA-01", "message": "El CSV debe estar codificado en UTF-8."},
            ) from None
        if not csv_texto.strip():
            raise HTTPException(
                status_code=422,
                detail={"code": "RN-PA-01", "message": "El CSV está vacío."},
            )

        try:
            reader = csv.reader(io.StringIO(csv_texto, newline=""), strict=True)
            encabezados = next(reader, None)
            if not encabezados:
                raise ValueError("El CSV debe incluir encabezados.")
            encabezados = [header.strip().lower() for header in encabezados]
            if len(encabezados) != len(set(encabezados)):
                raise ValueError("El CSV contiene encabezados repetidos.")
            if not CSV_REQUIRED_HEADERS.issubset(encabezados):
                raise ValueError("El CSV debe incluir las columnas nombre y apellido.")
            if set(encabezados) - CSV_ALLOWED_HEADERS:
                raise ValueError("El CSV contiene columnas no admitidas.")
            filas = list(reader)
        except (csv.Error, ValueError):
            raise HTTPException(
                status_code=422,
                detail={"code": "RN-PA-01", "message": "El formato o los encabezados del CSV no son válidos."},
            ) from None

        if len(filas) > MAX_IMPORT_ROWS:
            raise HTTPException(
                status_code=413,
                detail={"code": "RN-PA-01", "message": "El CSV supera el límite de 5.000 filas."},
            )
        if not filas:
            raise HTTPException(
                status_code=422,
                detail={"code": "RN-PA-01", "message": "El CSV no contiene filas de pacientes."},
            )

        resultados: list[dict] = []
        dni_vistos: set[str] = set()
        telefonos_vistos: set[str] = set()
        importadas = duplicadas = fallidas = 0

        for numero_fila, valores in enumerate(filas, start=2):
            if len(valores) != len(encabezados):
                resultados.append(
                    {
                        "fila": numero_fila,
                        "estado": "fallida",
                        "code": "RN-PA-01",
                        "mensaje": "La cantidad de valores no coincide con los encabezados.",
                    }
                )
                fallidas += 1
                continue

            fila = dict(zip(encabezados, (value.strip() for value in valores), strict=True))
            nombre = fila["nombre"]
            apellido = fila["apellido"]
            dni = fila.get("dni") or None
            telefono = fila.get("telefono") or None
            email = fila.get("email") or None
            if not nombre or not apellido:
                resultados.append(
                    {
                        "fila": numero_fila,
                        "estado": "fallida",
                        "code": "RN-PA-01",
                        "mensaje": "Nombre y apellido son obligatorios.",
                    }
                )
                fallidas += 1
                continue
            if telefono is not None and not _valid_e164(telefono):
                resultados.append(
                    {
                        "fila": numero_fila,
                        "estado": "fallida",
                        "code": "RN-PA-01",
                        "mensaje": "El teléfono debe tener formato E.164.",
                    }
                )
                fallidas += 1
                continue
            if (
                (dni is not None and dni in dni_vistos)
                or (telefono is not None and telefono in telefonos_vistos)
                or self.pacientes.exists_with_contact(
                    tenant_id, dni=dni, telefono=telefono
                )
            ):
                resultados.append(
                    {
                        "fila": numero_fila,
                        "estado": "duplicada",
                        "code": "RN-PA-02",
                        "mensaje": "Ya existe un paciente con ese DNI o teléfono.",
                    }
                )
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
            try:
                with self.session.begin_nested():
                    self.pacientes.create(paciente)
                    registrar_auditoria(
                        self.session,
                        tenant_id=tenant_id,
                        actor_id=actor_id,
                        accion="paciente.importado",
                        recurso="paciente",
                        recurso_id=paciente.id,
                        campos=["nombre", "apellido", "dni", "telefono", "email"],
                    )
            except IntegrityError:
                if not self.pacientes.exists_with_contact(
                    tenant_id, dni=dni, telefono=telefono
                ):
                    raise
                resultados.append(
                    {
                        "fila": numero_fila,
                        "estado": "duplicada",
                        "code": "RN-PA-02",
                        "mensaje": "Ya existe un paciente con ese DNI o teléfono.",
                    }
                )
                duplicadas += 1
                continue

            if dni:
                dni_vistos.add(dni)
            if telefono:
                telefonos_vistos.add(telefono)
            resultados.append(
                {"fila": numero_fila, "estado": "importada", "paciente_id": paciente.id}
            )
            importadas += 1

        self.session.commit()
        return {
            "importadas": importadas,
            "duplicadas": duplicadas,
            "fallidas": fallidas,
            "resultados": resultados,
        }

    def listar_evoluciones(
        self, tenant_id: str, paciente_id: str, actor_id: str, roles: list[str]
    ) -> list[EvolucionModel]:
        self.obtener(tenant_id, paciente_id)
        statement = select(EvolucionModel).where(
            EvolucionModel.tenant_id == tenant_id,
            EvolucionModel.paciente_id == paciente_id,
            EvolucionModel.deleted_at.is_(None),
        )
        if "dueno" not in set(roles):
            statement = statement.join(
                ProfesionalModel,
                (ProfesionalModel.id == EvolucionModel.profesional_id)
                & (ProfesionalModel.tenant_id == tenant_id),
            ).where(ProfesionalModel.usuario_id == actor_id)
        return list(
            self.session.execute(
                statement.order_by(EvolucionModel.fecha.desc(), EvolucionModel.id.desc())
            ).scalars()
        )

    def _profesional_del_actor(
        self, tenant_id: str, actor_id: str, profesional_id: str | None = None
    ) -> ProfesionalModel:
        statement = select(ProfesionalModel).where(
            ProfesionalModel.tenant_id == tenant_id,
            ProfesionalModel.usuario_id == actor_id,
            ProfesionalModel.activo.is_(True),
            ProfesionalModel.deleted_at.is_(None),
        )
        if profesional_id is not None:
            statement = statement.where(ProfesionalModel.id == profesional_id)
        profesionales = list(self.session.execute(statement).scalars())
        if not profesionales:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "RN-AU-04",
                    "message": "El profesional no está vinculado al usuario autenticado.",
                },
            )
        if len(profesionales) > 1:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "RN-AU-04",
                    "message": "El usuario está vinculado a más de un profesional; especificá cuál usar.",
                },
            )
        return profesionales[0]

    def crear_evolucion(
        self,
        tenant_id: str,
        paciente_id: str,
        actor_id: str,
        payload: EvolucionCreate,
    ) -> EvolucionModel:
        paciente = self.obtener(tenant_id, paciente_id)
        profesional = self._profesional_del_actor(
            tenant_id, actor_id, payload.profesional_id
        )
        ahora = _utc_now()
        evolucion = EvolucionModel(
            tenant_id=tenant_id,
            paciente_id=paciente.id,
            profesional_id=profesional.id,
            odontologo_id=actor_id,
            fecha=payload.fecha or ahora,
            motivo=payload.motivo.strip(),
            detalle=payload.detalle.strip(),
            pieza_fdi_slot=payload.pieza_fdi_slot,
            pieza_fdi_numero=payload.pieza_fdi_numero,
            odontograma_ref=payload.odontograma_ref,
            firma_simple=payload.firma_simple,
            firmado_at=ahora if payload.firma_simple else None,
            firma_timestamp=ahora if payload.firma_simple else None,
        )
        self.session.add(evolucion)
        self.session.flush()
        registrar_auditoria(
            self.session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="evolucion.creada",
            recurso="evolucion",
            recurso_id=evolucion.id,
            campos=[
                "profesional_id",
                "fecha",
                "motivo",
                "detalle",
                "pieza_fdi_slot",
                "pieza_fdi_numero",
                "odontograma_ref",
                "firma_simple",
                "firmado_at",
            ],
        )
        self.session.commit()
        return evolucion

    def actualizar_evolucion(
        self,
        tenant_id: str,
        paciente_id: str,
        evolucion_id: str,
        actor_id: str,
        payload: EvolucionCreate,
    ) -> EvolucionModel:
        evolucion = self.session.execute(
            select(EvolucionModel).where(
                EvolucionModel.tenant_id == tenant_id,
                EvolucionModel.paciente_id == paciente_id,
                EvolucionModel.id == evolucion_id,
                EvolucionModel.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if evolucion is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "RN-AU-01", "message": "Evolución no encontrada."},
            )
        profesional = self._profesional_del_actor(
            tenant_id, actor_id, payload.profesional_id or evolucion.profesional_id
        )
        if evolucion.profesional_id != profesional.id:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "RN-AU-04",
                    "message": "Solo podés editar tus propias evoluciones.",
                },
            )
        evolucion.fecha = payload.fecha or evolucion.fecha
        evolucion.motivo = payload.motivo.strip()
        evolucion.detalle = payload.detalle.strip()
        evolucion.pieza_fdi_slot = payload.pieza_fdi_slot
        evolucion.pieza_fdi_numero = payload.pieza_fdi_numero
        evolucion.odontograma_ref = payload.odontograma_ref
        evolucion.firma_simple = payload.firma_simple
        evolucion.firmado_at = (
            evolucion.firmado_at or _utc_now() if payload.firma_simple else None
        )
        evolucion.firma_timestamp = evolucion.firmado_at
        registrar_auditoria(
            self.session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="evolucion.actualizada",
            recurso="evolucion",
            recurso_id=evolucion.id,
            campos=[
                "fecha",
                "motivo",
                "detalle",
                "pieza_fdi_slot",
                "pieza_fdi_numero",
                "odontograma_ref",
                "firma_simple",
                "firmado_at",
            ],
        )
        self.session.commit()
        return evolucion

    def crear_adjunto(
        self,
        tenant_id: str,
        paciente_id: str,
        actor_id: str,
        nombre: str,
        tipo: str,
        contenido: bytes,
        storage: AttachmentStorage,
    ) -> AdjuntoModel:
        paciente = self.obtener(tenant_id, paciente_id)
        nombre_seguro = PurePath(nombre).name.strip()
        tipo_real = next(
            (
                mime
                for mime, detectar in _MIME_SIGNATURES.items()
                if detectar(contenido)
            ),
            None,
        )
        if (
            not nombre_seguro
            or len(nombre_seguro) > 200
            or not contenido
            or len(contenido) > MAX_ADJUNTO_BYTES
            or tipo not in _MIME_SIGNATURES
            or tipo_real != tipo
        ):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "RN-PA-03",
                    "message": "El adjunto debe ser JPEG, PNG o PDF válido y no superar 10 MiB.",
                },
            )
        adjunto_id = str(uuid4())
        storage_key = f"tenants/{tenant_id}/pacientes/{paciente.id}/{adjunto_id}"
        try:
            storage.put(storage_key, contenido, tipo_real)
        except AttachmentStorageError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "RN-PA-03",
                    "message": "No se pudo guardar el adjunto privado.",
                },
            ) from exc
        adjunto = AdjuntoModel(
            id=adjunto_id,
            tenant_id=tenant_id,
            paciente_id=paciente.id,
            nombre=nombre_seguro,
            tipo=tipo_real,
            tamano_bytes=len(contenido),
            storage_key=storage_key,
        )
        self.session.add(adjunto)
        registrar_auditoria(
            self.session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="adjunto.creado",
            recurso="adjunto",
            recurso_id=adjunto.id,
            campos=["nombre", "tipo", "tamano_bytes"],
        )
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            try:
                storage.delete(storage_key)
            except AttachmentStorageError as cleanup_error:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "code": "RN-PA-03",
                        "message": "Falló la persistencia y no se pudo limpiar el archivo privado.",
                    },
                ) from cleanup_error
            raise
        return adjunto

    def listar_adjuntos(self, tenant_id: str, paciente_id: str) -> list[AdjuntoModel]:
        self.obtener(tenant_id, paciente_id)
        return list(
            self.session.execute(
                select(AdjuntoModel)
                .where(
                    AdjuntoModel.tenant_id == tenant_id,
                    AdjuntoModel.paciente_id == paciente_id,
                    AdjuntoModel.deleted_at.is_(None),
                    AdjuntoModel.storage_key.is_not(None),
                )
                .order_by(AdjuntoModel.created_at.desc(), AdjuntoModel.id.desc())
            ).scalars()
        )

    def obtener_adjunto(
        self, tenant_id: str, paciente_id: str, adjunto_id: str
    ) -> AdjuntoModel:
        adjunto = self.session.execute(
            select(AdjuntoModel).where(
                AdjuntoModel.tenant_id == tenant_id,
                AdjuntoModel.paciente_id == paciente_id,
                AdjuntoModel.id == adjunto_id,
                AdjuntoModel.deleted_at.is_(None),
                AdjuntoModel.storage_key.is_not(None),
            )
        ).scalar_one_or_none()
        if adjunto is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "RN-AU-01", "message": "Adjunto no encontrado."},
            )
        return adjunto

    def listar_presupuestos(self, tenant_id: str, paciente_id: str) -> list[PresupuestoModel]:
        self.obtener(tenant_id, paciente_id)
        return list(
            self.session.execute(
                select(PresupuestoModel)
                .where(
                    PresupuestoModel.tenant_id == tenant_id,
                    PresupuestoModel.paciente_id == paciente_id,
                    PresupuestoModel.deleted_at.is_(None),
                )
                .order_by(PresupuestoModel.created_at.desc(), PresupuestoModel.id.desc())
            ).scalars()
        )

    def saldo_derivado(self, tenant_id: str, paciente_id: str) -> int:
        value = self.session.execute(
            select(func.coalesce(func.sum(PresupuestoModel.total_cents), 0)).where(
                PresupuestoModel.tenant_id == tenant_id,
                PresupuestoModel.paciente_id == paciente_id,
                PresupuestoModel.estado.in_(("aprobado", "aceptado")),
                PresupuestoModel.deleted_at.is_(None),
            )
        ).scalar_one()
        cargos = int(value)
        # C-11: restar cobros manuales. Señas se integran en C-12.
        try:
            from app.modules.cobros.models import CobroModel

            pagos = self.session.execute(
                select(func.coalesce(func.sum(CobroModel.monto_cents), 0)).where(
                    CobroModel.tenant_id == tenant_id,
                    CobroModel.paciente_id == paciente_id,
                    CobroModel.deleted_at.is_(None),
                )
            ).scalar_one()
            cargos -= int(pagos)
        except Exception:  # noqa: BLE001 - tabla puede no existir en tests legacy
            pass
        return cargos

    def _validar_total_presupuesto(self, payload: PresupuestoCreate | PresupuestoUpdate) -> int:
        total = sum(item.monto_cents for item in payload.items)
        if total > MAX_MONTO_CENTS:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "RN-CO-05",
                    "message": "El total del presupuesto supera el importe máximo permitido.",
                },
            )
        return total

    def crear_presupuesto(
        self,
        tenant_id: str,
        paciente_id: str,
        actor_id: str,
        payload: PresupuestoCreate,
    ) -> PresupuestoModel:
        paciente = self.obtener(tenant_id, paciente_id)
        total_cents = self._validar_total_presupuesto(payload)
        presupuesto = PresupuestoModel(
            tenant_id=tenant_id,
            paciente_id=paciente.id,
            total_cents=total_cents,
            estado=payload.estado,
            notas=payload.notas.strip() if payload.notas else None,
        )
        self.session.add(presupuesto)
        self.session.flush()
        for item in payload.items:
            self.session.add(
                PresupuestoItemModel(
                    tenant_id=tenant_id,
                    presupuesto_id=presupuesto.id,
                    descripcion=item.descripcion.strip(),
                    monto_cents=item.monto_cents,
                )
            )
        registrar_auditoria(
            self.session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="presupuesto.creado",
            recurso="presupuesto",
            recurso_id=presupuesto.id,
            campos=["estado", "total_cents", "notas", "items"],
        )
        self.session.commit()
        return presupuesto

    def _obtener_presupuesto(
        self, tenant_id: str, paciente_id: str, presupuesto_id: str
    ) -> PresupuestoModel:
        presupuesto = self.session.execute(
            select(PresupuestoModel).where(
                PresupuestoModel.tenant_id == tenant_id,
                PresupuestoModel.paciente_id == paciente_id,
                PresupuestoModel.id == presupuesto_id,
                PresupuestoModel.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if presupuesto is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "RN-AU-01", "message": "Presupuesto no encontrado."},
            )
        return presupuesto

    def actualizar_presupuesto(
        self,
        tenant_id: str,
        paciente_id: str,
        presupuesto_id: str,
        actor_id: str,
        payload: PresupuestoUpdate,
    ) -> PresupuestoModel:
        presupuesto = self._obtener_presupuesto(tenant_id, paciente_id, presupuesto_id)
        total_cents = self._validar_total_presupuesto(payload)
        for item in list(presupuesto.items):
            self.session.delete(item)
        self.session.flush()
        presupuesto.total_cents = total_cents
        presupuesto.notas = payload.notas.strip() if payload.notas else None
        for item in payload.items:
            self.session.add(
                PresupuestoItemModel(
                    tenant_id=tenant_id,
                    presupuesto_id=presupuesto.id,
                    descripcion=item.descripcion.strip(),
                    monto_cents=item.monto_cents,
                )
            )
        registrar_auditoria(
            self.session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="presupuesto.actualizado",
            recurso="presupuesto",
            recurso_id=presupuesto.id,
            campos=["total_cents", "notas", "items"],
        )
        self.session.commit()
        return presupuesto

    def actualizar_estado_presupuesto(
        self,
        tenant_id: str,
        paciente_id: str,
        presupuesto_id: str,
        actor_id: str,
        payload: PresupuestoEstadoUpdate,
    ) -> PresupuestoModel:
        presupuesto = self._obtener_presupuesto(tenant_id, paciente_id, presupuesto_id)
        presupuesto.estado = payload.estado
        registrar_auditoria(
            self.session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="presupuesto.estado_actualizado",
            recurso="presupuesto",
            recurso_id=presupuesto.id,
            campos=["estado"],
        )
        self.session.commit()
        return presupuesto

    def eliminar_presupuesto(
        self, tenant_id: str, paciente_id: str, presupuesto_id: str, actor_id: str
    ) -> None:
        presupuesto = self._obtener_presupuesto(tenant_id, paciente_id, presupuesto_id)
        registrar_auditoria(
            self.session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="presupuesto.eliminado",
            recurso="presupuesto",
            recurso_id=presupuesto.id,
            campos=["estado", "total_cents", "items"],
        )
        self.session.delete(presupuesto)
        self.session.commit()

    def exportar_csv(self, tenant_id: str) -> str:
        rows = self.pacientes.list(tenant_id)
        fieldnames = [
            "id",
            "nombre",
            "apellido",
            "dni",
            "telefono",
            "email",
            "fecha_nac",
            "notas",
            "saldo",
        ]
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for paciente in rows:
            writer.writerow(
                {
                    "id": paciente.id,
                    "nombre": paciente.nombre,
                    "apellido": paciente.apellido,
                    "dni": paciente.dni or "",
                    "telefono": paciente.telefono or "",
                    "email": paciente.email or "",
                    "fecha_nac": paciente.fecha_nac.isoformat() if paciente.fecha_nac else "",
                    "notas": paciente.notas or "",
                    "saldo": self.saldo_derivado(tenant_id, paciente.id),
                }
            )
        return "\ufeff" + output.getvalue()

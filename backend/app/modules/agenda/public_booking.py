from __future__ import annotations

import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rate_limit import InMemoryRateLimiter, RateLimiter
from app.modules.agenda.availability import candidatos_disponibles
from app.modules.agenda.models import (
    ConfigModel,
    PublicAuditModel,
    PublicTokenModel,
    PrestacionModel,
    ProfesionalModel,
    TenantModel,
    TurnoModel,
)
from app.modules.agenda.repository import PublicTokenRepository, TurnoRepository
from app.modules.agenda.service import AgendaCancelService, AgendaError, User, resolver_antelacion
from app.modules.agenda.turnos_service import TurnosService
from app.modules.cobros.senias_service import SeniaService
from app.modules.pacientes.repository import PacienteRepository
from app.modules.pacientes.models import OptInModel, PacienteModel

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")

PURPOSES = ("confirm", "cancel", "reschedule")
PUBLIC_TOKEN_TTL = timedelta(hours=72)
PAYMENT_TIMEOUT = timedelta(minutes=30)


class PublicSlotConflictError(RuntimeError):
    def __init__(self, alternatives: list[datetime]) -> None:
        super().__init__("El horario ya no está disponible.")
        self.alternatives = alternatives


def _valid_e164(value: str | None) -> bool:
    return value is not None and _E164.fullmatch(value) is not None


class PublicStrict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PublicAvailabilityResponse(PublicStrict):
    tenant_slug: str
    tenant_name: str
    professionals: list[dict]
    services: list[dict]
    slots: list[datetime]


class PublicBookingRequest(PublicStrict):
    tenant_slug: str = Field(min_length=1, max_length=100)
    profesional_id: str = Field(min_length=1, max_length=64)
    prestacion_id: str = Field(min_length=1, max_length=64)
    inicio: datetime
    nombre: str = Field(min_length=1, max_length=120)
    apellido: str = Field(min_length=1, max_length=120)
    telefono: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    whatsapp_opt_in: bool = False

    @model_validator(mode="after")
    def validate_request(self) -> "PublicBookingRequest":
        if self.inicio.tzinfo is None or self.inicio.utcoffset() is None:
            raise ValueError("El inicio debe incluir zona horaria.")
        if self.whatsapp_opt_in and not _valid_e164(self.telefono):
            raise ValueError("El teléfono debe ser E.164 para activar WhatsApp.")
        return self


class PublicActionRequest(PublicStrict):
    tenant_slug: str = Field(min_length=1, max_length=100)


class PublicRescheduleRequest(PublicStrict):
    tenant_slug: str = Field(min_length=1, max_length=100)
    profesional_id: str = Field(min_length=1, max_length=64)
    prestacion_id: str = Field(min_length=1, max_length=64)
    inicio: datetime

    @model_validator(mode="after")
    def validate_datetime(self) -> "PublicRescheduleRequest":
        if self.inicio.tzinfo is None or self.inicio.utcoffset() is None:
            raise ValueError("El inicio debe incluir zona horaria.")
        return self


class PublicBookingResponse(PublicStrict):
    turno_id: str
    estado: str
    action_tokens: dict[str, str]
    checkout_url: str | None = None


class PublicActionResponse(PublicStrict):
    turno_id: str
    estado: str
    confirmado_paciente_at: datetime | None = None


class PublicBookingService:
    def __init__(self, session: Session, rate_limiter: RateLimiter | None = None) -> None:
        self.session = session
        self.rate_limiter = rate_limiter or PUBLIC_RATE_LIMITER
        self.tokens = PublicTokenRepository(session)

    def tenant(self, slug: str) -> TenantModel:
        tenant = self.session.execute(
            select(TenantModel).where(TenantModel.slug == slug)
        ).scalar_one_or_none()
        if tenant is None:
            raise LookupError("Consultorio no encontrado.")
        return tenant

    def availability(
        self,
        *,
        slug: str,
        profesional_id: str | None,
        prestacion_id: str | None,
        desde: datetime,
        hasta: datetime,
        ahora: datetime,
    ) -> PublicAvailabilityResponse:
        tenant = self.tenant(slug)
        slots = []
        if profesional_id and prestacion_id:
            slots = candidatos_disponibles(
                self.session,
                tenant_id=tenant.id,
                profesional_id=profesional_id,
                prestacion_id=prestacion_id,
                desde=desde,
                hasta=hasta,
                ahora_utc=ahora,
            )
        professionals = self.session.execute(
            select(ProfesionalModel).where(
                ProfesionalModel.tenant_id == tenant.id,
                ProfesionalModel.activo.is_(True),
            ).order_by(ProfesionalModel.nombre)
        ).scalars().all()
        services = self.session.execute(
            select(PrestacionModel).where(
                PrestacionModel.tenant_id == tenant.id,
                PrestacionModel.activa.is_(True),
            ).order_by(PrestacionModel.nombre)
        ).scalars().all()
        senias = SeniaService(self.session)
        return PublicAvailabilityResponse(
            tenant_slug=tenant.slug,
            tenant_name=tenant.nombre,
            professionals=[{"id": item.id, "nombre": item.nombre} for item in professionals],
            services=[
                {
                    "id": item.id,
                    "nombre": item.nombre,
                    "duracion_min": item.duracion_min,
                    # C-12: el front público muestra si la reserva exige seña.
                    "senia_requerida": senias.senia_requerida_para(tenant.id, item),
                    "senia_monto_cents": item.senia_monto_cents,
                }
                for item in services
            ],
            slots=slots,
        )

    def create(
        self,
        request: PublicBookingRequest,
        idempotency_key: str,
        now: datetime,
    ) -> PublicBookingResponse:
        tenant = self.tenant(request.tenant_slug)
        if not idempotency_key or len(idempotency_key) > 255:
            raise ValueError("La clave idempotente es obligatoria.")
        inicio = request.inicio.astimezone(timezone.utc)
        prestacion = self.session.execute(
            select(PrestacionModel).where(
                PrestacionModel.tenant_id == tenant.id,
                PrestacionModel.id == request.prestacion_id,
                PrestacionModel.activa.is_(True),
            )
        ).scalar_one_or_none()
        profesional = self.session.execute(
            select(ProfesionalModel).where(
                ProfesionalModel.tenant_id == tenant.id,
                ProfesionalModel.id == request.profesional_id,
                ProfesionalModel.activo.is_(True),
            )
        ).scalar_one_or_none()
        if prestacion is None or profesional is None:
            raise LookupError("La disponibilidad solicitada no existe.")
        fin = inicio + timedelta(minutes=prestacion.duracion_min)
        existing = self.session.execute(
            select(TurnoModel).where(
                TurnoModel.tenant_id == tenant.id,
                TurnoModel.idempotency_key == idempotency_key,
            )
        ).scalar_one_or_none()
        fingerprint = _fingerprint(request)
        if existing is not None:
            if existing.motivo != f"public:{fingerprint}":
                raise ValueError("La clave idempotente ya fue utilizada con otros datos.")
            return self._response(
                existing,
                now,
                issue_tokens=False,
                checkout_url=self._checkout_replay(existing),
            )
        self.session.execute(
            select(ProfesionalModel).where(
                ProfesionalModel.tenant_id == tenant.id,
                ProfesionalModel.id == profesional.id,
            ).with_for_update()
        ).scalar_one()
        collision = self.session.execute(
            select(TurnoModel).where(
                TurnoModel.tenant_id == tenant.id,
                TurnoModel.profesional_id == profesional.id,
                TurnoModel.estado.in_(("confirmado", "pendiente_confirmacion")),
                TurnoModel.inicio < fin,
                TurnoModel.fin > inicio,
            )
        ).scalar_one_or_none()
        if collision is not None:
            raise RuntimeError("El horario ya no está disponible.")
        paciente = self.session.execute(
            select(PacienteModel).where(
                PacienteModel.tenant_id == tenant.id,
                PacienteModel.telefono == request.telefono,
                PacienteModel.deleted_at.is_(None),
            )
        ).scalar_one_or_none() if request.telefono else None
        telefono_anterior: str | None = None
        if paciente is None and request.email:
            paciente = self.session.execute(
                select(PacienteModel).where(
                    PacienteModel.tenant_id == tenant.id,
                    PacienteModel.email == request.email,
                    PacienteModel.deleted_at.is_(None),
                )
            ).scalar_one_or_none()
            if paciente is not None and paciente.telefono != request.telefono:
                telefono_anterior = paciente.telefono
        if paciente is None:
            paciente = PacienteModel(
                id=str(uuid.uuid4()),
                tenant_id=tenant.id,
                nombre=request.nombre,
                apellido=request.apellido,
                telefono=request.telefono,
                email=request.email,
            )
            self.session.add(paciente)
            self.session.flush()
        elif telefono_anterior is not None:
            paciente.telefono = request.telefono
            pendientes = self.session.execute(
                select(TurnoModel).where(
                    TurnoModel.tenant_id == tenant.id,
                    TurnoModel.paciente_id == paciente.id,
                    TurnoModel.estado == "pendiente_confirmacion",
                )
            ).scalars().all()
            for pendiente in pendientes:
                self.tokens.revoke_for_turno(
                    tenant_id=tenant.id,
                    turno_id=pendiente.id,
                    revoked_at=now,
                    reason="phone_changed",
                )
        if request.whatsapp_opt_in:
            optin = self.session.execute(
                select(OptInModel).where(
                    OptInModel.tenant_id == tenant.id,
                    OptInModel.paciente_id == paciente.id,
                    OptInModel.canal == "whatsapp",
                )
            ).scalar_one_or_none()
            if optin is None:
                optin = OptInModel(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant.id,
                    paciente_id=paciente.id,
                    canal="whatsapp",
                    estado=True,
                    updated_at=now,
                )
                self.session.add(optin)
            else:
                optin.estado = True
                optin.updated_at = now
        config = self.session.get(ConfigModel, tenant.id)
        senias = SeniaService(self.session)
        requiere_senia = senias.senia_requerida_para(tenant.id, prestacion)
        turno = TurnoModel(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            paciente_id=paciente.id,
            profesional_id=profesional.id,
            profesional_usuario_id=profesional.usuario_id,
            prestacion_id=prestacion.id,
            inicio=inicio,
            fin=fin,
            estado="pendiente_confirmacion",
            origen="reserva_publica",
            idempotency_key=idempotency_key,
            motivo=f"public:{fingerprint}",
            senia_pendiente_definicion=requiere_senia,
        )
        self.session.add(turno)
        self.session.flush()
        # C-12 (D1/D6): seña MP por prestación + preferencia → checkout_url.
        senia, checkout_url = senias.crear_para_booking(
            tenant_id=tenant.id,
            turno=turno,
            prestacion=prestacion,
            paciente_id=paciente.id,
            ahora=now,
        )
        if senia is not None:
            turno.senia_pendiente_definicion = True
        self.session.add(PublicAuditModel(
            tenant_id=tenant.id,
            turno_id=turno.id,
            action="reserva",
            outcome="creada",
        ))
        return self._response(turno, now, checkout_url=checkout_url)

    def action(self, raw_token: str, purpose: str, slug: str, now: datetime) -> TurnoModel:
        if purpose not in PURPOSES:
            raise PermissionError("Acción pública inválida.")
        tenant = self.tenant(slug)
        token = self.tokens.get_by_raw(
            tenant_id=tenant.id,
            raw_token=raw_token,
            purpose=purpose,
        )
        if token is None:
            raise PermissionError("token_rechazado")
        if token.revoked_at is not None:
            raise PermissionError("token_revocado")
        if token.expires_at <= now:
            raise PermissionError("token_expirado")
        turno = self.session.execute(
            select(TurnoModel).where(
                TurnoModel.tenant_id == tenant.id,
                TurnoModel.id == token.turno_id,
            ).with_for_update()
        ).scalar_one_or_none()
        if turno is None:
            raise PermissionError("Enlace inválido o vencido.")
        self.session.add(PublicAuditModel(
            tenant_id=tenant.id,
            turno_id=turno.id,
            action=purpose,
            outcome="token_validado",
        ))
        return turno

    def confirm(self, turno: TurnoModel, now: datetime | None = None) -> TurnoModel:
        if turno.estado == "pendiente_confirmacion":
            return TurnosService(
                repo=TurnoRepository(self.session),
                pacientes=PacienteRepository(self.session),
                prestaciones=None,
                disponibilidad=lambda **_: [],
            ).confirmar_turno(
                tenant_id=turno.tenant_id,
                turno_id=turno.id,
                user=User(id="public", tenant_id=turno.tenant_id, roles=("recepcion",)),
            )
        if turno.estado == "confirmado":
            if turno.confirmado_paciente_at is None and now is not None:
                from datetime import timezone as _tz

                turno.confirmado_paciente_at = (
                    now if now.tzinfo is not None else now.replace(tzinfo=_tz.utc)
                ).astimezone(_tz.utc)
            return turno
        raise AgendaError("RN-AG-08", "El estado del turno no permite esta acción.", 409)

    def record_rejection(
        self,
        *,
        slug: str,
        action: str,
        outcome: str,
        turno_id: str | None = None,
    ) -> None:
        tenant = self.tenant(slug)
        self.session.add(PublicAuditModel(
            tenant_id=tenant.id,
            turno_id=turno_id,
            action=action,
            outcome=outcome,
        ))

    def reschedule(
        self,
        turno: TurnoModel,
        *,
        profesional_id: str,
        prestacion_id: str,
        inicio: datetime,
        now: datetime,
    ) -> PublicBookingResponse:
        profesional = self.session.execute(
            select(ProfesionalModel).where(
                ProfesionalModel.tenant_id == turno.tenant_id,
                ProfesionalModel.id == profesional_id,
                ProfesionalModel.activo.is_(True),
            ).with_for_update()
        ).scalar_one_or_none()
        prestacion = self.session.execute(
            select(PrestacionModel).where(
                PrestacionModel.tenant_id == turno.tenant_id,
                PrestacionModel.id == prestacion_id,
                PrestacionModel.activa.is_(True),
            )
        ).scalar_one_or_none()
        if profesional is None or prestacion is None:
            raise LookupError("El horario solicitado no existe.")
        inicio_utc = inicio.astimezone(timezone.utc)
        fin_utc = inicio_utc + timedelta(minutes=prestacion.duracion_min)
        collision = self.session.execute(
            select(TurnoModel).where(
                TurnoModel.tenant_id == turno.tenant_id,
                TurnoModel.profesional_id == profesional.id,
                TurnoModel.estado.in_(("confirmado", "pendiente_confirmacion")),
                TurnoModel.inicio < fin_utc,
                TurnoModel.fin > inicio_utc,
            )
        ).scalar_one_or_none()
        if collision is not None:
            alternatives = candidatos_disponibles(
                self.session,
                tenant_id=turno.tenant_id,
                profesional_id=profesional.id,
                prestacion_id=prestacion.id,
                desde=inicio_utc,
                hasta=inicio_utc + timedelta(days=14),
                ahora_utc=now,
            )
            raise PublicSlotConflictError(alternatives)
        turno.estado = "reprogramado"
        nuevo = TurnoModel(
            id=str(uuid.uuid4()),
            tenant_id=turno.tenant_id,
            paciente_id=turno.paciente_id,
            profesional_id=profesional.id,
            profesional_usuario_id=profesional.usuario_id,
            prestacion_id=prestacion.id,
            inicio=inicio_utc,
            fin=fin_utc,
            estado="pendiente_confirmacion",
            origen="reserva_publica",
        )
        self.session.add(nuevo)
        self.session.flush()
        # C-12 (D4): arrastre de la seña acreditada al nuevo turno; si el
        # nuevo no requiere seña, queda como saldo a favor del paciente.
        SeniaService(self.session).arrastrar(
            turno_viejo=turno,
            turno_nuevo=nuevo,
            prestacion_nueva=prestacion,
        )
        self.session.add(PublicAuditModel(
            tenant_id=turno.tenant_id,
            turno_id=nuevo.id,
            action="reprogramar",
            outcome="creada",
        ))
        checkout_url: str | None = None
        if nuevo.senia_id:
            checkout_url = self._checkout_replay(nuevo)
        return self._response(nuevo, now, checkout_url=checkout_url)

    def _checkout_replay(self, turno: TurnoModel) -> str | None:
        """Recupera el `init_point` de la preferencia para reintentos."""
        if turno.senia_id is None:
            return None
        senias = SeniaService(self.session)
        senia = senias.get(turno.tenant_id, turno.senia_id)
        if senia is None or senia.estado != "pendiente":
            return None
        if senias.mp is None:
            return ""
        try:
            preferencia = senias.mp.obtener_preferencia(
                preference_id=senia.mp_preference_id
            )
        except Exception:  # noqa: BLE001 — RN-GL-03
            return ""
        return preferencia.get("init_point") or ""

    def _response(
        self,
        turno: TurnoModel,
        now: datetime,
        issue_tokens: bool = True,
        checkout_url: str | None = None,
    ) -> PublicBookingResponse:
        tokens: dict[str, str] = {}
        if issue_tokens:
            for purpose in PURPOSES:
                raw = secrets.token_urlsafe(32)
                self.session.add(PublicTokenModel(
                    tenant_id=turno.tenant_id,
                    turno_id=turno.id,
                    token_hash=_hash(raw),
                    purpose=purpose,
                    expires_at=turno.fin + PUBLIC_TOKEN_TTL,
                ))
                tokens[purpose] = raw
        return PublicBookingResponse(
            turno_id=turno.id,
            estado=turno.estado,
            action_tokens=tokens,
            checkout_url=checkout_url,
        )


def release_expired_pending_payments(session: Session, now: datetime) -> int:
    """Libera reservas públicas con seña pendiente sin acreditar pagos."""
    candidates = session.execute(
        select(TurnoModel).join(
            PublicAuditModel,
            (PublicAuditModel.tenant_id == TurnoModel.tenant_id)
            & (PublicAuditModel.turno_id == TurnoModel.id)
            & (PublicAuditModel.action == "reserva")
            & (PublicAuditModel.outcome == "creada"),
        ).where(
            TurnoModel.estado == "pendiente_confirmacion",
            TurnoModel.senia_pendiente_definicion.is_(True),
        ).distinct()
    ).scalars().all()
    expired = []
    for turno in candidates:
        config = session.get(ConfigModel, turno.tenant_id)
        if config is None:
            continue
        created_at = session.execute(
            select(PublicAuditModel.occurred_at).where(
                PublicAuditModel.tenant_id == turno.tenant_id,
                PublicAuditModel.turno_id == turno.id,
                PublicAuditModel.action == "reserva",
                PublicAuditModel.outcome == "creada",
            ).order_by(PublicAuditModel.occurred_at)
        ).scalar_one()
        if created_at <= now - timedelta(minutes=config.public_payment_timeout_min):
            expired.append(turno)
    released = 0
    for turno in expired:
        turno.estado = "cancelado"
        turno.cancelled_at = now
        turno.cancelled_by = "payment_timeout"
        turno.motivo = "Seña no acreditada dentro del plazo"
        # C-12: la seña pendiente queda `devuelta` sin crédito (no se pagó).
        SeniaService(session).marcar_timeout(turno)
        PublicTokenRepository(session).revoke_for_turno(
            tenant_id=turno.tenant_id,
            turno_id=turno.id,
            revoked_at=now,
            reason="payment_timeout",
        )
        session.add(PublicAuditModel(
            tenant_id=turno.tenant_id,
            turno_id=turno.id,
            action="payment_timeout",
            outcome="released",
        ))
        from app.modules.lista_espera.service import Hueco, ListaEsperaService

        hueco = Hueco(
            profesional_id=turno.profesional_id,
            inicio=turno.inicio,
            fin=turno.fin,
            prestacion_id=turno.prestacion_id,
        )
        svc_le = ListaEsperaService(session, now)
        svc_le.ofrecer_por_hueco(turno.tenant_id, hueco, now)
        released += 1
    session.flush()
    return released


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


PUBLIC_RATE_LIMITER = InMemoryRateLimiter()


def _fingerprint(request: PublicBookingRequest) -> str:
    payload = request.model_dump(mode="json")
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

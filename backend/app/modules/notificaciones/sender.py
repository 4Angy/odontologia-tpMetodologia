"""Sender: reclama envíos vencidos y los entrega (D7, D8, D9)."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.agenda.models import ConfigModel, TurnoModel, TenantModel
from app.modules.agenda.repository import ConfigRepository, TurnoRepository
from app.modules.pacientes.models import PacienteModel, OptInModel
from app.modules.agenda.public_booking import PublicTokenModel

from app.modules.notificaciones.models import NotificacionEnvioModel, PlantillaModel
from app.modules.notificaciones.repository import NotificacionEnvioRepository, PlantillaRepository
from app.modules.notificaciones.whatsapp import WhatsAppClient, EnvioResultado
from app.modules.notificaciones.email import EmailClient, EmailResultado

BACKOFF = [timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=15)]
MAX_INTENTOS = 3
PUBLIC_TOKEN_TTL = timedelta(hours=72)


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _render(cuerpo: str, paciente: PacienteModel, fecha: datetime, link: str) -> str:
    return (
        cuerpo.replace("{{paciente}}", f"{paciente.nombre} {paciente.apellido}".strip())
        .replace("{{fecha}}", fecha.astimezone(timezone.utc).isoformat())
        .replace("{{link}}", link)
    )


class SenderService:
    def __init__(
        self,
        session: Session,
        *,
        whatsapp: WhatsAppClient,
        email: EmailClient,
        now: datetime,
        public_base_url: str | None = None,
        limit: int = 50,
    ) -> None:
        self.session = session
        self.whatsapp = whatsapp
        self.email = email
        self.now = _utc(now)
        self.limit = limit
        self.public_base_url = public_base_url or get_settings().public_base_url
        self.repo = NotificacionEnvioRepository(session)
        self.plantillas = PlantillaRepository(session)

    def ejecutar(self) -> list[NotificacionEnvioModel]:
        procesados: list[NotificacionEnvioModel] = []
        vencidos = self.repo.reclamar_vencidos(None, self.now, self.limit)
        for envio in vencidos:
            self.procesar(envio)
            procesados.append(envio)
        self.session.flush()
        return procesados

    def procesar(self, envio: NotificacionEnvioModel) -> None:
        envio.intentos = (envio.intentos or 0) + 1
        turno = None
        if envio.turno_id:
            turno = self.session.execute(
                select(TurnoModel).where(
                    TurnoModel.tenant_id == envio.tenant_id,
                    TurnoModel.id == envio.turno_id,
                )
            ).scalar_one_or_none()
        # Cancelación por estado del turno
        if turno is not None and turno.estado not in ("confirmado", "pendiente_confirmacion"):
            self._cancelar(envio, "turno_cancelado" if turno.estado == "cancelado" else "turno_reprogramado")
            return
        if turno is None and envio.turno_id is not None:
            self._cancelar(envio, "turno_cancelado")
            return

        paciente = self.session.get(PacienteModel, envio.paciente_id)
        if paciente is None or paciente.tenant_id != envio.tenant_id:
            self._fallar(envio, "RN-AU-01", transitorio=False)
            return

        config = ConfigRepository(self.session).get(envio.tenant_id)
        tenant = self.session.get(TenantModel, envio.tenant_id)

        if envio.canal == "whatsapp":
            optin = self.session.execute(
                select(OptInModel).where(
                    OptInModel.tenant_id == envio.tenant_id,
                    OptInModel.paciente_id == envio.paciente_id,
                    OptInModel.canal == "whatsapp",
                )
            ).scalar_one_or_none()
            if optin is None or not bool(optin.estado) or not paciente.telefono:
                self._cancelar(envio, "optin_revocado")
                return
            plantilla = self.plantillas.get(envio.tenant_id, envio.plantilla_codigo, "whatsapp")
            if plantilla is None:
                self._fallar(envio, "plantilla_no_configurada", transitorio=False)
                return
            costo = int(config.whatsapp_costo_centavos) if config is not None else 0
            link = self._link_confirmacion(envio, turno, tenant)
            fecha = turno.inicio if turno is not None else self.now
            cuerpo = _render(plantilla.cuerpo, paciente, fecha, link)
            resultado = self.whatsapp.enviar(
                telefono=paciente.telefono,
                cuerpo=cuerpo,
                idempotency_key=envio.id,
            )
            self._registrar_resultado(envio, resultado, costo, fallback_email=(paciente.email is not None))
            return

        # email
        if not paciente.email:
            self._fallar(envio, "RN-PA-01", transitorio=False)
            return
        plantilla = self.plantillas.get(envio.tenant_id, envio.plantilla_codigo, "email")
        if plantilla is None:
            self._fallar(envio, "plantilla_no_configurada", transitorio=False)
            return
        link = self._link_confirmacion(envio, turno, tenant) if turno is not None else ""
        fecha = turno.inicio if turno is not None else self.now
        cuerpo = _render(plantilla.cuerpo, paciente, fecha, link)
        asunto = plantilla.asunto or "Recordatorio"
        resultado = self.email.enviar(destinatario=paciente.email, asunto=asunto, cuerpo=cuerpo)
        er = resultado
        if er.ok:
            envio.estado = "enviada"
            envio.provider_msg_id = er.message_id
            envio.enviado_at = self.now
            envio.costo_estimado_centavos = 0
            envio.ultimo_error_code = None
        else:
            self._aplicar_fallo(envio, er.error_code or "RN-GL-03", er.transitorio)

    def _link_confirmacion(self, envio, turno, tenant) -> str:
        raw = secrets.token_urlsafe(32)
        if turno is not None:
            token = PublicTokenModel(
                tenant_id=envio.tenant_id,
                turno_id=turno.id,
                token_hash=hashlib.sha256(raw.encode()).hexdigest(),
                purpose="confirm",
                expires_at=turno.fin + PUBLIC_TOKEN_TTL,
            )
            self.session.add(token)
            self.session.flush()
            slug = tenant.slug if tenant is not None else envio.tenant_id
            return f"{self.public_base_url}/r/{slug}/confirmar?token={raw}"
        return ""

    def _registrar_resultado(self, envio, resultado: EnvioResultado, costo: int, fallback_email: bool) -> None:
        if resultado.ok:
            envio.estado = "enviada"
            envio.provider_msg_id = resultado.provider_msg_id
            envio.enviado_at = self.now
            envio.costo_estimado_centavos = costo
            envio.ultimo_error_code = None
            return
        envio.ultimo_error_code = resultado.error_code
        if resultado.transitorio:
            if envio.intentos >= MAX_INTENTOS:
                envio.estado = "fallida"
                if fallback_email:
                    self._encolar_email(envio)
            else:
                envio.estado = "encolada"
                idx = min(envio.intentos - 1, len(BACKOFF) - 1)
                envio.next_attempt_at = self.now + BACKOFF[idx]
        else:
            envio.estado = "fallida"
            if fallback_email:
                self._encolar_email(envio)

    def _aplicar_fallo(self, envio, code: str, transitorio: bool) -> None:
        envio.ultimo_error_code = code
        if transitorio:
            if envio.intentos >= MAX_INTENTOS:
                envio.estado = "fallida"
            else:
                envio.estado = "encolada"
                idx = min(envio.intentos - 1, len(BACKOFF) - 1)
                envio.next_attempt_at = self.now + BACKOFF[idx]
        else:
            envio.estado = "fallida"

    def _cancelar(self, envio, motivo: str) -> None:
        envio.estado = "cancelada"
        envio.motivo_code = motivo
        envio.ultimo_error_code = None

    def _fallar(self, envio, code: str, transitorio: bool) -> None:
        envio.estado = "fallida"
        envio.ultimo_error_code = code

    def _encolar_email(self, envio: NotificacionEnvioModel) -> None:
        email_envio = NotificacionEnvioModel(
            id=str(uuid.uuid4()),
            tenant_id=envio.tenant_id,
            paciente_id=envio.paciente_id,
            turno_id=envio.turno_id,
            canal="email",
            plantilla_codigo=envio.plantilla_codigo,
            ventana=envio.ventana,
            estado="encolada",
            motivo_code="RN-PA-04",
            intentos=0,
            next_attempt_at=self.now,
            costo_estimado_centavos=0,
        )
        self.repo.insertar_si_no_existe(email_envio)


__all__ = ["SenderService", "BACKOFF", "MAX_INTENTOS"]

"""Servicio de dominio para lista de espera (C-10)."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.agenda.models import ConfigModel, PublicTokenModel, TenantModel, TurnoModel
from app.modules.agenda.repository import PublicTokenRepository, TurnoRepository
from app.modules.lista_espera.models import ListaEsperaModel
from app.modules.lista_espera.repository import ListaEsperaRepository
from app.modules.notificaciones.models import NotificacionEnvioModel
from app.modules.notificaciones.repository import NotificacionEnvioRepository
from app.modules.pacientes.models import OptInModel, PacienteModel


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _a_utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} debe incluir zona horaria")
    return value.astimezone(timezone.utc)


class ListaEsperaError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class Hueco:
    def __init__(self, profesional_id: str, inicio: datetime, fin: datetime, prestacion_id: str | None = None) -> None:
        self.profesional_id = profesional_id
        self.inicio = _a_utc(inicio, "inicio")
        self.fin = _a_utc(fin, "fin")
        self.prestacion_id = prestacion_id


class ListaEsperaService:
    def __init__(self, session: Session, now: datetime | None = None) -> None:
        self.session = session
        self.now = now or datetime.now(timezone.utc)
        self.repo = ListaEsperaRepository(session)
        self.turnos_repo = TurnoRepository(session)
        self.tokens_repo = PublicTokenRepository(session)
        self.notif_repo = NotificacionEnvioRepository(session)

    def _tenant_by_slug(self, slug: str) -> TenantModel:
        tenant = self.session.execute(
            select(TenantModel).where(TenantModel.slug == slug)
        ).scalar_one_or_none()
        if tenant is None:
            raise ListaEsperaError("RN-AU-01", "Tenant no encontrado.", 404)
        return tenant

    def _ttl_hs(self, tenant_id: str) -> int:
        cfg = self.session.get(ConfigModel, tenant_id)
        if cfg is None:
            return 2
        return int(getattr(cfg, "lista_espera_ttl_hs", 2) or 2)

    def _paciente_tiene_optin_whatsapp(self, tenant_id: str, paciente_id: str) -> bool:
        paciente = self.session.execute(
            select(PacienteModel).where(
                PacienteModel.tenant_id == tenant_id,
                PacienteModel.id == paciente_id,
            )
        ).scalar_one_or_none()
        if paciente is None or not paciente.telefono:
            return False
        for optin in paciente.optins or []:
            if optin.canal == "whatsapp" and bool(optin.estado):
                return True
        return False

    def _costo_centavos(self, tenant_id: str) -> int:
        cfg = self.session.get(ConfigModel, tenant_id)
        if cfg is None:
            return 0
        return int(cfg.whatsapp_costo_centavos or 0)

    def _encolar_envio(
        self,
        *,
        tenant_id: str,
        paciente_id: str,
        estado: str,
        motivo_code: str | None,
        now: datetime,
    ) -> NotificacionEnvioModel:
        envio = NotificacionEnvioModel(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            paciente_id=paciente_id,
            turno_id=None,
            canal="whatsapp",
            plantilla_codigo="lista_espera",
            ventana=None,
            estado=estado,
            motivo_code=motivo_code,
            intentos=0,
            next_attempt_at=now,
            costo_estimado_centavos=self._costo_centavos(tenant_id) if estado == "encolada" else 0,
        )
        self.session.add(envio)
        self.session.flush()
        return envio

    def _generar_tokens(self, tenant_id: str, entry_id: str, expires_at: datetime) -> dict[str, str]:
        tokens: dict[str, str] = {}
        for purpose in ("waitlist_accept", "waitlist_decline"):
            raw = secrets.token_urlsafe(32)
            self.session.add(
                PublicTokenModel(
                    tenant_id=tenant_id,
                    turno_id=entry_id,
                    token_hash=_hash(raw),
                    purpose=purpose,
                    expires_at=expires_at,
                )
            )
            tokens[purpose] = raw
        self.session.flush()
        return tokens

    def ofrecer_por_hueco(
        self, tenant_id: str, hueco: Hueco, now: datetime | None = None
    ) -> ListaEsperaModel | None:
        now = now or self.now
        ttl_hs = self._ttl_hs(tenant_id)
        expires_at = now + timedelta(hours=ttl_hs)
        candidatos = self.repo.list_activas_compatibles(
            tenant_id, hueco.profesional_id, hueco.prestacion_id
        )
        for entry in candidatos:
            if not self._paciente_tiene_optin_whatsapp(tenant_id, entry.paciente_id):
                self._encolar_envio(
                    tenant_id=tenant_id,
                    paciente_id=entry.paciente_id,
                    estado="omitida",
                    motivo_code="RN-PA-01",
                    now=now,
                )
                continue
            entry.estado = "ofrecida"
            entry.hueco_profesional_id = hueco.profesional_id
            entry.hueco_inicio = hueco.inicio
            entry.hueco_fin = hueco.fin
            entry.hueco_prestacion_id = hueco.prestacion_id
            entry.ofrecido_at = now
            entry.expires_at = expires_at
            self.repo.update(entry)
            self._encolar_envio(
                tenant_id=tenant_id,
                paciente_id=entry.paciente_id,
                estado="encolada",
                motivo_code=None,
                now=now,
            )
            self._generar_tokens(tenant_id, entry.id, expires_at)
            return entry
        return None

    def vencer_y_avanzar(self, now: datetime | None = None) -> int:
        now = now or self.now
        vencidas = self.repo.list_ofrecidas_vencidas(now)
        procesadas = 0
        for entry in vencidas:
            hueco = Hueco(
                profesional_id=entry.hueco_profesional_id or "",
                inicio=entry.hueco_inicio or now,
                fin=entry.hueco_fin or now,
                prestacion_id=entry.hueco_prestacion_id,
            )
            entry.estado = "vencida"
            self.repo.update(entry)
            self.ofrecer_por_hueco(entry.tenant_id, hueco, now)
            procesadas += 1
        return procesadas

    def _token_valido(self, raw_token: str, purpose: str, now: datetime) -> PublicTokenModel:
        token_hash = _hash(raw_token)
        stmt = select(PublicTokenModel).where(
            PublicTokenModel.token_hash == token_hash,
            PublicTokenModel.purpose == purpose,
            PublicTokenModel.revoked_at.is_(None),
            PublicTokenModel.expires_at > now,
        )
        token = self.session.execute(stmt).scalar_one_or_none()
        if token is None:
            raise ListaEsperaError("RN-AU-01", "Token invalido o expirado.", 404)
        return token

    def aceptar(self, raw_token: str, tenant_slug: str | None = None, now: datetime | None = None) -> tuple[ListaEsperaModel, TurnoModel]:
        now = now or self.now
        token = self._token_valido(raw_token, "waitlist_accept", now)
        if tenant_slug is None:
            tenant = self.session.get(TenantModel, token.tenant_id)
            if tenant is None:
                raise ListaEsperaError("RN-AU-01", "Tenant no encontrado.", 404)
        else:
            tenant = self._tenant_by_slug(tenant_slug)
        if token.tenant_id != tenant.id:
            raise ListaEsperaError("RN-AU-01", "Token invalido o expirado.", 404)
        entry = self.repo.get_by_id(tenant.id, token.turno_id)
        if entry is None or entry.estado != "ofrecida":
            raise ListaEsperaError("RN-AG-08", "La oferta ya no esta vigente.", 409)
        if entry.expires_at is not None and entry.expires_at <= now:
            raise ListaEsperaError("RN-AG-08", "La oferta expiro.", 409)
        if not entry.hueco_profesional_id or not entry.hueco_inicio or not entry.hueco_fin:
            raise ListaEsperaError("RN-GL-02", "Hueco invalido.", 422)

        profesional = self.turnos_repo.lock_profesional(tenant.id, entry.hueco_profesional_id)
        if profesional is None:
            raise ListaEsperaError("RN-AU-01", "Profesional no encontrado.", 404)

        solapados = self.turnos_repo.list_solapados(
            tenant_id=tenant.id,
            profesional_id=entry.hueco_profesional_id,
            inicio=entry.hueco_inicio,
            fin=entry.hueco_fin,
        )
        if solapados:
            entry.estado = "activa"
            entry.hueco_profesional_id = None
            entry.hueco_inicio = None
            entry.hueco_fin = None
            entry.hueco_prestacion_id = None
            entry.ofrecido_at = None
            entry.expires_at = None
            self.repo.update(entry)
            raise ListaEsperaError("RN-AG-03", "El hueco ya no esta disponible.", 409)

        turno = TurnoModel(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            paciente_id=entry.paciente_id,
            profesional_id=entry.hueco_profesional_id,
            profesional_usuario_id=profesional.usuario_id,
            prestacion_id=entry.hueco_prestacion_id,
            inicio=entry.hueco_inicio,
            fin=entry.hueco_fin,
            estado="confirmado",
            origen="lista_espera",
        )
        self.turnos_repo.create(turno)
        entry.estado = "convertida"
        self.repo.update(entry)
        self.tokens_repo.revoke_for_turno(
            tenant_id=tenant.id, turno_id=entry.id, revoked_at=now, reason="waitlist_accepted"
        )
        return entry, turno

    def declinar(self, raw_token: str, tenant_slug: str | None = None, now: datetime | None = None) -> ListaEsperaModel:
        now = now or self.now
        token = self._token_valido(raw_token, "waitlist_decline", now)
        if tenant_slug is None:
            tenant = self.session.get(TenantModel, token.tenant_id)
            if tenant is None:
                raise ListaEsperaError("RN-AU-01", "Tenant no encontrado.", 404)
        else:
            tenant = self._tenant_by_slug(tenant_slug)
        if token.tenant_id != tenant.id:
            raise ListaEsperaError("RN-AU-01", "Token invalido o expirado.", 404)
        entry = self.repo.get_by_id(tenant.id, token.turno_id)
        if entry is None or entry.estado != "ofrecida":
            raise ListaEsperaError("RN-AG-08", "La oferta ya no esta vigente.", 409)
        hueco = Hueco(
            profesional_id=entry.hueco_profesional_id or "",
            inicio=entry.hueco_inicio or now,
            fin=entry.hueco_fin or now,
            prestacion_id=entry.hueco_prestacion_id,
        )
        entry.estado = "vencida"
        self.repo.update(entry)
        self.tokens_repo.revoke_for_turno(
            tenant_id=tenant.id, turno_id=entry.id, revoked_at=now, reason="waitlist_declined"
        )
        self.ofrecer_por_hueco(tenant.id, hueco, now)
        return entry

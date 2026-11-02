"""Lógica de negocio de sesión (C-03): login, refresh, logout, me, reset.

Los errores se levantan como `AppError` (`{code, message}`) del contrato
único de la API (R9). Toda operación escribe/lee `auth_token` vía
`AuthTokenRepository` (estado duradero en Postgres — design decisión 1).
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import log_event
from app.core.rate_limit import RateLimiter, RateLimitResult
from app.core.security import mint_token
from app.modules.agenda.models import TenantModel, UsuarioModel
from app.modules.auth.models import PropositoToken
from app.modules.auth.passwords import verificar_password
from app.modules.auth.repository import AuthTokenRepository

logger = logging.getLogger("odontologia.auth")

_UTC = timezone.utc

#: Mensaje genérico de credenciales (anti-enumeración: idéntico en casos).
MSJ_CREDENCIALES_INVALIDAS = "Email o password incorrectos."
#: Mensaje de reset genérico (no revela si el email existe).
MSJ_RESET_GENERICO = (
    "Si el email está registrado en el sistema, te enviamos el enlace para "
    "cambiar tu password."
)

VENTANA_RESET_HORAS = 1


@dataclass(frozen=True)
class SesionEmitida:
    """Resultado de login/refresh: el access va al body, el refresh a cookie."""

    access_token: str
    expires_in: int
    refresh_jti: str
    refresh_expira: datetime


class AuthService:
    """Servicio de todas las operaciones de sesión."""

    def __init__(self, session: Session, rate_limiter: RateLimiter | None = None) -> None:
        self._session = session
        self._settings = get_settings()
        self._rate_limiter = rate_limiter

    # --- login (task 2.2) ---------------------------------------------------

    def login(
        self,
        *,
        email: str,
        password: str,
        now: datetime,
        tenant_slug: str | None = None,
        client_ip: str | None = None,
    ) -> SesionEmitida:
        """Autentica por email + password y emite access + refresh (cookie a nivel router)."""
        email_norm = email.strip().lower()

        # Rate limit 5/60s por IP+email (task 3.3)
        if self._rate_limiter and client_ip:
            key = f"{client_ip}:{email_norm}"
            resultado = self._rate_limiter.check(key, limit=5, window_seconds=60)
            if not resultado.allowed:
                raise AppError(
                    code="RN-AU-03",
                    message="Demasiados intentos. Esperá unos minutos antes de volver a intentar.",
                    status_code=429,
                )

        usuarios = self._session.scalars(
            select(UsuarioModel).where(
                UsuarioModel.email == email_norm,
                UsuarioModel.deleted_at.is_(None),
            )
        ).all()

        if not usuarios:
            # Trabajo comparable para no filtrar por demora que el email no existe.
            verificar_password(password, None)
            self._log_evento("login_fallido", reason="sin_usuario", patron="")
            raise AppError(
                code="RN-AU-01",
                message=MSJ_CREDENCIALES_INVALIDAS,
                status_code=401,
            )

        usuario = self._resolver_unicidad(usuarios, email_norm, tenant_slug)

        if not verificar_password(password, usuario.password_hash):
            self._log_evento(
                "login_fallido", reason="password_incorrecta",
                usuario_id=usuario.id, tenant_id=usuario.tenant_id,
            )
            raise AppError(code="RN-AU-01", message=MSJ_CREDENCIALES_INVALIDAS, status_code=401)

        if not usuario.activo:
            self._log_evento(
                "login_fallido", reason="usuario_inactivo",
                usuario_id=usuario.id, tenant_id=usuario.tenant_id,
            )
            raise AppError(
                code="RN-AU-01",
                message="Tu usuario está inactivo. Contactá al dueño del consultorio.",
                status_code=403,
            )

        self._purgar(now)
        return self._emitir(usuario=usuario, now=now)

    # --- refresh (task 2.3) -------------------------------------------------

    def refresh(self, *, refresh_jti: str, now: datetime) -> SesionEmitida:
        """Rota el refresh: valida contra `auth_token`, detecta reuse (RN-AU-02)."""
        repo = AuthTokenRepository(self._session)  # cookie es jti global único
        fila = repo.obtener(refresh_jti)

        if fila is not None:
            estado = repo.estado(fila, now=now)
            if estado.es_reuse:
                revocadas = repo.revocar_familia(fila.familia_id, now=now)
                self._session.commit()
                self._log_evento(
                    "reuse_detectado",
                    familia=fila.familia_id,
                    usuario_id=fila.usuario_id,
                    filas_revocadas=revocadas,
                )
                fila = None  # cae al error RN-AU-02
            elif not estado.dentro_de_plazo:
                fila = None  # expirado: mismo sobre, sin revelar cuál

        if fila is None:
            raise AppError(
                code="RN-AU-02",
                message="Tu sesión expiró o fue revocada. Iniciá sesión de nuevo.",
                status_code=401,
            )

        usuario = self._session.get(UsuarioModel, fila.usuario_id)
        if (
            usuario is None
            or usuario.tenant_id != fila.tenant_id
            or usuario.deleted_at is not None
        ):
            repo.revocar_familia(fila.familia_id, now=now)
            self._session.commit()
            raise AppError(
                code="RN-AU-02",
                message="Tu sesión expiró o fue revocada. Iniciá sesión de nuevo.",
                status_code=401,
            )
        if not usuario.activo:
            repo.revocar_familia(fila.familia_id, now=now)
            self._session.commit()
            raise AppError(
                code="RN-AU-01",
                message="Tu usuario está inactivo. Contactá al dueño del consultorio.",
                status_code=403,
            )

        nueva = repo.rotar(
            jti_viejo=fila.id,
            jti_nuevo=str(uuid.uuid4()),
            expira=now + timedelta(days=self._settings.jwt_refresh_days),
            now=now,
        )
        if nueva is None:  # carreras: la fila desapareció entre leer y rotar
            self._session.commit()
            raise AppError(
                code="RN-AU-02",
                message="Tu sesión expiró o fue revocada. Iniciá sesión de nuevo.",
                status_code=401,
            )
        self._session.commit()
        self._purgar(now)
        return self._emitir(usuario=usuario, now=now, familia_id=fila.familia_id)

    # --- logout (task 2.4) --------------------------------------------------

    def logout(self, *, refresh_jti: str | None, now: datetime) -> None:
        """Revoca la familia del refresh y limpia estado. Idempotente."""
        if not refresh_jti:
            return
        repo = AuthTokenRepository(self._session)
        fila = repo.obtener(refresh_jti, proposito=None)
        if fila is not None:
            revocadas = repo.revocar_familia(fila.familia_id, now=now)
            self._session.commit()
            self._log_evento("logout", familia=fila.familia_id, filas_revocadas=revocadas)
        return None

    # --- me (task 2.5) ------------------------------------------------------

    def me(self, *, usuario_id: str, tenant_id: str) -> dict:
        """Identidad vigente + permiso efectivo = unión de roles (RN-AU-04)."""
        usuario = self._session.scalars(
            select(UsuarioModel).where(
                UsuarioModel.id == usuario_id,
                UsuarioModel.tenant_id == tenant_id,
                UsuarioModel.deleted_at.is_(None),
            )
        ).first()
        if usuario is None:
            raise AppError(
                code="RN-AU-01",
                message="Credenciales inválidas o ausentes.",
                status_code=403,
            )
        roles = list(usuario.roles)
        return {
            "sub": usuario.id,
            "email": usuario.email,
            "nombre": usuario.nombre,
            "roles": roles,
            # La unión explícita (ded-up + orden estable) la deriva el backend:
            # el frontend no vuelve a decidir el modelo de permisos.
            "permisos": sorted(set(roles)),
        }

    # --- reset de password (task 2.6) ----------------------------------------

    def reset_solicitar(self, *, email: str, now: datetime) -> dict:
        """Emite token de uso único con 1h de vigencia (respuesta genérica)."""
        email_norm = email.strip().lower()
        usuarios = self._session.scalars(
            select(UsuarioModel).where(
                UsuarioModel.email == email_norm,
                UsuarioModel.deleted_at.is_(None),
            )
        ).all()
        token: str | None = None
        if len(usuarios) == 1:
            token = str(uuid.uuid4())
            repo = AuthTokenRepository(self._session)
            repo.crear(
                jti=token,
                usuario_id=usuarios[0].id,
                familia_id=str(uuid.uuid4()),
                proposito=PropositoToken.RESET,
                expira=now + timedelta(hours=VENTANA_RESET_HORAS),
                tenant_id=usuarios[0].tenant_id,
                now=now,
            )
            self._session.commit()
            self._log_evento("reset_solicitado", usuario_id=usuarios[0].id, tenant_id=usuarios[0].tenant_id)
        # Respuesta idéntica si el email no existe (anti-enumeración).
        respuesta = {"message": MSJ_RESET_GENERICO, "token": token}
        if self._settings.app_env == "prod":
            respuesta["token"] = None
        self._purgar(now)
        return respuesta

    def reset_confirmar(self, *, token: str, nueva_password: str, now: datetime) -> dict:
        """Cambia la password con el token; invalida el token y las familias previas."""
        repo = AuthTokenRepository(self._session)
        fila = repo.obtener(token, proposito=PropositoToken.RESET)
        invalido = (
            fila is None
            or fila.revoked
            or fila.used_at is not None
            or fila.expira <= now
        )
        if invalido:
            raise AppError(
                code="RN-AU-01",
                message="El enlace no es válido o ya fue usado. Pedí uno nuevo.",
                status_code=400,
            )
        from app.modules.auth.passwords import hash_password

        usuario = self._session.get(UsuarioModel, fila.usuario_id)
        if usuario is None or usuario.tenant_id != fila.tenant_id:
            raise AppError(
                code="RN-AU-01",
                message="El enlace no es válido o ya fue usado. Pedí uno nuevo.",
                status_code=400,
            )
        usuario.password_hash = hash_password(nueva_password)
        repo.marcar_usado_reset(fila.id, now=now)
        repo.revocar_de_usuario(fila.usuario_id, now=now)  # fuerza re-login (spec)
        self._session.commit()
        self._log_evento("reset_usado", usuario_id=usuario.id, tenant_id=usuario.tenant_id)
        return {"message": "Tu password cambió. Iniciá sesión con la nueva."}

    # --- helpers ------------------------------------------------------------

    def _resolver_unicidad(
        self, usuarios: list[UsuarioModel], email_norm: str, tenant_slug: str | None
    ) -> UsuarioModel:
        """El email es único por tenant: puede repetirse entre consultorios.

        SIEMPRE que un email aparezca en 2+ tenants se exige `tenant_slug`
        para elegir; si falta, 409 con mensaje accionable (no se revela cuándo
        es válido el password de cada uno).
        """
        if len(usuarios) == 1:
            return usuarios[0]
        if tenant_slug:
            slugs = {
                fila.tenant_id: fila.slug
                for fila in self._session.scalars(
                    select(TenantModel).where(TenantModel.slug == tenant_slug)
                ).all()
            }
            for usuario in usuarios:
                if slugs.get(usuario.tenant_id):
                    return usuario
        raise AppError(
            code="RN-GL-00",
            message=(
                "Este email está asociado a más de un consultorio. "
                "Iniciá sesión desde el link de tu consultorio."
            ),
            status_code=409,
        )

    def _emitir(
        self, *, usuario: UsuarioModel, now: datetime, familia_id: str | None = None
    ) -> SesionEmitida:
        """Crea (o continúa) una familia y emite la pareja de tokens."""
        familia = familia_id or str(uuid.uuid4())
        repo = AuthTokenRepository(self._session, tenant_id=usuario.tenant_id)
        refresh_jti = str(uuid.uuid4())
        expira = now + timedelta(days=self._settings.jwt_refresh_days)
        repo.crear(
            jti=refresh_jti,
            usuario_id=usuario.id,
            familia_id=familia,
            proposito=PropositoToken.REFRESH,
            expira=expira,
            now=now,
        )
        self._session.commit()
        access = mint_token(
            user_id=usuario.id,
            tenant_id=usuario.tenant_id,
            roles=list(usuario.roles),
            email=usuario.email,
            token_type="access",
            now=now,
        )
        return SesionEmitida(
            access_token=access,
            expires_in=self._settings.jwt_access_min * 60,
            refresh_jti=refresh_jti,
            refresh_expira=expira,
        )

    def _purgar(self, now: datetime) -> None:
        """Purge cheap de tokens vencidos en el mismo flujo (design riesgo 1)."""
        repo = AuthTokenRepository(self._session)
        borrados = repo.purgar_expirados(now=now)
        if borrados:
            self._session.commit()

    def _log_evento(self, evento: str, **datos: object) -> None:
        """Registro de seguridad estructurado con contexto (task 3.4)."""
        log_event(logger, logging.INFO, f"auth.{evento}", **datos)


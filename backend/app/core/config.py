"""Configuración del backend por variables de entorno (C-01).

Fuente única de configuración. 14 variables canónicas de dominio + variables
operativas (`APP_ENV`, `LOG_LEVEL`).

Reglas duras:
- La configuración se lee SOLO del entorno (`.env` en desarrollo).
- Se valida al arrancar: si algo falta o es inválido, la app NO arranca
  (fail-fast) con un mensaje que nombra la variable y el formato esperado.
- `JWT_SECRET` es obligatoria fuera de `dev`/`test`; en `dev`/`test` se puede
  operar con un valor efímero generado en el proceso (con aviso explícito).
- Los valores sensibles son `SecretStr` y nunca se loguean (ver `core.logging`).
"""
from __future__ import annotations

import logging
import os
import secrets
from functools import lru_cache
from typing import Any, Literal, Mapping
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["dev", "test", "prod"]

#: Las 14 variables canónicas de dominio (KB `08_arquitectura_propuesta.md`).
CANONICAL_ENV_VARS: tuple[str, ...] = (
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_SECRET",
    "JWT_ACCESS_MIN",
    "JWT_REFRESH_DAYS",
    "TENANT_DEFAULT_TZ",
    "WHATSAPP_PROVIDER",
    "WHATSAPP_API_TOKEN",
    "WHATSAPP_PHONE_ID",
    "MP_ACCESS_TOKEN",
    "MP_WEBHOOK_SECRET",
    "SMTP_URL",
    "PUBLIC_BASE_URL",
    "SEED_DEMO",
)

#: Variables operativas (no forman parte del contrato de dominio).
OPERATIONAL_ENV_VARS: tuple[str, ...] = ("APP_ENV", "LOG_LEVEL")

#: Nombre del servicio y versión que expone `/health`.
SERVICE_NAME = "odontologia-api"
SERVICE_VERSION = "0.1.0"

#: Mapeo variable de entorno -> campo de `Settings`.
ENV_BY_FIELD: dict[str, str] = {
    "database_url": "DATABASE_URL",
    "redis_url": "REDIS_URL",
    "jwt_secret": "JWT_SECRET",
    "jwt_access_min": "JWT_ACCESS_MIN",
    "jwt_refresh_days": "JWT_REFRESH_DAYS",
    "tenant_default_tz": "TENANT_DEFAULT_TZ",
    "whatsapp_provider": "WHATSAPP_PROVIDER",
    "whatsapp_api_token": "WHATSAPP_API_TOKEN",
    "whatsapp_phone_id": "WHATSAPP_PHONE_ID",
    "mp_access_token": "MP_ACCESS_TOKEN",
    "mp_webhook_secret": "MP_WEBHOOK_SECRET",
    "smtp_url": "SMTP_URL",
    "public_base_url": "PUBLIC_BASE_URL",
    "seed_demo": "SEED_DEMO",
    "app_env": "APP_ENV",
    "log_level": "LOG_LEVEL",
}
FIELD_BY_ENV: dict[str, str] = {v: k for k, v in ENV_BY_FIELD.items()}

#: Longitud mínima del secreto de firma en entornos que no son de desarrollo.
MIN_JWT_SECRET_LENGTH = 32


class ConfigError(RuntimeError):
    """Configuración inválida o incompleta: la aplicación no debe arrancar."""


class Settings(BaseSettings):
    """Configuración tipada del backend."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        # `extra="ignore"`: el entorno del proceso puede traer variables ajenas.
        extra="ignore",
        case_sensitive=False,
        frozen=True,
    )

    # --- Conexiones ---------------------------------------------------------
    database_url: str
    redis_url: str

    # --- Autenticación (C-03) ----------------------------------------------
    jwt_secret: SecretStr | None = None
    jwt_access_min: int = Field(default=15, ge=1)
    jwt_refresh_days: int = Field(default=7, ge=1)

    # --- Tenant -------------------------------------------------------------
    tenant_default_tz: ZoneInfo = ZoneInfo("America/Argentina/Buenos_Aires")

    # --- Mensajería (ADR-001) ----------------------------------------------
    whatsapp_provider: Literal["official", "gateway"] = "official"
    whatsapp_api_token: SecretStr | None = None
    whatsapp_phone_id: str | None = None

    # --- Mercado Pago (C-12) -----------------------------------------------
    mp_access_token: SecretStr | None = None
    mp_webhook_secret: SecretStr | None = None

    # --- Email fallback (C-09) ---------------------------------------------
    smtp_url: SecretStr | None = None

    # --- Varios -------------------------------------------------------------
    public_base_url: str = "http://localhost:5173"
    seed_demo: bool = False

    # --- Operativas ---------------------------------------------------------
    app_env: AppEnv = "dev"
    log_level: str = "INFO"

    @field_validator("tenant_default_tz", mode="before")
    @classmethod
    def _parsear_zona_horaria(cls, value: Any) -> Any:
        """`ZoneInfo` no se coacciona solo: se resuelve desde el string."""
        if isinstance(value, str):
            return ZoneInfo(value)
        return value

    @property
    def es_desarrollo(self) -> bool:
        return self.app_env in ("dev", "test")

    def jwt_secret_plain(self) -> str:
        """Valor plano del secreto. Solo para firmar tokens; nunca loguear."""
        if self.jwt_secret is None:
            raise ConfigError("JWT_SECRET no está configurada.")
        return self.jwt_secret.get_secret_value()

    def sensitive_values(self) -> tuple[str, ...]:
        """Literales sensibles que el logging debe filtrar."""
        valores: list[str] = []
        for campo in (
            "jwt_secret",
            "whatsapp_api_token",
            "mp_access_token",
            "mp_webhook_secret",
            "smtp_url",
        ):
            valor = getattr(self, campo)
            if isinstance(valor, SecretStr):
                texto = valor.get_secret_value()
                if texto:
                    valores.append(texto)
        return tuple(valores)


def _collect(env: Mapping[str, str]) -> dict[str, Any]:
    """Traduce variables de entorno a kwargs de `Settings` (init > env > dotenv)."""
    datos: dict[str, Any] = {}
    for variable, campo in FIELD_BY_ENV.items():
        if variable in env:
            datos[campo] = env[variable]
    return datos


def _format_validation_error(exc: ValidationError) -> str:
    """Mensaje accionable: nombra la variable de entorno y el formato esperado."""
    lineas: list[str] = []
    for error in exc.errors():
        ubicacion = ".".join(str(parte) for parte in error.get("loc", ())) or "(raíz)"
        variable = ENV_BY_FIELD.get(ubicacion, ubicacion.upper())
        tipo = error.get("type", "valor inválido")
        mensaje = error.get("msg", "valor inválido")
        lineas.append(f"  - {variable}: {mensaje} (se esperaba {tipo})")
    return "Configuración inválida:\n" + "\n".join(lineas)


def _settings_desde_env(env: Mapping[str, str]) -> Settings:
    """Construye `Settings` usando SOLO el env dado.

    `BaseSettings` con `custom_init` mergea las fuentes (entorno y `.env`)
    incluso en `model_validate`, así que se anulan con
    `settings_customise_sources`: con un env explícito manda ese env y nada
    más (los tests no deben depender de la configuración de la máquina).
    """

    class _SoloEnv(Settings):
        @classmethod
        def settings_customise_sources(  # noqa: D102 - firma de pydantic-settings
            cls,
            settings_cls,
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        ):
            return (init_settings,)

    return _SoloEnv(**_collect(env))


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Construye y valida la configuración.

    `env=None` lee el entorno real (variables + `.env`). Con `env` explícito
    (tests) solo se usan esas variables.

    Lanza `ConfigError` con un mensaje accionable si algo falta o es inválido.
    """
    try:
        settings = _settings_desde_env(env) if env is not None else Settings()
    except ValidationError as exc:
        raise ConfigError(_format_validation_error(exc)) from exc

    return _aplicar_reglas(settings)


def _aplicar_reglas(settings: Settings) -> Settings:
    """Reglas que no se pueden expresar como validación de campo."""
    valor = settings.jwt_secret.get_secret_value() if settings.jwt_secret is not None else ""
    if not valor.strip():
        # Ausente o vacía: en ambos casos "falta".
        if not settings.es_desarrollo:
            raise ConfigError(
                "Configuración inválida:\n"
                "  - JWT_SECRET: falta y es obligatoria fuera de dev/test "
                "(generá una con `openssl rand -hex 32`)."
            )
        logging.getLogger("odontologia.config").warning(
            "JWT_SECRET no está configurada: se usa un secreto TEMPORAL "
            "generado en este proceso. Los tokens firmados con él se invalidan "
            "al reiniciar. Sólo se permite en dev/test."
        )
        return settings.model_copy(update={"jwt_secret": SecretStr(secrets.token_hex(32))})

    if not settings.es_desarrollo:
        largo = len(settings.jwt_secret.get_secret_value())
        if largo < MIN_JWT_SECRET_LENGTH:
            raise ConfigError(
                "Configuración inválida:\n"
                f"  - JWT_SECRET: demasiado corto ({largo} caracteres); "
                f"se esperaban al menos {MIN_JWT_SECRET_LENGTH}."
            )
    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Instancia única de configuración del proceso."""
    return load_settings()


def reset_settings_cache() -> None:
    """Limpia la caché de `get_settings` (tests)."""
    get_settings.cache_clear()


__all__ = [
    "AppEnv",
    "CANONICAL_ENV_VARS",
    "OPERATIONAL_ENV_VARS",
    "SERVICE_NAME",
    "SERVICE_VERSION",
    "ConfigError",
    "Settings",
    "get_settings",
    "load_settings",
    "reset_settings_cache",
]

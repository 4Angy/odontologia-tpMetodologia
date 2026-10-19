"""Helpers compartidos por los tests del runtime (C-01)."""
from __future__ import annotations

import pytest

#: Las 14 variables canónicas con valores válidos.
VALIDO: dict[str, str] = {
    "APP_ENV": "test",
    "DATABASE_URL": "postgresql+psycopg://usuario:clave@localhost:5432/odontologia",
    "REDIS_URL": "redis://localhost:6379/0",
    "JWT_SECRET": "s" * 64,
    "JWT_ACCESS_MIN": "15",
    "JWT_REFRESH_DAYS": "7",
    "TENANT_DEFAULT_TZ": "America/Argentina/Buenos_Aires",
    "WHATSAPP_PROVIDER": "official",
    "WHATSAPP_API_TOKEN": "token-de-whatsapp",
    "WHATSAPP_PHONE_ID": "5411000000000",
    "MP_ACCESS_TOKEN": "APP_USR-token-mp",
    "MP_WEBHOOK_SECRET": "secreto-de-webhook",
    "SMTP_URL": "smtp://usuario:clave@smtp.ejemplo.com:587",
    "PUBLIC_BASE_URL": "https://app.ejemplo.com",
    "SEED_DEMO": "false",
}


@pytest.fixture()
def env_valido() -> dict[str, str]:
    """Copia del entorno válido (cada test puede mutarlo sin afectar a otros)."""
    return dict(VALIDO)

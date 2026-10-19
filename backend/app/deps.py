"""Dependencias inyectables: sesión de DB, reloj y sondas de readiness.

La sesión y el reloj se pueden sobreescribir en tests (app sin DB real).
Las sondas (`database_probe`, `redis_probe`) son el punto de extensión de
`GET /health/ready`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from fastapi import Request
from sqlalchemy import Engine, create_engine, text

from app.core.config import get_settings


def get_session(request: Request):  # type: ignore[no-untyped-def]  # resuelto por create_app
    return request.app.state.session_factory()


def get_now() -> datetime:
    return datetime.now(timezone.utc)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Engine SQLAlchemy del proceso (Postgres 16, driver psycopg 3)."""
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


def reset_engine_cache() -> None:
    """Limpia la caché del engine (tests)."""
    get_engine.cache_clear()


def database_probe() -> bool:
    """Sonda de readiness de la base de datos."""
    with get_engine().connect() as conexion:
        conexion.execute(text("SELECT 1"))
    return True


def redis_probe() -> bool:
    """Sonda de readiness de Redis."""
    import redis

    settings = get_settings()
    cliente = redis.Redis.from_url(
        settings.redis_url, socket_connect_timeout=2, socket_timeout=2
    )
    try:
        return bool(cliente.ping())
    finally:
        cliente.close()


__all__ = [
    "database_probe",
    "get_engine",
    "get_now",
    "get_session",
    "redis_probe",
    "reset_engine_cache",
]

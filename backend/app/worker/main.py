"""Worker del backend (C-01 + C-09).

Ejecuta dos jobs idempotentes por tick:
1. `notificaciones.scheduler` — si el lock del intervalo se obtiene, evalúa las
   dos ventanas de todos los tenants con `NOTIFICACIONES_ENABLED=true`.
2. `notificaciones.sender` — reclama hasta `N` envíos vencidos y los procesa.
"""
from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Any

import sqlalchemy
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import ConfigError, get_settings
from app.core.logging import configure_logging, log_event
from app.modules.notificaciones.lock import TickLock, redis_key
from app.modules.notificaciones.scheduler import SchedulerService
from app.modules.notificaciones.sender import SenderService
from app.modules.notificaciones.whatsapp import CloudApiClient
from app.modules.notificaciones.email import SmtpEmailClient

#: Segundos entre ticks del scheduler.
TICK_SECONDS = 15

#: Jobs registrados (C-09).
JOBS: tuple[str, ...] = ("notificaciones.scheduler", "notificaciones.sender")

logger = logging.getLogger("odontologia.worker")


def _conectar_redis(redis_url: str) -> object | None:
    """Conecta a Redis. Devuelve None si no está disponible (no bloquea el arranque)."""
    try:
        import redis

        cliente = redis.Redis.from_url(redis_url, socket_connect_timeout=5)
        cliente.ping()
        return cliente
    except Exception as exc:  # noqa: BLE001 - el arranque no debe depender de Redis
        log_event(logger, logging.WARNING, "redis no disponible", detalle=str(exc))
        return None


def _session_factory_from_settings() -> sessionmaker:
    from app import deps

    return sessionmaker(bind=deps.get_engine())


def ejecutar_tick(
    *,
    session: Session,
    redis_client: object | None,
    now: datetime | None = None,
    whatsapp_client: Any = None,
    email_client: Any = None,
    enabled: bool | None = None,
) -> dict[str, int]:
    """Ejecuta un tick determinístico. Usado por el loop y por la evidencia del MCP."""
    settings = get_settings()
    now = now or datetime.now(timezone.utc)
    if enabled is None:
        enabled = bool(settings.notificaciones_enabled)
    if whatsapp_client is None:
        whatsapp_client = CloudApiClient(
            api_token=settings.whatsapp_api_token.get_secret_value() if settings.whatsapp_api_token else None,
            phone_id=settings.whatsapp_phone_id,
        )
    if email_client is None:
        email_client = SmtpEmailClient()

    # Scheduler: por tenant, con lock.
    from app.modules.agenda.models import TenantModel
    from app.modules.agenda.repository import ConfigRepository

    tenants = list(session.execute(sqlalchemy.select(TenantModel)).scalars().all())
    encolados = 0
    for tenant in tenants:
        lock = TickLock(redis_client, session)
        if not lock.acquire(tenant.id):
            continue
        try:
            cfg = ConfigRepository(session).get(tenant.id)
            svc = SchedulerService(
                session,
                enabled=enabled,
                now=now,
                redis_client=redis_client,
            )
            # procesar solo este tenant
            nuevos = svc.procesar_tenant(tenant.id, cfg, now)
            encolados += len(nuevos)
        except Exception:
            lock.release(tenant.id)
            raise

    # Sender
    sender = SenderService(
        session,
        whatsapp=whatsapp_client,
        email=email_client,
        now=now,
        public_base_url=settings.public_base_url,
    )
    procesados = sender.ejecutar()
    session.commit()
    return {"encolados": encolados, "procesados": len(procesados)}


def main() -> int:
    try:
        settings = get_settings()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    configure_logging(settings.log_level, secrets=settings.sensitive_values())
    log_event(
        logger,
        logging.INFO,
        "worker arrancado",
        env=settings.app_env,
        jobs=len(JOBS),
        tick_seconds=TICK_SECONDS,
    )

    cliente = _conectar_redis(settings.redis_url)
    if cliente is not None:
        log_event(logger, logging.INFO, "redis conectado")

    session_factory = _session_factory_from_settings()

    detener = False

    def _parar(_signum: int, _frame: object) -> None:
        nonlocal detener
        detener = True

    signal.signal(signal.SIGINT, _parar)
    signal.signal(signal.SIGTERM, _parar)

    try:
        while not detener:
            try:
                with session_factory() as session:
                    resultado = ejecutar_tick(
                        session=session,
                        redis_client=cliente,
                        enabled=settings.notificaciones_enabled,
                    )
                    log_event(logger, logging.INFO, "tick", jobs=len(JOBS), **resultado)
            except Exception as exc:  # noqa: BLE001
                log_event(logger, logging.ERROR, "tick fallido", detalle=str(exc))
            time.sleep(TICK_SECONDS)
    finally:
        if cliente is not None:
            try:
                cliente.close()
            except Exception:  # noqa: BLE001
                pass
        log_event(logger, logging.INFO, "worker detenido")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

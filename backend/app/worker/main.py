"""Worker del backend (C-01).

Esqueleto sin jobs: el motor de notificaciones y el scheduler de recordatorios
son de C-09 (governance ALTO). Este módulo existe para que el compose del
proyecto tenga su servicio `worker` y para que C-09 tenga dónde aterrizar.
"""
from __future__ import annotations

import logging
import signal
import sys
import time

from app.core.config import ConfigError, get_settings
from app.core.logging import configure_logging, log_event

#: Segundos entre ticks del scheduler (C-09 usa 15 min; el esqueleto es más rápido).
TICK_SECONDS = 15

logger = logging.getLogger("odontologia.worker")

#: Jobs registrados. C-01 no registra ninguno.
JOBS: tuple[str, ...] = ()


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

    detener = False

    def _parar(_signum: int, _frame: object) -> None:
        nonlocal detener
        detener = True

    signal.signal(signal.SIGINT, _parar)
    signal.signal(signal.SIGTERM, _parar)

    try:
        while not detener:
            if JOBS:
                log_event(logger, logging.INFO, "tick", jobs=len(JOBS))
            else:
                log_event(logger, logging.INFO, "tick sin jobs registrados (C-09 los agrega)")
            time.sleep(TICK_SECONDS)
    finally:
        if cliente is not None:
            try:
                cliente.close()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 - cierre best-effort
                pass
        log_event(logger, logging.INFO, "worker detenido")
    return 0


if __name__ == "__main__":  # pragma: no cover - entrypoint
    raise SystemExit(main())

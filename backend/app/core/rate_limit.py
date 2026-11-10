"""Rate limiter con interfaz swapable (design decisión 6).

Implementación in-memory para v1; interfaz permite swap a Redis en C-13.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol


@dataclass
class RateLimitResult:
    """Resultado de verificación de rate limit."""
    allowed: bool
    retry_after: int | None = None  # segundos restantes si no permitido


class RateLimiter(Protocol):
    """Interfaz de rate limiter para permitir implementaciones swapables."""

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        """Verifica si la key excede el límite en la ventana."""
        ...


class InMemoryRateLimiter:
    """Rate limiter in-memory con ventana deslizante (design decisión 6).

    Almacena timestamps por key; purga timestamps viejos en cada check.
    V1 corre en una instancia, así que esta implementación es suficiente.
    C-13 puede swap a Redis usando la misma interfaz.
    """

    def __init__(self) -> None:
        self._timestamps: defaultdict[str, list[float]] = defaultdict(list)

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        """Verifica si la key excede el límite en la ventana."""
        now = time.time()
        timestamps = self._timestamps[key]

        # Purgar timestamps viejos fuera de la ventana
        timestamps[:] = [ts for ts in timestamps if now - ts < window_seconds]

        if len(timestamps) >= limit:
            # Calcular cuánto falta para que el timestamp más viejo expire
            oldest = timestamps[0]
            retry_after = int(oldest + window_seconds - now) + 1
            return RateLimitResult(allowed=False, retry_after=retry_after)

        # Agregar timestamp actual
        timestamps.append(now)
        return RateLimitResult(allowed=True)


import logging

logger = logging.getLogger("odontologia.rate_limit")


class RedisRateLimiter:
    """Rate limiter distribuido basado en Redis (C-13).

    Usa INCR + EXPIRE atómicos. Si Redis no está disponible, cae a
    InMemoryRateLimiter con un warning (no bloquea el arranque).
    """

    def __init__(self, redis_url: str, fallback: "InMemoryRateLimiter | None" = None) -> None:
        self._redis_url = redis_url
        self._fallback = fallback or InMemoryRateLimiter()
        self._client = None
        try:
            import redis

            self._client = redis.Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
            self._client.ping()
        except Exception as exc:  # noqa: BLE001
            logger.warning("redis no disponible para rate limit, usando in-memory: %s", exc)
            self._client = None

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        if self._client is None:
            return self._fallback.check(key, limit, window_seconds)
        try:
            redis_key = f"rl:{key}"
            pipe = self._client.pipeline()
            pipe.incr(redis_key)
            pipe.ttl(redis_key)
            count, ttl = pipe.execute()
            if ttl is None or ttl < 0:
                self._client.expire(redis_key, window_seconds)
                ttl = window_seconds
            if count > limit:
                retry_after = int(ttl) if ttl and ttl > 0 else window_seconds
                return RateLimitResult(allowed=False, retry_after=retry_after)
            return RateLimitResult(allowed=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("error en rate limit redis, usando fallback: %s", exc)
            return self._fallback.check(key, limit, window_seconds)


def get_rate_limiter() -> "RateLimiter":
    """Factory: InMemory en test, Redis en dev/prod (con fallback)."""
    try:
        from app.core.config import get_settings

        settings = get_settings()
        if getattr(settings, "app_env", "dev") == "test":
            return InMemoryRateLimiter()
        return RedisRateLimiter(settings.redis_url)
    except Exception:  # noqa: BLE001
        return InMemoryRateLimiter()


__all__ = ["RateLimiter", "RateLimitResult", "InMemoryRateLimiter", "RedisRateLimiter", "get_rate_limiter"]

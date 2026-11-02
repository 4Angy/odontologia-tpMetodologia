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


__all__ = ["RateLimiter", "RateLimitResult", "InMemoryRateLimiter"]

"""Tests de rate limit de login (Task 3.3): 5/60s por IP+email.

Valida:
- 6to intento → 429 antes de evaluar credenciales (aunque password correcta)
- ventana cumplida → login normal
"""
from __future__ import annotations

import time

import pytest

from app.core.rate_limit import InMemoryRateLimiter, RateLimitResult


def test_rate_limit_seis_intentos_rechazado() -> None:
    """El sexto intento dentro de la ventana devuelve 429."""
    limiter = InMemoryRateLimiter()
    key = "192.168.1.1:test@example.com"

    # Primeros 5 intentos deben ser permitidos
    for i in range(5):
        resultado = limiter.check(key, limit=5, window_seconds=60)
        assert resultado.allowed is True, f"Intento {i+1} debe ser permitido"
        assert resultado.retry_after is None

    # Sexto intento debe ser rechazado
    resultado = limiter.check(key, limit=5, window_seconds=60)
    assert resultado.allowed is False
    assert resultado.retry_after is not None
    assert resultado.retry_after > 0


def test_rate_limit_ventana_cumplida_login_normal() -> None:
    """Después de que la ventana expira, el login se evalúa normalmente."""
    limiter = InMemoryRateLimiter()
    key = "192.168.1.1:test@example.com"

    # Consumir el límite
    for _ in range(5):
        limiter.check(key, limit=5, window_seconds=60)

    # Sexto intento rechazado
    resultado = limiter.check(key, limit=5, window_seconds=60)
    assert resultado.allowed is False

    # Esperar a que expire el primer timestamp (ventana corta para test)
    time.sleep(1)
    resultado = limiter.check(key, limit=5, window_seconds=1)
    assert resultado.allowed is True


def test_rate_limit_claves_distintas_no_interfieren() -> None:
    """Rate limit por clave: IP+email distintos no interfieren."""
    limiter = InMemoryRateLimiter()
    key1 = "192.168.1.1:user1@example.com"
    key2 = "192.168.1.1:user2@example.com"

    # Consumir límite en key1
    for _ in range(5):
        limiter.check(key1, limit=5, window_seconds=60)

    # key1 debe estar bloqueada
    resultado1 = limiter.check(key1, limit=5, window_seconds=60)
    assert resultado1.allowed is False

    # key2 debe seguir permitida
    resultado2 = limiter.check(key2, limit=5, window_seconds=60)
    assert resultado2.allowed is True


def test_rate_limit_ventana_deslizante() -> None:
    """La ventana es deslizante: timestamps viejos se purgan."""
    limiter = InMemoryRateLimiter()
    key = "192.168.1.1:test@example.com"

    # Primer intento
    limiter.check(key, limit=5, window_seconds=2)
    time.sleep(1)

    # Intentos 2-5
    for _ in range(4):
        limiter.check(key, limit=5, window_seconds=2)

    # Intento 6 debe ser rechazado
    resultado = limiter.check(key, limit=5, window_seconds=2)
    assert resultado.allowed is False

    # Esperar a que expire el primer timestamp
    time.sleep(1.1)

    # Ahora debe permitirse nuevamente (ventana deslizante)
    resultado = limiter.check(key, limit=5, window_seconds=2)
    assert resultado.allowed is True

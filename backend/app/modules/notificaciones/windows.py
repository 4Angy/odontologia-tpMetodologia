"""Cálculo de ventanas de recordatorio (D10).

Todo en UTC. Los instantes se calculan sobre `turno.inicio` en UTC, y una ventana
se considera debida si su instante de envío cayó en el último intervalo del
scheduler (15 min), para no reenviar mensajes tardíos ni duplicar.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.modules.agenda.models import ConfigModel


TICK_INTERVAL = timedelta(minutes=15)
LOOKBACK = timedelta(hours=24)


@dataclass(frozen=True)
class Ventana:
    codigo: str
    horas: int
    enviar_at: datetime


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def ventanas_configuradas(config: Optional[ConfigModel]) -> list[tuple[str, int, bool]]:
    """Devuelve [(codigo, horas, habilitado)] según la config del tenant."""
    if config is None:
        return [("t-48h", 48, True), ("t-24h", 24, True)]
    return [
        ("t-48h", int(config.recordatorio_1_hs), bool(config.recordatorio_t_48h)),
        ("t-24h", int(config.recordatorio_2_hs), bool(config.recordatorio_t_24h)),
    ]


def calcular_ventanas(
    inicio_turno: datetime, config: Optional[ConfigModel]
) -> list[Ventana]:
    """Calcula las ventanas para un turno, deduplicando por horas."""
    resultado: list[Ventana] = []
    vistos: set[int] = set()
    for codigo, horas, habilitado in ventanas_configuradas(config):
        if not habilitado:
            continue
        if horas in vistos:
            continue
        vistos.add(horas)
        enviar_at = _utc(inicio_turno) - timedelta(hours=horas)
        resultado.append(Ventana(codigo=codigo, horas=horas, enviar_at=enviar_at))
    return resultado


def ventana_debida(ventana: Ventana, now: datetime, tick: timedelta = TICK_INTERVAL) -> bool:
    now_utc = _utc(now)
    enviar = _utc(ventana.enviar_at)
    return enviar <= now_utc < enviar + tick


__all__ = [
    "Ventana",
    "TICK_INTERVAL",
    "LOOKBACK",
    "ventanas_configuradas",
    "calcular_ventanas",
    "ventana_debida",
]

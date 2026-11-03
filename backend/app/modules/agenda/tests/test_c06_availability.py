from __future__ import annotations

from datetime import datetime, time, timezone

import pytest

from app.modules.agenda.availability import (
    HorarioSemanal,
    IntervaloTiempo,
    calcular_disponibilidad,
)


def test_disponibilidad_respeta_duracion_bloqueos_turnos_y_granularidad():
    horarios = [HorarioSemanal(dia_semana=0, inicio=time(9), fin=time(12))]
    bloqueo = IntervaloTiempo(
        inicio=datetime(2026, 11, 2, 10, 30, tzinfo=timezone.utc),
        fin=datetime(2026, 11, 2, 11, 0, tzinfo=timezone.utc),
    )
    turno_activo = IntervaloTiempo(
        inicio=datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc),
        fin=datetime(2026, 11, 2, 9, 30, tzinfo=timezone.utc),
    )

    candidatos = calcular_disponibilidad(
        horarios=horarios,
        bloqueos=[bloqueo],
        turnos_activos=[turno_activo],
        desde=datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc),
        hasta=datetime(2026, 11, 3, 0, 0, tzinfo=timezone.utc),
        duracion_min=60,
        antelacion_reserva_hs=2,
        ahora_utc=datetime(2026, 11, 2, 6, 0, tzinfo=timezone.utc),
        zona_horaria="UTC",
    )

    assert candidatos == [
        datetime(2026, 11, 2, 9, 30, tzinfo=timezone.utc),
        datetime(2026, 11, 2, 11, 0, tzinfo=timezone.utc),
    ]


def test_disponibilidad_interpreta_horario_en_zona_del_tenant_y_aplica_antelacion():
    candidatos = calcular_disponibilidad(
        horarios=[HorarioSemanal(dia_semana=0, inicio=time(8), fin=time(10))],
        bloqueos=[],
        turnos_activos=[],
        desde=datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc),
        hasta=datetime(2026, 11, 3, 0, 0, tzinfo=timezone.utc),
        duracion_min=30,
        antelacion_reserva_hs=2,
        ahora_utc=datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc),
        zona_horaria="America/Argentina/Buenos_Aires",
    )

    assert candidatos == [
        datetime(2026, 11, 2, 11, 0, tzinfo=timezone.utc),
        datetime(2026, 11, 2, 11, 30, tzinfo=timezone.utc),
        datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 11, 2, 12, 30, tzinfo=timezone.utc),
    ]


@pytest.mark.parametrize(
    ("desde", "hasta"),
    [
        (datetime(2026, 11, 2, 0, 0), datetime(2026, 11, 3, 0, 0, tzinfo=timezone.utc)),
        (
            datetime(2026, 11, 3, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc),
        ),
    ],
)
def test_disponibilidad_rechaza_ventana_naive_o_invertida(desde, hasta):
    with pytest.raises(ValueError):
        calcular_disponibilidad(
            horarios=[],
            bloqueos=[],
            turnos_activos=[],
            desde=desde,
            hasta=hasta,
            duracion_min=30,
            antelacion_reserva_hs=2,
            ahora_utc=datetime(2026, 11, 2, 6, 0, tzinfo=timezone.utc),
            zona_horaria="UTC",
        )

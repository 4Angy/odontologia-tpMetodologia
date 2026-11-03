from __future__ import annotations

from datetime import datetime, time, timezone

import pytest

from app.modules.agenda.availability import candidatos_disponibles
from app.modules.agenda.models import (
    BloqueoModel,
    ConfigModel,
    HorarioProfesionalModel,
    PrestacionModel,
    ProfesionalModel,
    TenantModel,
    TurnoModel,
)


def test_servicio_consulta_horarios_bloqueos_turnos_y_config_por_tenant(session):
    tenant = TenantModel(id="tenant-availability", slug="tenant-availability", tz="UTC")
    profesional = ProfesionalModel(
        id="prof-availability",
        tenant_id=tenant.id,
        nombre="Profesional sintético",
    )
    prestacion = PrestacionModel(
        id="prest-availability",
        tenant_id=tenant.id,
        nombre="Consulta sintética",
        duracion_min=30,
        precio_ref=None,
    )
    session.add_all([
        tenant,
        profesional,
        prestacion,
        ConfigModel(tenant_id=tenant.id, antelacion_reserva_hs=2),
        HorarioProfesionalModel(
            id="horario-availability",
            tenant_id=tenant.id,
            profesional_id=profesional.id,
            dia_semana=0,
            hora_inicio=time(9),
            hora_fin=time(15),
        ),
        BloqueoModel(
            id="bloqueo-availability",
            tenant_id=tenant.id,
            profesional_id=profesional.id,
            inicio=datetime(2026, 11, 2, 12, 30, tzinfo=timezone.utc),
            fin=datetime(2026, 11, 2, 13, 0, tzinfo=timezone.utc),
        ),
        TurnoModel(
            id="turno-activo-availability",
            tenant_id=tenant.id,
            paciente_id="paciente-sintetico",
            profesional_id=profesional.id,
            inicio=datetime(2026, 11, 2, 13, 30, tzinfo=timezone.utc),
            fin=datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc),
            estado="confirmado",
        ),
        TurnoModel(
            id="turno-cancelado-availability",
            tenant_id=tenant.id,
            paciente_id="paciente-sintetico",
            profesional_id=profesional.id,
            inicio=datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc),
            fin=datetime(2026, 11, 2, 14, 30, tzinfo=timezone.utc),
            estado="cancelado",
        ),
    ])
    session.commit()

    candidatos = candidatos_disponibles(
        session,
        tenant_id=tenant.id,
        profesional_id=profesional.id,
        prestacion_id=prestacion.id,
        desde=datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc),
        hasta=datetime(2026, 11, 3, 0, 0, tzinfo=timezone.utc),
        ahora_utc=datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc),
    )

    assert candidatos == [
        datetime(2026, 11, 2, 11, 0, tzinfo=timezone.utc),
        datetime(2026, 11, 2, 11, 30, tzinfo=timezone.utc),
        datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 11, 2, 13, 0, tzinfo=timezone.utc),
        datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc),
        datetime(2026, 11, 2, 14, 30, tzinfo=timezone.utc),
    ]


def test_servicio_no_resuelve_profesional_de_otro_tenant(session):
    owner = TenantModel(id="tenant-availability-owner", slug="availability-owner")
    foreign = TenantModel(id="tenant-availability-foreign", slug="availability-foreign")
    foreign_professional = ProfesionalModel(
        id="prof-availability-foreign",
        tenant_id=foreign.id,
        nombre="Profesional ajeno",
    )
    prestacion = PrestacionModel(
        id="prest-availability-owner",
        tenant_id=owner.id,
        nombre="Consulta sintética",
        duracion_min=30,
        precio_ref=None,
    )
    session.add_all([owner, foreign, foreign_professional, prestacion])
    session.commit()

    with pytest.raises(LookupError):
        candidatos_disponibles(
            session,
            tenant_id=owner.id,
            profesional_id=foreign_professional.id,
            prestacion_id=prestacion.id,
            desde=datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc),
            hasta=datetime(2026, 11, 3, 0, 0, tzinfo=timezone.utc),
            ahora_utc=datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc),
        )

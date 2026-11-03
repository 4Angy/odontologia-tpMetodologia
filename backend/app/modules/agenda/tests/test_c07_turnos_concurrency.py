from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from types import SimpleNamespace

import pytest

from app.modules.agenda.models import (
    PrestacionModel,
    ProfesionalModel,
    TenantModel,
)
from app.modules.agenda.repository import PrestacionRepository, TurnoRepository
from app.modules.agenda.service import User
from app.modules.agenda.turnos_service import ColisionTurnoError, TurnosService
from app.modules.pacientes.models import PacienteModel
from app.modules.pacientes.repository import PacienteRepository


def test_dos_reservas_concurrentes_del_mismo_profesional_no_se_solapan(
    db_engine, session_factory
):
    if db_engine.dialect.name != "postgresql":
        pytest.skip("SELECT FOR UPDATE requiere PostgreSQL para probar concurrencia real.")

    tenant_id = "tenant-c07-concurrencia"
    profesional_id = "prof-c07-concurrencia"
    paciente_id = "pac-c07-concurrencia"
    prestacion_id = "prest-c07-concurrencia"
    inicio = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
    ahora = inicio - timedelta(days=1)
    setup = session_factory()
    setup.add(TenantModel(id=tenant_id, nombre="Demo concurrencia"))
    setup.flush()
    setup.add_all(
        [
            ProfesionalModel(
                id=profesional_id,
                tenant_id=tenant_id,
                nombre="Profesional concurrencia",
                usuario_id="odontologo-c07-concurrencia",
            ),
            PrestacionModel(
                id=prestacion_id,
                tenant_id=tenant_id,
                nombre="Consulta concurrencia",
                duracion_min=30,
            ),
            PacienteModel(
                id=paciente_id,
                tenant_id=tenant_id,
                nombre="Paciente",
                apellido="Sintético",
            ),
        ]
    )
    setup.commit()
    setup.close()

    barrera = Barrier(2)

    def reservar(clave: str) -> str:
        session = session_factory()
        try:
            service = TurnosService(
                repo=TurnoRepository(session),
                pacientes=PacienteRepository(session),
                prestaciones=PrestacionRepository(session),
                disponibilidad=lambda **_kwargs: [],
            )
            request = SimpleNamespace(
                paciente_id=paciente_id,
                profesional_id=profesional_id,
                prestacion_id=prestacion_id,
                inicio=inicio,
                fin=inicio + timedelta(minutes=30),
                sobreturno=False,
                sobreturno_motivo=None,
            )
            barrera.wait(timeout=5)
            service.crear_turno(
                user=User(
                    id="recepcion-c07-concurrencia",
                    tenant_id=tenant_id,
                    roles=("recepcion",),
                ),
                request=request,
                idempotency_key=clave,
                ahora_utc=ahora,
            )
            session.commit()
            return "creado"
        except ColisionTurnoError:
            session.rollback()
            return "conflicto"
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(executor.map(reservar, ("concurrente-a", "concurrente-b")))

    assert sorted(resultados) == ["conflicto", "creado"]

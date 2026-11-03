from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.modules.agenda.models import (
    ProfesionalModel,
    TenantModel,
    TurnoModel,
)
from app.modules.agenda.repository import TurnoRepository

TENANT_A = "tenant-c07-a"
TENANT_B = "tenant-c07-b"
DESDE = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


def _crear_tenants(session) -> None:
    session.add_all(
        [
            TenantModel(id=TENANT_A, nombre="Demo A"),
            TenantModel(id=TENANT_B, nombre="Demo B"),
        ]
    )
    session.flush()
    session.add_all(
        [
            ProfesionalModel(id="prof-a", tenant_id=TENANT_A, nombre="Profesional A"),
            ProfesionalModel(id="prof-b", tenant_id=TENANT_B, nombre="Profesional B"),
        ]
    )
    session.flush()


def _turno(
    *,
    turno_id: str,
    tenant_id: str,
    profesional_id: str,
    inicio: datetime,
    fin: datetime,
    usuario_id: str | None = None,
    idempotency_key: str | None = None,
) -> TurnoModel:
    return TurnoModel(
        id=turno_id,
        tenant_id=tenant_id,
        paciente_id=f"pac-{turno_id}",
        profesional_id=profesional_id,
        profesional_usuario_id=usuario_id,
        inicio=inicio,
        fin=fin,
        estado="confirmado",
        idempotency_key=idempotency_key,
    )


def test_repo_bloquea_profesional_solo_dentro_del_tenant(session):
    _crear_tenants(session)
    session.commit()

    repo = TurnoRepository(session)
    assert repo.lock_profesional(TENANT_A, "prof-a") is not None
    assert repo.lock_profesional(TENANT_A, "prof-b") is None


def test_repo_lista_agenda_por_interseccion_tenant_y_usuario(session):
    _crear_tenants(session)
    session.add_all(
        [
            _turno(
                turno_id="a-overlap",
                tenant_id=TENANT_A,
                profesional_id="prof-a",
                inicio=DESDE - timedelta(minutes=15),
                fin=DESDE + timedelta(minutes=15),
                usuario_id="odontologo-a",
            ),
            _turno(
                turno_id="a-fuera",
                tenant_id=TENANT_A,
                profesional_id="prof-a",
                inicio=DESDE + timedelta(days=2),
                fin=DESDE + timedelta(days=2, minutes=30),
                usuario_id="odontologo-a",
            ),
            _turno(
                turno_id="b-overlap",
                tenant_id=TENANT_B,
                profesional_id="prof-b",
                inicio=DESDE - timedelta(minutes=10),
                fin=DESDE + timedelta(minutes=20),
                usuario_id="odontologo-b",
            ),
        ]
    )
    session.commit()

    resultados = TurnoRepository(session).list_for_agenda(
        tenant_id=TENANT_A,
        desde=DESDE,
        hasta=DESDE + timedelta(hours=1),
        profesional_usuario_id="odontologo-a",
    )
    assert [turno.id for turno in resultados] == ["a-overlap"]


def test_repo_busca_idempotencia_tenant_scoped(session):
    _crear_tenants(session)
    session.add_all(
        [
            _turno(
                turno_id="a-idempotente",
                tenant_id=TENANT_A,
                profesional_id="prof-a",
                inicio=DESDE,
                fin=DESDE + timedelta(minutes=30),
                idempotency_key="key-1",
            ),
            _turno(
                turno_id="b-idempotente",
                tenant_id=TENANT_B,
                profesional_id="prof-b",
                inicio=DESDE,
                fin=DESDE + timedelta(minutes=30),
                idempotency_key="key-1",
            ),
        ]
    )
    session.commit()

    repo = TurnoRepository(session)
    assert repo.get_by_idempotency_key(TENANT_A, "key-1").id == "a-idempotente"
    assert repo.get_by_idempotency_key(TENANT_B, "key-1").id == "b-idempotente"
    assert repo.get_by_idempotency_key(TENANT_A, "missing") is None

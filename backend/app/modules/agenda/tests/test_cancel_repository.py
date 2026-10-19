"""Tests de repositorio (Task 2.1, RED primero).

TDD estricto, datos sintéticos (R14). Corre contra Postgres 16 real: la
sesión la provee la fixture compartida de `backend/conftest.py` (un esquema
por test).
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.modules.agenda.models import ConfigModel, TenantModel, TurnoModel
from app.modules.agenda.repository import ConfigRepository, TurnoRepository

TENANT_A = "tenant-demo-a"
TENANT_B = "tenant-demo-b"


def _crear_tenants(session, *tenant_ids):
    """Crea los tenants. Necesario porque Postgres SÍ valida las FK
    (`config.tenant_id` -> `tenant.id`), cosa que SQLite no hacía."""
    for tenant_id in tenant_ids:
        session.add(TenantModel(id=tenant_id, nombre=tenant_id))
    session.commit()


def _turno(**kw):
    ahora = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
    base = dict(
        id="turno-1",
        tenant_id=TENANT_A,
        paciente_id="pac-1",
        profesional_id="prof-1",
        prestacion_id=None,
        inicio=ahora + timedelta(hours=48),
        fin=ahora + timedelta(hours=48, minutes=30),
        estado="confirmado",
    )
    base.update(kw)
    return TurnoModel(**base)


def test_repo_query_filtra_por_tenant_id_R1(session):
    """R1: un tenant no ve ni cancela turnos de otro tenant."""
    _crear_tenants(session, TENANT_A, TENANT_B)
    session.add(_turno(id="t-a", tenant_id=TENANT_A))
    session.add(_turno(id="t-b", tenant_id=TENANT_B))
    session.add(ConfigModel(tenant_id=TENANT_A, antelacion_cancel_hs=24))
    session.add(ConfigModel(tenant_id=TENANT_B, antelacion_cancel_hs=24))
    session.commit()

    repo = TurnoRepository(session)
    assert repo.get_by_id(TENANT_A, "t-a") is not None
    assert repo.get_by_id(TENANT_A, "t-b") is None  # cross-tenant invisible
    assert repo.get_by_id(TENANT_B, "t-a") is None

    activos_a = repo.list_activos(TENANT_A, "prof-1",
                                 datetime(2026, 10, 1, tzinfo=timezone.utc),
                                 datetime(2026, 11, 1, tzinfo=timezone.utc))
    assert [t.id for t in activos_a] == ["t-a"]


def test_repo_cancelled_at_se_persiste_utc_aware_R7(session):
    """R7: cancelled_at se persiste y vuelve con timezone (UTC)."""
    _crear_tenants(session, TENANT_A)
    t = _turno()
    t.estado = "cancelado"
    t.cancelled_by = "user-1"
    t.cancelled_at = datetime(2026, 10, 7, 13, 0, tzinfo=timezone.utc)
    t.motivo = "x"
    session.add(t)
    session.commit()
    session.expire_all()

    repo = TurnoRepository(session)
    leido = repo.get_by_id(TENANT_A, "turno-1")
    assert leido.cancelled_at is not None
    assert leido.cancelled_at.tzinfo is not None, "cancelled_at debe volver aware (R7)"
    assert leido.inicio.tzinfo is not None


def test_repo_config_columna_precisa_y_check_no_negativo(session):
    """Columna precisa `antelacion_cancel_hs` (no `antelacion_hs`), default 24, CHECK >= 0."""
    from sqlalchemy import inspect as sa_inspect
    cols = {c["name"] for c in sa_inspect(session.bind).get_columns("config")}
    assert "antelacion_cancel_hs" in cols
    assert "antelacion_hs" not in cols

    _crear_tenants(session, TENANT_A)
    repo = ConfigRepository(session)
    assert repo.get_hs(TENANT_A) is None  # ausente → servicio usa fallback
    repo.upsert(TENANT_A, 12)
    assert repo.get_hs(TENANT_A) == 12
    with pytest.raises(Exception):  # noqa: PT011 - CHECK >= 0 a nivel DB
        repo.upsert(TENANT_A, -1)
        session.flush()


def test_repo_senia_flag_default_false(session):
    """`senia_pendiente_definicion` DEFAULT FALSE a nivel de columna."""
    _crear_tenants(session, TENANT_A)
    session.add(_turno())
    session.commit()
    session.expire_all()
    leido = TurnoRepository(session).get_by_id(TENANT_A, "turno-1")
    assert leido.senia_pendiente_definicion is False

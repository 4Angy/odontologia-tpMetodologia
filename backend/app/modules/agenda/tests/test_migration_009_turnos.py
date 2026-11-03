from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects import sqlite

from app.modules.agenda.models import TurnoModel

def _migration():
    migration_path = (
        Path(__file__).resolve().parents[4]
        / "alembic"
        / "versions"
        / "009_turnos_agenda_interna.py"
    )
    spec = importlib.util.spec_from_file_location("migration_009_turnos", migration_path)
    assert spec is not None
    assert spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _crear_esquema_previo(connection) -> None:
    connection.execute(text("CREATE TABLE tenant (id VARCHAR(64) PRIMARY KEY)"))
    connection.execute(text("INSERT INTO tenant (id) VALUES ('tenant-sintetico')"))
    connection.execute(text("""
        CREATE TABLE turno (
            id VARCHAR(64) PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            paciente_id VARCHAR(64) NOT NULL,
            profesional_id VARCHAR(64) NOT NULL,
            profesional_usuario_id VARCHAR(64),
            prestacion_id VARCHAR(64),
            inicio TIMESTAMP NOT NULL,
            fin TIMESTAMP NOT NULL,
            estado VARCHAR(32) NOT NULL,
            cancelled_by VARCHAR(64),
            cancelled_at TIMESTAMP,
            motivo TEXT,
            senia_pendiente_definicion BOOLEAN NOT NULL DEFAULT 0
        )
    """))
    connection.execute(text("""
        INSERT INTO turno (
            id, tenant_id, paciente_id, profesional_id, inicio, fin, estado
        ) VALUES (
            'turno-existente', 'tenant-sintetico', 'paciente-sintetico',
            'profesional-sintetico', '2026-10-07 12:00:00',
            '2026-10-07 12:30:00', 'confirmado'
        )
    """))


def test_migracion_009_extiende_turno_y_preserva_datos_en_upgrade_downgrade():
    migration = _migration()
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        _crear_esquema_previo(connection)

        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        schema = inspect(connection)
        columnas = {columna["name"] for columna in schema.get_columns("turno")}
        assert {
            "token_publico",
            "origen",
            "senia_id",
            "idempotency_key",
            "sobreturno",
            "sobreturno_motivo",
            "sobreturno_autorizado_por",
        } <= columnas
        existente = connection.execute(
            text("SELECT tenant_id, paciente_id, estado, origen FROM turno WHERE id = 'turno-existente'")
        ).one()
        assert tuple(existente) == (
            "tenant-sintetico",
            "paciente-sintetico",
            "confirmado",
            "mostrador",
        )

        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()

        columnas_despues = {columna["name"] for columna in inspect(connection).get_columns("turno")}
        assert "idempotency_key" not in columnas_despues
        assert "token_publico" not in columnas_despues
        assert connection.execute(
            text("SELECT id FROM turno WHERE id = 'turno-existente'")
        ).scalar_one() == "turno-existente"
        assert connection.execute(
            text("SELECT id FROM tenant WHERE id = 'tenant-sintetico'")
        ).scalar_one() == "tenant-sintetico"
    engine.dispose()


def test_migracion_009_crea_indices_esperados_para_turnos():
    migration = _migration()
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        _crear_esquema_previo(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        indices = {indice["name"]: indice for indice in inspect(connection).get_indexes("turno")}
        assert indices["ix_turno_tenant_profesional_inicio"]["column_names"] == [
            "tenant_id",
            "profesional_id",
            "inicio",
        ]
        assert indices["ux_turno_token_publico"]["unique"] == 1
        assert indices["ux_turno_tenant_idempotency_key"]["unique"] == 1
    engine.dispose()


def test_modelo_turno_declara_campos_tenant_claves_y_datetimes_aware():
    columnas = TurnoModel.__table__.columns
    assert {
        "token_publico",
        "origen",
        "senia_id",
        "idempotency_key",
        "sobreturno",
        "sobreturno_motivo",
        "sobreturno_autorizado_por",
    } <= set(columnas.keys())
    assert columnas["idempotency_key"].nullable is True
    assert columnas["token_publico"].nullable is True
    assert columnas["inicio"].type.impl.timezone is True

    indices = {indice.name: indice for indice in TurnoModel.__table__.indexes}
    assert indices["ux_turno_tenant_idempotency_key"].unique is True
    assert indices["ux_turno_token_publico"].unique is True

    with pytest.raises(ValueError, match="datetime naive"):
        columnas["inicio"].type.process_bind_param(
            datetime(2026, 10, 7, 12, 0), sqlite.dialect()
        )

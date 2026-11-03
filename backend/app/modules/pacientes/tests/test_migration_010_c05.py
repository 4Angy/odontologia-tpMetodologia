from __future__ import annotations

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


_MIGRATION_FILE = (
    Path(__file__).parents[4]
    / "alembic"
    / "versions"
    / "010_c05_contrato_clinico.py"
)
_SPEC = importlib.util.spec_from_file_location("migration_010_c05", _MIGRATION_FILE)
assert _SPEC is not None and _SPEC.loader is not None
_MIGRATION = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MIGRATION)


def _legacy_schema(connection) -> None:
    connection.exec_driver_sql("CREATE TABLE tenant (id VARCHAR(64) PRIMARY KEY)")
    connection.exec_driver_sql(
        "CREATE TABLE paciente (id VARCHAR(64) PRIMARY KEY, tenant_id VARCHAR(64))"
    )
    connection.exec_driver_sql("CREATE TABLE usuario (id VARCHAR(64) PRIMARY KEY)")
    connection.exec_driver_sql(
        "CREATE TABLE profesional (id VARCHAR(64) PRIMARY KEY, tenant_id VARCHAR(64), usuario_id VARCHAR(64))"
    )
    connection.exec_driver_sql(
        "CREATE TABLE evolucion ("
        "id VARCHAR(64) PRIMARY KEY, tenant_id VARCHAR(64), paciente_id VARCHAR(64), "
        "odontologo_id VARCHAR(64), motivo VARCHAR(200) NOT NULL, detalle TEXT NOT NULL, "
        "firma_simple BOOLEAN NOT NULL, firma_timestamp TIMESTAMP, created_at TIMESTAMP NOT NULL, "
        "updated_at TIMESTAMP NOT NULL, deleted_at TIMESTAMP)"
    )
    connection.exec_driver_sql(
        "CREATE TABLE adjunto ("
        "id VARCHAR(64) PRIMARY KEY, tenant_id VARCHAR(64), paciente_id VARCHAR(64), "
        "nombre VARCHAR(200) NOT NULL, tipo VARCHAR(100) NOT NULL, tamano_bytes INTEGER NOT NULL, "
        "url VARCHAR(500), created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL, "
        "deleted_at TIMESTAMP)"
    )
    connection.exec_driver_sql(
        "CREATE TABLE presupuesto ("
        "id VARCHAR(64) PRIMARY KEY, tenant_id VARCHAR(64), paciente_id VARCHAR(64), "
        "total_cents INTEGER NOT NULL, estado VARCHAR(32) NOT NULL, notas TEXT, "
        "created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL, deleted_at TIMESTAMP)"
    )


def test_migration_010_preserves_legacy_data_and_is_reversible():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        _legacy_schema(connection)
        for statement in (
            "INSERT INTO tenant(id) VALUES ('tenant-sintetico')",
            "INSERT INTO usuario(id) VALUES ('usuario-sintetico')",
            "INSERT INTO paciente(id, tenant_id) VALUES ('paciente-sintetico', 'tenant-sintetico')",
            "INSERT INTO profesional(id, tenant_id, usuario_id) "
            "VALUES ('profesional-sintetico', 'tenant-sintetico', 'usuario-sintetico')",
            "INSERT INTO evolucion(id, tenant_id, paciente_id, odontologo_id, motivo, detalle, "
            "firma_simple, firma_timestamp, created_at, updated_at) VALUES "
            "('evo-sintetica', 'tenant-sintetico', 'paciente-sintetico', 'usuario-sintetico', "
            "'Motivo sintético', 'Detalle sintético', 1, '2026-11-03 12:00:00', "
            "'2026-11-03 11:00:00', '2026-11-03 11:00:00')",
            "INSERT INTO presupuesto(id, tenant_id, paciente_id, total_cents, estado, created_at, updated_at) "
            "VALUES ('presupuesto-sintetico', 'tenant-sintetico', 'paciente-sintetico', 2500, "
            "'activo', '2026-11-03 11:00:00', '2026-11-03 11:00:00')",
        ):
            connection.exec_driver_sql(statement)
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            _MIGRATION.upgrade()
            _MIGRATION.upgrade()

        columns = {column["name"] for column in inspect(connection).get_columns("evolucion")}
        assert {
            "profesional_id",
            "fecha",
            "pieza_fdi_slot",
            "pieza_fdi_numero",
            "odontograma_ref",
            "firmado_at",
        } <= columns
        evolucion = connection.execute(
            text(
                "SELECT profesional_id, fecha, motivo, detalle, firmado_at "
                "FROM evolucion WHERE id = 'evo-sintetica'"
            )
        ).one()
        assert evolucion.profesional_id == "profesional-sintetico"
        assert evolucion.fecha.startswith("2026-11-03 11:00:00")
        assert evolucion.motivo == "Motivo sintético"
        assert evolucion.detalle == "Detalle sintético"
        assert evolucion.firmado_at.startswith("2026-11-03 12:00:00")
        assert connection.execute(
            text("SELECT estado FROM presupuesto WHERE id = 'presupuesto-sintetico'")
        ).scalar_one() == "aceptado"
        assert "storage_key" in {
            column["name"] for column in inspect(connection).get_columns("adjunto")
        }

        with Operations.context(context):
            _MIGRATION.downgrade()
        legacy_evolucion = connection.execute(
            text(
                "SELECT odontologo_id, motivo, detalle, firma_timestamp "
                "FROM evolucion WHERE id = 'evo-sintetica'"
            )
        ).one()
        assert legacy_evolucion.odontologo_id == "usuario-sintetico"
        assert legacy_evolucion.motivo == "Motivo sintético"
        assert legacy_evolucion.detalle == "Detalle sintético"
        assert legacy_evolucion.firma_timestamp.startswith("2026-11-03 12:00:00")
        assert connection.execute(
            text("SELECT estado FROM presupuesto WHERE id = 'presupuesto-sintetico'")
        ).scalar_one() == "activo"
    engine.dispose()

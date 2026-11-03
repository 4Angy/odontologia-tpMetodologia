from __future__ import annotations

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_migracion_008_es_reversible_y_no_altera_tenant():
    migration_path = (
        Path(__file__).resolve().parents[4]
        / "alembic"
        / "versions"
        / "008_horarios_profesional.py"
    )
    spec = importlib.util.spec_from_file_location("migration_008_horarios", migration_path)
    assert spec is not None
    assert spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE tenant (id VARCHAR(64) PRIMARY KEY)"))
        connection.execute(text("INSERT INTO tenant (id) VALUES ('tenant-sintetico')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        schema = inspect(connection)
        assert schema.has_table("horario_profesional")
        assert "ux_horario_profesional_inicio" in {
            item["name"] for item in schema.get_unique_constraints("horario_profesional")
        }

        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert not inspect(connection).has_table("horario_profesional")
        assert connection.execute(text("SELECT id FROM tenant")).scalar_one() == "tenant-sintetico"

        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        assert inspect(connection).has_table("horario_profesional")
    engine.dispose()

"""Regresión del atajo SQLite (P2).

SQLite ignora las FK por defecto. Si el engine de test no activa
`PRAGMA foreign_keys=ON`, la suite local puede quedar verde mientras que en
Postgres (donde las FK son reales) falla. Este test protege ese contrato.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.agenda.models import UsuarioModel, UsuarioRoles

_ES_SQLITE = os.getenv("TEST_DATABASE_URL", "").startswith("sqlite://")

pytestmark = pytest.mark.skipif(
    not _ES_SQLITE,
    reason="solo aplica al atajo SQLite (TEST_DATABASE_URL=sqlite://)",
)


def test_engine_sqlite_de_test_enforce_foreign_keys(db_engine):
    with db_engine.connect() as conexion:
        assert conexion.execute(text("PRAGMA foreign_keys")).scalar() == 1

    with Session(db_engine) as session:
        session.add(
            UsuarioModel(
                id="u-sin-tenant",
                tenant_id="tenant-inexistente",
                email="sin-tenant@example.test",
                nombre="Usuario huérfano",
                roles=[UsuarioRoles.DUENO.value],
                activo=True,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()

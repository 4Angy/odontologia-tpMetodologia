"""Fixtures compartidas del backend (C-01).

La suite corre contra **Postgres 16 real** (decisión M1): cada test usa su
propio esquema, así que el aislamiento entre tests no depende del motor y las
diferencias de PostgreSQL (timestamptz, CHECK, tipos) se detectan en CI.

Atajo: si `TEST_DATABASE_URL` es una URL de SQLite, se usa SQLite en memoria.

Este conftest vive en la **raíz de `backend/`** a propósito: un conftest dentro
de `backend/tests/` no sería visible para `backend/app/modules/**/tests/`.
"""
from __future__ import annotations

import os
import uuid
from typing import Iterator

import pytest
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, import_models

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://odontologia:odontologia@localhost:55432/odontologia_test",
)

# Variables mínimas para que la app sea arrancable en tests sin `.env`.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "t" * 64)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("LOG_LEVEL", "WARNING")

_ES_SQLITE = TEST_DATABASE_URL.startswith("sqlite://")


@pytest.fixture()
def db_engine() -> Iterator[Engine]:
    """Engine de test: esquema aislado por test (Postgres) o SQLite en memoria."""
    import_models()

    if _ES_SQLITE:
        engine = create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        try:
            yield engine
        finally:
            engine.dispose()
        return

    esquema = f"test_{uuid.uuid4().hex[:12]}"
    engine = create_engine(TEST_DATABASE_URL)

    with engine.begin() as conexion:
        conexion.execute(text(f'CREATE SCHEMA "{esquema}"'))
        conexion.execute(text(f'SET search_path TO "{esquema}"'))

    @event.listens_for(engine, "checkout")
    def _search_path(dbapi_connection, connection_record, connection_proxy):  # noqa: ANN001, ARG001
        with dbapi_connection.cursor() as cursor:
            cursor.execute(f'SET search_path TO "{esquema}"')

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        with engine.begin() as conexion:
            conexion.execute(text(f'DROP SCHEMA IF EXISTS "{esquema}" CASCADE'))
        engine.dispose()


@pytest.fixture()
def session_factory(db_engine: Engine) -> sessionmaker:
    """`sessionmaker`_bound al engine de test."""
    return sessionmaker(bind=db_engine)


@pytest.fixture()
def session(session_factory: sessionmaker) -> Iterator[Session]:
    """Sesión de DB aislada por test."""
    s = session_factory()
    try:
        yield s
    finally:
        s.close()

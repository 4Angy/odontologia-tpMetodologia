"""Alembic env: metadata compartida de todos los módulos (C-01).

La URL sale de la configuración validada (`DATABASE_URL`); el compose y el CI
siempre la definen. `target_metadata` es la `Base` única del monolito modular
(`app.core.db`), con los modelos de todos los módulos importados.
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import ConfigError, get_settings  # noqa: E402
from app.core.db import Base, import_models  # noqa: E402

import_models()  # noqa: E402  - registra los modelos antes de leer la metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

DEFAULT_URL = "postgresql+psycopg://odontologia:odontologia@localhost:5432/odontologia"


def get_url() -> str:
    """URL de la base de datos para las migraciones."""
    try:
        return get_settings().database_url
    except ConfigError:
        return os.getenv("DATABASE_URL", DEFAULT_URL)


def run_migrations_offline() -> None:
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(get_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

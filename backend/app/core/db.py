"""Base SQLAlchemy compartida del monolito modular (C-01).

Todos los modelos de todos los módulos importan `Base` de acá, para que
Alembic y los tests tengan **una sola** metadata.
"""
from __future__ import annotations

import importlib
import pkgutil

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa común a todos los módulos."""


def import_models() -> None:
    """Importa los modelos de todos los módulos para registrarlos en `Base`.

    Se llama desde Alembic (`target_metadata`) y desde los fixtures de test.
    Los módulos sin `models.py` se ignoran.
    """
    import app.core.tenancy.models  # noqa: F401
    import app.modules as modules_package

    for info in pkgutil.iter_modules(modules_package.__path__):
        if not info.ispkg:
            continue
        try:
            importlib.import_module(f"app.modules.{info.name}.models")
        except ModuleNotFoundError:
            continue


__all__ = ["Base", "import_models"]

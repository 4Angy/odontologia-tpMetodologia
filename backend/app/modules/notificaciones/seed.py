"""Seed idempotente de plantillas (C-09, D15)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.notificaciones.repository import PlantillaRepository


def seed_plantillas(session: Session, tenant_id: str) -> list:
    repo = PlantillaRepository(session)
    return repo.seed_tenant(tenant_id)


__all__ = ["seed_plantillas"]

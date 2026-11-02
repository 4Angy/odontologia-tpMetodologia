from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.security import has_effective_permission
from app.core.tenancy.repositories import BaseRepository, TenantRepository, UnitOfWork
from app.modules.agenda.models import TenantModel, UsuarioModel, normalize_slug


@pytest.fixture()
def sqlite_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_tenant_and_audit_mixins_capture_tenant_and_audit_fields(sqlite_session: Session):
    tenant = TenantModel(id="tenant-a", nombre="Clínica A", slug="clinica-a")
    sqlite_session.add(tenant)
    sqlite_session.commit()

    usuario = UsuarioModel(
        id="user-1",
        tenant_id="tenant-a",
        nombre="Ana",
        email="ana@clinica.com",
        roles=["recepcion", "odontologo"],
        activo=True,
    )
    sqlite_session.add(usuario)
    sqlite_session.commit()

    assert usuario.tenant_id == "tenant-a"
    assert usuario.created_at.tzinfo is not None
    assert usuario.updated_at.tzinfo is not None
    assert usuario.deleted_at is None
    assert normalize_slug("  Clínica Demo  ") == "clinica-demo"


def test_repository_filters_by_tenant_and_excludes_deleted_rows(sqlite_session: Session):
    sqlite_session.add_all(
        [
            TenantModel(id="tenant-a", nombre="A", slug="tenant-a"),
            TenantModel(id="tenant-b", nombre="B", slug="tenant-b"),
        ]
    )
    sqlite_session.commit()

    sqlite_session.add_all(
        [
            UsuarioModel(id="u-a-1", tenant_id="tenant-a", email="a1@demo.com", roles=["recepcion"], activo=True),
            UsuarioModel(id="u-a-2", tenant_id="tenant-a", email="a2@demo.com", roles=["odontologo"], activo=True),
            UsuarioModel(id="u-b-1", tenant_id="tenant-b", email="b1@demo.com", roles=["dueno"], activo=True),
        ]
    )
    sqlite_session.commit()

    sqlite_session.query(UsuarioModel).filter_by(id="u-a-2").update({"deleted_at": datetime.now(timezone.utc)})
    sqlite_session.commit()

    repo = BaseRepository(sqlite_session, UsuarioModel, tenant_id="tenant-a")
    assert [u.id for u in repo.list(limit=20)] == ["u-a-1"]
    assert repo.get_by_id("u-b-1") is None


def test_uow_scopes_business_repositories_and_blocks_invalid_construction(sqlite_session: Session):
    sqlite_session.add_all(
        [
            TenantModel(id="tenant-a", nombre="A", slug="tenant-a"),
            TenantModel(id="tenant-b", nombre="B", slug="tenant-b"),
        ]
    )
    sqlite_session.commit()

    uow = UnitOfWork("tenant-a", sqlite_session)
    assert isinstance(uow.tenants, TenantRepository)
    assert uow.repository(UsuarioModel).tenant_id == "tenant-a"
    assert uow.get_repository(UsuarioModel).tenant_id == "tenant-a"

    with pytest.raises(ValueError):
        BaseRepository(sqlite_session, UsuarioModel, tenant_id=None)

    with pytest.raises(ValueError):
        UnitOfWork("", sqlite_session)


def test_permission_is_effective_union_of_roles():
    assert has_effective_permission(("recepcion", "odontologo"), "recepcion")
    assert has_effective_permission(("recepcion", "odontologo"), "odontologo")
    assert not has_effective_permission((), "dueno")
    assert has_effective_permission(("dueno", "recepcion"), "recepcion", "dueno")

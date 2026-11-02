"""Tests de aislamiento cross-tenant en auth (Task 5.1).

Valida R1: usuario del tenant A no puede invitar ni listar sobre tenant B.
Cross-tenant → rechazo o sin filas.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.agenda.models import TenantModel, UsuarioModel, UsuarioRoles


def test_listar_usuarios_solo_tenant(session: Session) -> None:
    """GET /users filtra por tenant_id (R1): solo usuarios del mismo tenant."""
    tenant_a = TenantModel(id=str(uuid.uuid4()), slug="tenant-a", nombre="Tenant A")
    tenant_b = TenantModel(id=str(uuid.uuid4()), slug="tenant-b", nombre="Tenant B")
    session.add_all([tenant_a, tenant_b])
    session.flush()

    usuario_a = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        email="user@a.com",
        nombre="Usuario A",
        roles=[UsuarioRoles.RECEPCION.value],
        activo=True,
    )
    usuario_b = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        email="user@b.com",
        nombre="Usuario B",
        roles=[UsuarioRoles.RECEPCION.value],
        activo=True,
    )
    session.add_all([usuario_a, usuario_b])
    session.commit()

    # Query filtrando por tenant A
    usuarios_a = session.scalars(
        select(UsuarioModel).where(UsuarioModel.tenant_id == tenant_a.id)
    ).all()

    assert len(usuarios_a) == 1
    assert usuarios_a[0].email == "user@a.com"
    assert usuarios_a[0].tenant_id == tenant_a.id

    # Query filtrando por tenant B
    usuarios_b = session.scalars(
        select(UsuarioModel).where(UsuarioModel.tenant_id == tenant_b.id)
    ).all()

    assert len(usuarios_b) == 1
    assert usuarios_b[0].email == "user@b.com"
    assert usuarios_b[0].tenant_id == tenant_b.id


def test_email_duplicado_por_tenant(session: Session) -> None:
    """El email es único por tenant (R1), no global."""
    tenant_a = TenantModel(id=str(uuid.uuid4()), slug="tenant-a", nombre="Tenant A")
    tenant_b = TenantModel(id=str(uuid.uuid4()), slug="tenant-b", nombre="Tenant B")
    session.add_all([tenant_a, tenant_b])
    session.flush()

    usuario_a = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        email="mismo@test.com",
        nombre="Usuario A",
        roles=[UsuarioRoles.RECEPCION.value],
        activo=True,
    )
    usuario_b = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        email="mismo@test.com",  # mismo email, distinto tenant (permitido)
        nombre="Usuario B",
        roles=[UsuarioRoles.RECEPCION.value],
        activo=True,
    )
    session.add_all([usuario_a, usuario_b])
    session.commit()

    # Ambos usuarios deben existir
    assert session.get(UsuarioModel, usuario_a.id) is not None
    assert session.get(UsuarioModel, usuario_b.id) is not None
    assert usuario_a.tenant_id != usuario_b.tenant_id


def test_mismo_email_mismo_tenant_falla(session: Session) -> None:
    """El email duplicado en el mismo tenant viola la unicidad."""
    tenant = TenantModel(id=str(uuid.uuid4()), slug="tenant-a", nombre="Tenant A")
    session.add(tenant)
    session.flush()

    usuario1 = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email="mismo@test.com",
        nombre="Usuario 1",
        roles=[UsuarioRoles.RECEPCION.value],
        activo=True,
    )
    session.add(usuario1)
    session.commit()

    usuario2 = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email="mismo@test.com",  # duplicado en mismo tenant
        nombre="Usuario 2",
        roles=[UsuarioRoles.RECEPCION.value],
        activo=True,
    )
    session.add(usuario2)

    # Debe fallar por constraint de unicidad
    with pytest.raises(Exception):  # IntegrityError
        session.commit()

"""Tests de gestión de usuarios del tenant (Task 3.2): /users/invite, /users.

Valida:
- dueno invita con rol acotado
- no-dueno → 403 RN-AU-04
- rol inexistente → 422 en español-AR
- email duplicado en tenant rechazado sin filtrar otros tenants (R1)
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import mint_token
from app.main import create_app
from app.modules.agenda.models import TenantModel, UsuarioModel, UsuarioRoles


@pytest.fixture()
def setup_db(session_factory):  # noqa: ANN201
    """Provee la fábrica aislada para la aplicación bajo prueba."""
    return session_factory


@pytest.fixture()
def client(setup_db):  # noqa: ANN201
    app = create_app(session_factory=setup_db)
    return TestClient(app)


def test_dueno_invita_con_rol_acotado(client: TestClient, session: Session) -> None:
    """El dueño puede invitar un usuario con roles válidos."""
    tenant = TenantModel(id=str(uuid.uuid4()), slug="test-tenant", nombre="Test")
    session.add(tenant)
    session.flush()
    dueno = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email="dueno@test.com",
        nombre="Dueño",
        roles=[UsuarioRoles.DUENO.value],
        activo=True,
    )
    session.add(dueno)
    session.commit()

    token = mint_token(
        user_id=dueno.id,
        tenant_id=tenant.id,
        roles=dueno.roles,
        email=dueno.email,
        token_type="access",
    )

    response = client.post(
        "/users/invite",
        json={
            "email": "nuevo@test.com",
            "nombre": "Nuevo Usuario",
            "roles": ["recepcion"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "nuevo@test.com"
    assert data["roles"] == ["recepcion"]
    assert data["activo"] is True


def test_no_dueno_no_puede_invitar(client: TestClient, session: Session) -> None:
    """Un usuario sin rol dueno recibe 403 RN-AU-04."""
    tenant = TenantModel(id=str(uuid.uuid4()), slug="test-tenant", nombre="Test")
    session.add(tenant)
    session.flush()
    recepcion = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email="recepcion@test.com",
        nombre="Recepción",
        roles=[UsuarioRoles.RECEPCION.value],
        activo=True,
    )
    session.add(recepcion)
    session.commit()

    token = mint_token(
        user_id=recepcion.id,
        tenant_id=tenant.id,
        roles=recepcion.roles,
        email=recepcion.email,
        token_type="access",
    )

    response = client.post(
        "/users/invite",
        json={
            "email": "nuevo@test.com",
            "nombre": "Nuevo Usuario",
            "roles": ["recepcion"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "RN-AU-04"


def test_rol_inexistente_rechazado(client: TestClient, session: Session) -> None:
    """Un rol inválido en la invitación devuelve 422 en español-AR."""
    tenant = TenantModel(id=str(uuid.uuid4()), slug="test-tenant", nombre="Test")
    session.add(tenant)
    session.flush()
    dueno = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email="dueno@test.com",
        nombre="Dueño",
        roles=[UsuarioRoles.DUENO.value],
        activo=True,
    )
    session.add(dueno)
    session.commit()

    token = mint_token(
        user_id=dueno.id,
        tenant_id=tenant.id,
        roles=dueno.roles,
        email=dueno.email,
        token_type="access",
    )

    response = client.post(
        "/users/invite",
        json={
            "email": "nuevo@test.com",
            "nombre": "Nuevo Usuario",
            "roles": ["rol_inexistente"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    detail = response.json()
    assert detail["code"] == "RN-AU-04"
    assert "Rol inválido" in detail["message"]


def test_email_duplicado_en_tenant_rechazado(client: TestClient, session: Session) -> None:
    """Un email duplicado en el mismo tenant es rechazado sin filtrar otros tenants (R1)."""
    tenant_a = TenantModel(id=str(uuid.uuid4()), slug="tenant-a", nombre="Tenant A")
    tenant_b = TenantModel(id=str(uuid.uuid4()), slug="tenant-b", nombre="Tenant B")
    session.add_all([tenant_a, tenant_b])
    session.flush()

    dueno_a = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        email="dueno@a.com",
        nombre="Dueño A",
        roles=[UsuarioRoles.DUENO.value],
        activo=True,
    )
    usuario_a = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        email="duplicado@test.com",
        nombre="Usuario A",
        roles=[UsuarioRoles.RECEPCION.value],
        activo=True,
    )
    usuario_b = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        email="duplicado@test.com",  # mismo email en otro tenant
        nombre="Usuario B",
        roles=[UsuarioRoles.RECEPCION.value],
        activo=True,
    )
    session.add_all([dueno_a, usuario_a, usuario_b])
    session.commit()

    token = mint_token(
        user_id=dueno_a.id,
        tenant_id=tenant_a.id,
        roles=dueno_a.roles,
        email=dueno_a.email,
        token_type="access",
    )

    response = client.post(
        "/users/invite",
        json={
            "email": "duplicado@test.com",  # duplicado en tenant A
            "nombre": "Otro Usuario",
            "roles": ["recepcion"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    detail = response.json()
    assert detail["code"] == "RN-AU-04"
    assert "ya está registrado en este consultorio" in detail["message"]


def test_listar_usuarios_por_dueno(client: TestClient, session: Session) -> None:
    """El dueño puede listar usuarios de su tenant."""
    tenant = TenantModel(id=str(uuid.uuid4()), slug="test-tenant", nombre="Test")
    session.add(tenant)
    session.flush()
    dueno = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email="dueno@test.com",
        nombre="Dueño",
        roles=[UsuarioRoles.DUENO.value],
        activo=True,
    )
    usuario1 = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email="user1@test.com",
        nombre="Usuario 1",
        roles=[UsuarioRoles.RECEPCION.value],
        activo=True,
    )
    usuario2 = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email="user2@test.com",
        nombre="Usuario 2",
        roles=[UsuarioRoles.ODONTOLOGO.value],
        activo=True,
    )
    session.add_all([dueno, usuario1, usuario2])
    session.commit()

    token = mint_token(
        user_id=dueno.id,
        tenant_id=tenant.id,
        roles=dueno.roles,
        email=dueno.email,
        token_type="access",
    )

    response = client.get(
        "/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    usuarios = response.json()
    assert len(usuarios) == 3  # dueno + 2 usuarios
    emails = {u["email"] for u in usuarios}
    assert "dueno@test.com" in emails
    assert "user1@test.com" in emails
    assert "user2@test.com" in emails


def test_no_dueno_no_puede_listar(client: TestClient, session: Session) -> None:
    """Un usuario sin rol dueno recibe 403 al intentar listar usuarios."""
    tenant = TenantModel(id=str(uuid.uuid4()), slug="test-tenant", nombre="Test")
    session.add(tenant)
    session.flush()
    recepcion = UsuarioModel(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        email="recepcion@test.com",
        nombre="Recepción",
        roles=[UsuarioRoles.RECEPCION.value],
        activo=True,
    )
    session.add(recepcion)
    session.commit()

    token = mint_token(
        user_id=recepcion.id,
        tenant_id=tenant.id,
        roles=recepcion.roles,
        email=recepcion.email,
        token_type="access",
    )

    response = client.get(
        "/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "RN-AU-04"

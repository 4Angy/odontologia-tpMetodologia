"""Tests de idempotencia del seed demo con auth activa (Task 5.2).

Verifica que re-ejecutar el seed no duplica usuarios ni crea tokens duplicados.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.agenda.models import UsuarioModel
from app.modules.agenda.seed_demo import seed_demo, TENANT_DEMO


def test_seed_demo_idempotente_sin_duplicar_usuarios(session: Session) -> None:
    """Re-ejecutar el seed no duplica usuarios (requisito de C-02, validado aquí)."""
    # Primera ejecución
    resultado1 = seed_demo(session)
    assert resultado1["tenant"] == TENANT_DEMO

    usuarios_despues_1 = session.scalars(
        select(UsuarioModel).where(UsuarioModel.tenant_id == TENANT_DEMO)
    ).all()
    count_1 = len(usuarios_despues_1)
    assert count_1 == 4  # recepcion, odontologo, dueno, multi

    # Segunda ejecución (idempotente)
    resultado2 = seed_demo(session)
    assert resultado2["tenant"] == TENANT_DEMO

    usuarios_despues_2 = session.scalars(
        select(UsuarioModel).where(UsuarioModel.tenant_id == TENANT_DEMO)
    ).all()
    count_2 = len(usuarios_despues_2)

    # No debe haber más usuarios
    assert count_2 == count_1 == 4

    # Los mismos usuarios deben existir (mismos IDs)
    ids_1 = {u.id for u in usuarios_despues_1}
    ids_2 = {u.id for u in usuarios_despues_2}
    assert ids_1 == ids_2


def test_seed_demo_usuarios_sin_password_hash(session: Session) -> None:
    """Los usuarios del seed tienen password_hash = None (pendiente de reset)."""
    seed_demo(session)

    usuarios = session.scalars(
        select(UsuarioModel).where(UsuarioModel.tenant_id == TENANT_DEMO)
    ).all()

    for usuario in usuarios:
        # Los usuarios del seed no tienen password (se setean vía reset)
        assert usuario.password_hash is None
        assert usuario.activo is True


def test_seed_demo_usuario_multi_3_roles(session: Session) -> None:
    """El usuario 'multi' tiene los 3 roles (DD-06)."""
    seed_demo(session)

    usuario_multi = session.scalars(
        select(UsuarioModel).where(
            UsuarioModel.tenant_id == TENANT_DEMO,
            UsuarioModel.email == "multi@demo.com",
        )
    ).first()

    assert usuario_multi is not None
    assert len(usuario_multi.roles) == 3
    assert "recepcion" in usuario_multi.roles
    assert "odontologo" in usuario_multi.roles
    assert "dueno" in usuario_multi.roles


def test_seed_demo_no_crea_tokens_auth(session: Session) -> None:
    """El seed no crea tokens de auth (se crean en login)."""
    seed_demo(session)

    # Verificar que no hay tokens en auth_token después del seed
    from app.modules.auth.models import AuthTokenModel

    tokens = session.scalars(AuthTokenModel.__table__.select()).all()
    assert len(tokens) == 0

"""Tests del modelo `auth_token` y del repositorio de familias (Tasks 1.1, 2.1).

TDD estricto (R11): rojo antes del código. Datos sintéticos (R14). Usa las
fixtures de `backend/conftest.py` (Postgres 16 real, esquema aislado por test).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.modules.agenda.models import TenantModel, UsuarioModel
from app.modules.auth.models import AuthTokenModel, PropositoToken
from app.modules.auth.repository import AuthTokenRepository

TENANT = "t-1"
AHORA = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def _crear_usuario(session, usuario_id: str, password_hash: str | None = None) -> UsuarioModel:
    session.add(TenantModel(id=TENANT, nombre="Demo"))
    session.flush()
    u = UsuarioModel(
        id=usuario_id,
        tenant_id=TENANT,
        email=f"{usuario_id}@demo.com",
        password_hash=password_hash,
        roles=["dueno"],
    )
    session.add(u)
    session.commit()
    return u


# --- Task 1.1: modelo/fila auth_token -------------------------------------------------


def test_fila_auth_token_se_guarda_con_claves(session):
    _crear_usuario(session, "u-1")
    repo = AuthTokenRepository(session)
    fila = repo.crear(
        jti="jti-a",
        usuario_id="u-1",
        familia_id="f-1",
        proposito=PropositoToken.REFRESH,
        expira=AHORA + timedelta(days=7),
        tenant_id=TENANT,
    )
    session.commit()
    leida = repo.obtener("jti-a")
    assert leida is not None
    assert leida.familia_id == "f-1"
    assert leida.usuario_id == "u-1"
    assert leida.proposito == PropositoToken.REFRESH.value
    assert leida.revoked is False
    assert leida.used_at is None
    assert leida.expira == AHORA + timedelta(days=7)


def test_dos_familias_no_colisionan_por_jti(session):
    _crear_usuario(session, "u-1")
    repo = AuthTokenRepository(session)
    repo.crear(jti="jti-x", usuario_id="u-1", familia_id="f-1",
               proposito=PropositoToken.REFRESH, expira=AHORA + timedelta(days=7),
               tenant_id=TENANT)
    # mismo jti distinto tenant sigue siendo PK global: se rechaza (FK/integridad)
    session.add(TenantModel(id=TENANT + "-b", nombre="B"))
    session.flush()
    with pytest.raises(Exception):
        repo.crear(jti="jti-x", usuario_id="u-1", familia_id="f-2",
                   proposito=PropositoToken.REFRESH, expira=AHORA + timedelta(days=7),
                   tenant_id=TENANT)


# --- Task 2.1: rotación / reuse / revocación en cascada / purge ------------------------


def test_rotacion_marca_usado_emite_nuevo_misma_familia(session):
    _crear_usuario(session, "u-1")
    repo = AuthTokenRepository(session)
    repo.crear(jti="j-1", usuario_id="u-1", familia_id="f-1",
               proposito=PropositoToken.REFRESH, expira=AHORA + timedelta(days=7),
               tenant_id=TENANT)
    session.commit()

    nuevo = repo.rotar(jti_viejo="j-1", jti_nuevo="j-2",
                       expira=AHORA + timedelta(days=7), now=AHORA)
    session.commit()
    assert nuevo is not None
    assert nuevo.id == "j-2"
    assert nuevo.familia_id == "f-1"
    viejo = repo.obtener("j-1")
    assert viejo.used_at == AHORA
    assert viejo.revoked is False  # usado pero aún reconocible como reuse


def test_reuse_revoca_familia_completa(session):
    _crear_usuario(session, "u-1")
    repo = AuthTokenRepository(session)
    repo.crear(jti="j-1", usuario_id="u-1", familia_id="f-1",
               proposito=PropositoToken.REFRESH, expira=AHORA + timedelta(days=7),
               tenant_id=TENANT)
    repo.rotar(jti_viejo="j-1", jti_nuevo="j-2", expira=AHORA + timedelta(days=7), now=AHORA)
    session.commit()

    fila = repo.obtener("j-1")
    deteccion = repo.estado(fila)
    assert deteccion.es_reuse is True

    repo.revocar_familia("f-1")
    session.commit()
    assert repo.obtener("j-1").revoked is True
    assert repo.obtener("j-2").revoked is True  # el válido más nuevo muere también


def test_familia_otro_usuario_no_toca(session):
    _crear_usuario(session, "u-1")
    repo = AuthTokenRepository(session)
    repo.crear(jti="j-a", usuario_id="u-1", familia_id="f-1",
               proposito=PropositoToken.REFRESH, expira=AHORA + timedelta(days=7),
               tenant_id=TENANT)
    repo.crear(jti="j-b", usuario_id="u-1", familia_id="f-2",
               proposito=PropositoToken.REFRESH, expira=AHORA + timedelta(days=7),
               tenant_id=TENANT)
    repo.revocar_familia("f-1")
    session.commit()
    assert repo.obtener("j-b").revoked is False


def test_purge_borra_solo_expirados(session):
    _crear_usuario(session, "u-1")
    repo = AuthTokenRepository(session)
    repo.crear(jti="j-viejo", usuario_id="u-1", familia_id="f-1",
               proposito=PropositoToken.REFRESH, expira=AHORA - timedelta(days=1),
               tenant_id=TENANT)
    repo.crear(jti="j-vivo", usuario_id="u-1", familia_id="f-2",
               proposito=PropositoToken.REFRESH, expira=AHORA + timedelta(days=7),
               tenant_id=TENANT)
    session.commit()
    borrados = repo.purgar_expirados(now=AHORA)
    assert borrados == 1
    assert repo.obtener("j-viejo") is None
    assert repo.obtener("j-vivo") is not None


def test_revocar_todas_las_familias_de_usuario(session):
    _crear_usuario(session, "u-1")
    repo = AuthTokenRepository(session)
    repo.crear(jti="j-1", usuario_id="u-1", familia_id="f-1",
               proposito=PropositoToken.REFRESH, expira=AHORA + timedelta(days=7),
               tenant_id=TENANT)
    repo.crear(jti="j-2", usuario_id="u-1", familia_id="f-2",
               proposito=PropositoToken.REFRESH, expira=AHORA + timedelta(days=7),
               tenant_id=TENANT)
    repo.revocar_de_usuario("u-1")
    session.commit()
    assert repo.obtener("j-1").revoked is True
    assert repo.obtener("j-2").revoked is True

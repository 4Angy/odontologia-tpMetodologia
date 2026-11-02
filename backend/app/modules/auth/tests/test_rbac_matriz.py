"""Tests de la matriz RBAC (Task 3.1): constantes de 03_actores_y_roles.md.

La unión de roles (RN-AU-04) es la base de todo permiso; acá se prueba que:
- `dueno` cubre la matriz completa; y
- los tres roles acumulados en UNA persona cubren la matriz completa (DD-06),
  mientras que un mínimo no-cantidad de 2 roles deja recursos sin cubrir.
"""
from __future__ import annotations

from app.modules.auth.rbac import MATRIZ_RBAC, permisos_de_union

LOS_TRES = ["recepcion", "odontologo", "dueno"]


def test_dueno_cubre_toda_la_matriz():
    assert permisos_de_union(["dueno"]) == set(MATRIZ_RBAC)


def test_3_roles_en_1_persona_cubre_matriz():
    assert permisos_de_union(LOS_TRES) == set(MATRIZ_RBAC)


def test_dos_roles_no_cubren_la_matriz():
    assert permisos_de_union(["recepcion", "odontologo"]) != set(MATRIZ_RBAC)


def test_recurso_solo_para_dueno():
    assert MATRIZ_RBAC["usuarios_tenant"] == {"dueno"}
    assert MATRIZ_RBAC["configuracion_tenant"] == {"dueno"}
    assert MATRIZ_RBAC["auditoria"] == {"dueno"}


def test_cobros_sin_odontologo():
    """El odontólogo no cobra (matriz: Cobros/señas '—')."""
    assert "odontologo" not in MATRIZ_RBAC["cobros"]
    assert "recepcion" in MATRIZ_RBAC["cobros"]

"""Matriz RBAC del sistema (de 03_actores_y_roles.md).

Mapa recurso → roles permitidos. Para permiso efectivo por unión, usar
`has_effective_permission` de security.py con este mapa. El rol `dueno`
incluye todo, pero la matriz se expresa explícitamente para claridad.

Registro de rol activo por acción (DD-06): cada endpoint puede importar
este mapa y registrar qué rol se usó en logs/auditoría.
"""
from __future__ import annotations

from typing import Final

# Matriz de permisos: recurso → roles que pueden acceder
# Fuente: knowledge-base/03_actores_y_roles.md
MATRIZ_RBAC: Final = {
    "agenda": {"recepcion", "dueno"},
    "reserva_publica": {"recepcion", "dueno"},
    "pacientes": {"recepcion", "odontologo", "dueno"},
    "evoluciones": {"odontologo", "dueno"},
    "presupuestos": {"recepcion", "odontologo", "dueno"},
    "cobros": {"recepcion", "dueno"},
    "deudas": {"recepcion", "dueno"},
    "recordatorios": {"recepcion", "dueno"},
    "usuarios_tenant": {"dueno"},
    "configuracion_tenant": {"dueno"},
    "exportacion": {"recepcion", "odontologo", "dueno"},
    "auditoria": {"dueno"},
}


def permisos_de_union(roles: list[str] | tuple[str, ...]) -> set[str]:
    """Calcula la unión de recursos accesibles dado una lista de roles.

    Ejemplo: ["recepcion", "odontologo"] → unión de recursos que ambos pueden ver.
    """
    recursos = set()
    for rol in roles:
        for recurso, roles_permitidos in MATRIZ_RBAC.items():
            if rol in roles_permitidos:
                recursos.add(recurso)
    return recursos


__all__ = ["MATRIZ_RBAC", "permisos_de_union"]

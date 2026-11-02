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
PERMISOS_AGENDA: Final = ("recepcion", "dueno")
PERMISOS_RESERVA_PUBLICA: Final = ("recepcion", "dueno")
PERMISOS_PACIENTES: Final = ("recepcion", "odontologo", "dueno")
PERMISOS_EVOLUCIONES: Final = ("odontologo", "dueno")
PERMISOS_PRESUPUESTOS: Final = ("recepcion", "odontologo", "dueno")
PERMISOS_COBROS: Final = ("recepcion", "dueno")
PERMISOS_DEUDAS: Final = ("recepcion", "dueno")
PERMISOS_RECORDATORIOS: Final = ("recepcion", "dueno")
PERMISOS_USUARIOS: Final = ("dueno",)
PERMISOS_CONFIGURACION: Final = ("dueno",)
PERMISOS_EXPORTACION: Final = ("recepcion", "odontologo", "dueno")
PERMISOS_AUDITORIA: Final = ("dueno",)

# Mapa unificado por recurso para lookup dinámico
RECURSO_A_ROLES: Final = {
    "agenda": PERMISOS_AGENDA,
    "reserva_publica": PERMISOS_RESERVA_PUBLICA,
    "pacientes": PERMISOS_PACIENTES,
    "evoluciones": PERMISOS_EVOLUCIONES,
    "presupuestos": PERMISOS_PRESUPUESTOS,
    "cobros": PERMISOS_COBROS,
    "deudas": PERMISOS_DEUDAS,
    "recordatorios": PERMISOS_RECORDATORIOS,
    "usuarios": PERMISOS_USUARIOS,
    "configuracion": PERMISOS_CONFIGURACION,
    "exportacion": PERMISOS_EXPORTACION,
    "auditoria": PERMISOS_AUDITORIA,
}

__all__ = [
    "PERMISOS_AGENDA",
    "PERMISOS_RESERVA_PUBLICA",
    "PERMISOS_PACIENTES",
    "PERMISOS_EVOLUCIONES",
    "PERMISOS_PRESUPUESTOS",
    "PERMISOS_COBROS",
    "PERMISOS_DEUDAS",
    "PERMISOS_RECORDATORIOS",
    "PERMISOS_USUARIOS",
    "PERMISOS_CONFIGURACION",
    "PERMISOS_EXPORTACION",
    "PERMISOS_AUDITORIA",
    "RECURSO_A_ROLES",
]

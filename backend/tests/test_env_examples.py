"""Higiene de secretos en los archivos de ejemplo de variables de entorno.

Cubre el escenario del spec `foundation/runtime`:
"los archivos de ejemplo de variables de entorno del proyecto no contienen
valores de secreto real, sólo marcadores de posición y su descripción".
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ_REPO = Path(__file__).resolve().parents[2]

ARCHIVOS_EJEMPLO = (
    RAIZ_REPO / ".env.example",
    RAIZ_REPO / "backend" / ".env.example",
    RAIZ_REPO / "frontend" / ".env.example",
)

#: Variables cuyo valor nunca debe venir relleno.
VARIABLES_SECRETAS = {
    "JWT_SECRET",
    "WHATSAPP_API_TOKEN",
    "WHATSAPP_PHONE_ID",
    "MP_ACCESS_TOKEN",
    "MP_WEBHOOK_SECRET",
    "SMTP_URL",
}

#: Un valor que parezca un secreto real (hex largo, token, password en URI).
PATRON_SECRETO = re.compile(r"[0-9a-f]{32,}|sk-[A-Za-z0-9]{16,}|APP_USR-[A-Za-z0-9-]{8,}")
#: Una URI con credenciales embebidas.
PATRON_URI_CON_CREDENCIALES = re.compile(r"[a-zA-Z0-9+.\-]+://[^:@/\s]*:(?P<password>[^@/\s]*)@")

#: Contraseñas de desarrollo documentadas (las mismas que usan el compose y el
#: Postgres local). No son secretos: son defaults públicos y conocidos.
CONTRASENAS_DE_DEV = {"odontologia", "clave", "password", "postgres"}


def _lineas_de_valor(archivo: Path) -> list[tuple[str, str]]:
    pares: list[tuple[str, str]] = []
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        limpia = linea.strip()
        if not limpia or limpia.startswith("#") or "=" not in limpia:
            continue
        nombre, valor = limpia.split("=", 1)
        pares.append((nombre.strip(), valor.strip()))
    return pares


@pytest.mark.parametrize("archivo", ARCHIVOS_EJEMPLO, ids=lambda a: a.name)
def test_el_archivo_de_ejemplo_existe(archivo: Path) -> None:
    assert archivo.exists(), f"falta {archivo}"


@pytest.mark.parametrize("archivo", ARCHIVOS_EJEMPLO, ids=lambda a: a.name)
def test_los_ejemplos_no_contienen_secretos_reales(archivo: Path) -> None:
    for nombre, valor in _lineas_de_valor(archivo):
        assert not PATRON_SECRETO.search(valor), (
            f"{archivo.name}: {nombre} parece un valor de secreto real"
        )
        credenciales = PATRON_URI_CON_CREDENCIALES.search(valor)
        if credenciales is not None:
            password = credenciales.group("password")
            assert password in CONTRASENAS_DE_DEV, (
                f"{archivo.name}: {nombre} contiene una contraseña real en la URI"
            )


@pytest.mark.parametrize("archivo", ARCHIVOS_EJEMPLO, ids=lambda a: a.name)
def test_las_variables_secretas_estan_vacias_o_con_marcador(archivo: Path) -> None:
    for nombre, valor in _lineas_de_valor(archivo):
        if nombre not in VARIABLES_SECRETAS:
            continue
        es_marcador = (
            valor == ""
            or "generar" in valor.lower()
            or "colocar" in valor.lower()
            or "completar" in valor.lower()
            or "<" in valor
        )
        assert es_marcador, (
            f"{archivo.name}: {nombre} debería estar vacío o con un marcador, no {valor!r}"
        )

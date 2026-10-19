"""Tests de los health checks (C-01, grupo 5).

TDD estricto: mínimo 2 casos por comportamiento (R11).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _todas_las_sondas_ok() -> dict:
    return {"database": lambda: True, "redis": lambda: True}


def test_health_responde_200_con_estado_servicio_y_version():
    cliente = TestClient(create_app())

    r = cliente.get("/health")

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["status"] == "ok"
    assert cuerpo["service"]
    assert cuerpo["version"]


def test_health_no_consulta_las_dependencias():
    def _falla() -> bool:
        raise RuntimeError("la base está caída")

    cliente = TestClient(create_app(probes={"database": _falla, "redis": _falla}))

    r = cliente.get("/health")

    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready_responde_200_cuando_todas_las_dependencias_operan():
    cliente = TestClient(create_app(probes=_todas_las_sondas_ok()))

    r = cliente.get("/health/ready")

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["status"] == "ready"
    assert cuerpo["components"] == {"database": "ok", "redis": "ok"}


def test_ready_responde_503_identificando_el_componente_fallido():
    cliente = TestClient(
        create_app(probes={"database": lambda: False, "redis": lambda: True})
    )

    r = cliente.get("/health/ready")

    assert r.status_code == 503
    cuerpo = r.json()
    assert cuerpo["status"] == "not_ready"
    assert cuerpo["components"]["database"] == "fallo"
    assert cuerpo["components"]["redis"] == "ok"


def test_ready_responde_503_cuando_falla_redis_y_la_base_datos_no():
    cliente = TestClient(
        create_app(probes={"database": lambda: True, "redis": lambda: False})
    )

    r = cliente.get("/health/ready")

    assert r.status_code == 503
    cuerpo = r.json()
    assert cuerpo["status"] == "not_ready"
    assert cuerpo["components"]["redis"] == "fallo"
    assert cuerpo["components"]["database"] == "ok"


def test_ready_responde_503_cuando_la_sonda_lanza_excepcion():
    def _explota() -> bool:
        raise RuntimeError("no conecta")

    cliente = TestClient(
        create_app(probes={"database": _explota, "redis": lambda: True})
    )

    r = cliente.get("/health/ready")

    assert r.status_code == 503
    assert r.json()["components"]["database"] == "fallo"


def test_ready_no_expone_credenciales_ni_uris():
    cliente = TestClient(
        create_app(probes={"database": lambda: False, "redis": lambda: False})
    )

    cuerpo = cliente.get("/health/ready").text

    assert "://" not in cuerpo
    assert "password" not in cuerpo.lower()
    assert "clave" not in cuerpo.lower()

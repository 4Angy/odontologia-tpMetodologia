"""Tests del contrato de error `{code, message, action?}` (C-01, grupo 4).

TDD estricto: mínimo 2 casos por comportamiento (R11).
"""
from __future__ import annotations

import json
import logging

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.errors import GENERIC_ERROR_CODE, AppError, ErrorAction
from app.main import create_app


def _cliente_que_falla(exc: Exception) -> TestClient:
    app = create_app()

    @app.get("/boom")
    def _boom():  # pragma: no cover - sólo dispara la excepción
        raise exc

    return TestClient(app, raise_server_exceptions=False)


def test_error_de_negocio_produce_sobre_con_code_message_y_action():
    cliente = _cliente_que_falla(
        AppError(
            "RN-AG-01",
            "No se puede cancelar con menos de 24 h de antelación.",
            action=ErrorAction("reprogramar", "Coordiná manualmente un nuevo horario."),
            status_code=409,
        )
    )

    r = cliente.get("/boom")

    assert r.status_code == 409
    assert r.json() == {
        "code": "RN-AG-01",
        "message": "No se puede cancelar con menos de 24 h de antelación.",
        "action": {"type": "reprogramar", "hint": "Coordiná manualmente un nuevo horario."},
    }


def test_error_sin_accion_no_incluye_el_campo_action():
    cliente = _cliente_que_falla(AppError("RN-CO-05", "El saldo es derivado.", status_code=409))

    cuerpo = cliente.get("/boom").json()

    assert "action" not in cuerpo
    assert set(cuerpo) == {"code", "message"}


def test_http_exception_con_detail_dict_conserva_el_contrato():
    cliente = _cliente_que_falla(
        HTTPException(status_code=404, detail={"code": "RN-AU-01", "message": "Turno no encontrado."})
    )

    r = cliente.get("/boom")

    assert r.status_code == 404
    assert r.json() == {"code": "RN-AU-01", "message": "Turno no encontrado."}


def test_http_exception_con_texto_usa_el_codigo_generico():
    cliente = _cliente_que_falla(HTTPException(status_code=418, detail="soy una tetera"))

    cuerpo = cliente.get("/boom").json()

    assert cuerpo["code"] == GENERIC_ERROR_CODE
    assert cuerpo["message"] == "soy una tetera"


def test_error_inesperado_no_expone_trazas_ni_sql():
    cliente = _cliente_que_falla(RuntimeError("SELECT * FROM turno WHERE dni = '123'"))

    r = cliente.get("/boom")
    cuerpo = r.json()

    assert r.status_code == 500
    assert cuerpo["code"] == GENERIC_ERROR_CODE
    serializado = json.dumps(cuerpo)
    assert "SELECT" not in serializado
    assert "Traceback" not in serializado
    assert "turno" not in serializado
    assert "/app/" not in serializado


def test_el_log_del_error_coincide_con_el_code_devuelto_al_usuario(caplog):
    logger = logging.getLogger("odontologia.api")
    cliente = _cliente_que_falla(
        AppError("RN-AG-01", "Fuera de término.", status_code=409)
    )

    with caplog.at_level(logging.WARNING, logger="odontologia.api"):
        respuesta = cliente.get("/boom")

    registros = [r for r in caplog.records if r.name == "odontologia.api"]
    assert registros, "el error debe registrarse"
    assert registros[-1].context["code"] == respuesta.json()["code"]

"""Tests del logging estructurado (C-01, grupo 3).

TDD estricto: mínimo 2 casos por comportamiento (R11).
"""
from __future__ import annotations

import json
import logging

from app.core.logging import (
    REDACTED,
    StructuredFormatter,
    configure_logging,
    log_event,
    redact,
    scrub_uri,
)


def _registro(nombre: str = "test.log") -> logging.LogRecord:
    return logging.getLogger(nombre).makeRecord(
        nombre, logging.INFO, "fichero.py", 1, "mensaje", None, None
    )


def test_el_formato_es_json_con_ts_utc_nivel_logger_mensaje_y_contexto():
    registro = _registro()
    registro.context = {"env": "test", "version": "0.1.0"}

    datos = json.loads(StructuredFormatter().format(registro))

    assert datos["level"] == "INFO"
    assert datos["logger"] == "test.log"
    assert datos["message"] == "mensaje"
    assert datos["ts"].endswith("Z")
    assert datos["context"] == {"env": "test", "version": "0.1.0"}


def test_el_contexto_va_en_campos_separados_y_no_dentro_del_mensaje():
    registro = _registro()
    registro.context = {"code": "RN-AG-01"}

    datos = json.loads(StructuredFormatter().format(registro))

    assert datos["context"]["code"] == "RN-AG-01"
    assert "RN-AG-01" not in datos["message"]


def test_las_claves_sensibles_se_redactan():
    datos = redact({"jwt_secret": "valor", "otro": "visible"})

    assert datos["jwt_secret"] == REDACTED
    assert datos["otro"] == "visible"


def test_la_contrasena_de_una_uri_se_redacta():
    uri = "postgresql+psycopg://usuario:clave-secreta@db:5432/odontologia"

    resultado = scrub_uri(uri)

    assert "clave-secreta" not in resultado
    assert "db:5432" in resultado
    assert "usuario" in resultado


def test_los_valores_sensibles_no_aparecen_en_el_log():
    secreto = "token-super-secreto"
    registro = _registro()
    registro.context = {"jwt_secret": secreto, "mp_access_token": secreto, "otro": "visible"}

    salida = StructuredFormatter(secrets=[secreto]).format(registro)

    assert secreto not in salida
    assert REDACTED in salida
    assert "visible" in salida


def test_configure_logging_no_rompe_los_handlers_ajenos():
    logger = logging.getLogger("otro.proceso")
    logger.addHandler(logging.NullHandler())
    handlers_previos = list(logger.handlers)

    configure_logging("INFO")

    assert logger.handlers == handlers_previos


def test_log_event_manda_el_contexto_al_registro():
    logger = logging.getLogger("test.event")
    registros: list[logging.LogRecord] = []

    class _Capturador(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            registros.append(record)

    logger.addHandler(_Capturador())
    logger.setLevel(logging.INFO)

    log_event(logger, logging.WARNING, "error de negocio", code="RN-AG-01", status=409)

    assert registros[-1].context == {"code": "RN-AG-01", "status": 409}
    assert registros[-1].levelname == "WARNING"

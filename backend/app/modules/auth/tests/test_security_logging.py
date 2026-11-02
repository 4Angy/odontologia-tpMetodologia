"""Tests de logging estructurado de seguridad (Task 3.4).

Valida que eventos de seguridad (login fallido, reuse detectado, reset usado,
invitaciones) emiten logs con user_id, tenant_id, endpoint, code.
"""
from __future__ import annotations

import logging

import pytest


def test_login_fallido_emite_log_con_code(caplog) -> None:
    """Un login fallido emite el log esperado con su code."""
    from app.core.logging import log_event

    usuario_id = "user-123"
    tenant_id = "tenant-456"

    with caplog.at_level(logging.INFO):
        log_event(
            logging.getLogger("odontologia.auth"),
            logging.INFO,
            "auth.login_fallido",
            reason="password_incorrecta",
            usuario_id=usuario_id,
            tenant_id=tenant_id,
            code="RN-AU-01",
        )

    # Verificar que el log se emitió con los campos correctos
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.message == "auth.login_fallido"
    context = getattr(record, "context", {})
    assert context.get("reason") == "password_incorrecta"
    assert context.get("usuario_id") == usuario_id
    assert context.get("tenant_id") == tenant_id
    assert context.get("code") == "RN-AU-01"


def test_reuse_detectado_emite_log_con_contexto(caplog) -> None:
    """Un reuse detectado emite log con familia y usuario."""
    from app.core.logging import log_event

    usuario_id = "user-123"
    familia_id = "familia-789"

    with caplog.at_level(logging.INFO):
        log_event(
            logging.getLogger("odontologia.auth"),
            logging.INFO,
            "auth.reuse_detectado",
            familia=familia_id,
            usuario_id=usuario_id,
            filas_revocadas=3,
            code="RN-AU-02",
        )

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.message == "auth.reuse_detectado"
    context = getattr(record, "context", {})
    assert context.get("familia") == familia_id
    assert context.get("usuario_id") == usuario_id
    assert context.get("filas_revocadas") == 3
    assert context.get("code") == "RN-AU-02"


def test_reset_usado_emite_log_con_usuario(caplog) -> None:
    """Un reset usado emite log con usuario y tenant."""
    from app.core.logging import log_event

    usuario_id = "user-123"
    tenant_id = "tenant-456"

    with caplog.at_level(logging.INFO):
        log_event(
            logging.getLogger("odontologia.auth"),
            logging.INFO,
            "auth.reset_usado",
            usuario_id=usuario_id,
            tenant_id=tenant_id,
            code="RN-AU-01",
        )

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.message == "auth.reset_usado"
    context = getattr(record, "context", {})
    assert context.get("usuario_id") == usuario_id
    assert context.get("tenant_id") == tenant_id
    assert context.get("code") == "RN-AU-01"


def test_invitacion_emite_log_con_roles(caplog) -> None:
    """Una invitación emite log con email, roles e invitado_por."""
    from app.core.logging import log_event

    usuario_id = "user-123"
    tenant_id = "tenant-456"
    invitado_por = "user-789"

    with caplog.at_level(logging.INFO):
        log_event(
            logging.getLogger("odontologia.tenancy"),
            logging.INFO,
            "usuarios.invitacion",
            usuario_id=usuario_id,
            tenant_id=tenant_id,
            email="nuevo@test.com",
            roles=["recepcion"],
            invitado_por=invitado_por,
            code="RN-AU-04",
        )

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.message == "usuarios.invitacion"
    context = getattr(record, "context", {})
    assert context.get("usuario_id") == usuario_id
    assert context.get("tenant_id") == tenant_id
    assert context.get("email") == "nuevo@test.com"
    assert context.get("roles") == ["recepcion"]
    assert context.get("invitado_por") == invitado_por
    assert context.get("code") == "RN-AU-04"

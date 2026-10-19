"""Tests de configuración por variables de entorno (C-01, grupo 2).

TDD estricto: mínimo 2 casos por comportamiento (R11).
"""
from __future__ import annotations

import logging

import pytest

from app.core.config import CANONICAL_ENV_VARS, ConfigError, load_settings


def test_carga_las_14_variables_canonicas(env_valido):
    settings = load_settings(env_valido)

    assert settings.database_url == env_valido["DATABASE_URL"]
    assert settings.redis_url == env_valido["REDIS_URL"]
    assert settings.jwt_access_min == 15
    assert settings.jwt_refresh_days == 7
    assert settings.seed_demo is False
    assert str(settings.tenant_default_tz) == "America/Argentina/Buenos_Aires"
    assert settings.whatsapp_provider == "official"
    assert settings.whatsapp_phone_id == "5411000000000"
    assert settings.public_base_url == "https://app.ejemplo.com"
    assert settings.app_env == "test"
    assert len(CANONICAL_ENV_VARS) == 14


def test_los_tipos_se_parsean(env_valido):
    env_valido["JWT_ACCESS_MIN"] = "30"
    env_valido["JWT_REFRESH_DAYS"] = "14"
    env_valido["SEED_DEMO"] = "true"

    settings = load_settings(env_valido)

    assert settings.jwt_access_min == 30
    assert settings.jwt_refresh_days == 14
    assert settings.seed_demo is True
    assert str(settings.tenant_default_tz) == "America/Argentina/Buenos_Aires"


def test_los_secretos_no_se_exponen_como_texto_plano(env_valido):
    settings = load_settings(env_valido)

    assert settings.jwt_secret is not None
    assert "s" * 64 not in str(settings.jwt_secret)
    assert settings.jwt_secret_plain() == "s" * 64
    assert "token-de-whatsapp" in settings.sensitive_values()


def test_variable_invalida_aborta_nombrando_la_variable_y_el_formato(env_valido):
    env_valido["JWT_ACCESS_MIN"] = "quince"

    with pytest.raises(ConfigError) as exc:
        load_settings(env_valido)

    mensaje = str(exc.value)
    assert "JWT_ACCESS_MIN" in mensaje
    assert "integer" in mensaje.lower()


def test_variable_requerida_ausente_aborta_nombrando_la_variable(env_valido):
    del env_valido["DATABASE_URL"]

    with pytest.raises(ConfigError) as exc:
        load_settings(env_valido)

    assert "DATABASE_URL" in str(exc.value)


def test_proveedor_whatsapp_invalido_aborta(env_valido):
    env_valido["WHATSAPP_PROVIDER"] = "otro-proveedor"

    with pytest.raises(ConfigError) as exc:
        load_settings(env_valido)

    assert "WHATSAPP_PROVIDER" in str(exc.value)


def test_sin_jwt_secret_fuera_de_dev_test_aborta(env_valido):
    env_valido["APP_ENV"] = "prod"
    del env_valido["JWT_SECRET"]

    with pytest.raises(ConfigError) as exc:
        load_settings(env_valido)

    assert "JWT_SECRET" in str(exc.value)


def test_sin_jwt_secret_en_dev_usa_un_secreto_efimero(env_valido):
    env_valido["APP_ENV"] = "dev"
    del env_valido["JWT_SECRET"]

    settings = load_settings(env_valido)

    assert settings.jwt_secret is not None
    assert len(settings.jwt_secret_plain()) >= 32


def test_sin_jwt_secret_en_dev_avisa_que_usa_un_secreto_temporal(env_valido, caplog):
    """El arranque debe avisar explícitamente (spec: escenario 'aviso explícito')."""
    env_valido["APP_ENV"] = "dev"
    del env_valido["JWT_SECRET"]

    with caplog.at_level(logging.WARNING, logger="odontologia.config"):
        load_settings(env_valido)

    avisos = [r for r in caplog.records if r.name == "odontologia.config"]
    assert avisos, "debe emitirse un aviso cuando se usa el secreto temporal"
    mensaje = avisos[-1].getMessage()
    assert "JWT_SECRET" in mensaje
    assert "TEMPORAL" in mensaje.upper()


def test_el_secreto_efimero_es_distinto_en_cada_carga(env_valido):
    env_valido["APP_ENV"] = "dev"
    del env_valido["JWT_SECRET"]

    primero = load_settings(env_valido).jwt_secret_plain()
    segundo = load_settings(env_valido).jwt_secret_plain()

    assert primero != segundo


def test_jwt_secret_corto_en_prod_aborta(env_valido):
    env_valido["APP_ENV"] = "prod"
    env_valido["JWT_SECRET"] = "corto"

    with pytest.raises(ConfigError) as exc:
        load_settings(env_valido)

    assert "JWT_SECRET" in str(exc.value)


def test_jwt_secret_vacio_en_prod_aborta_diciendo_que_falta(env_valido):
    env_valido["APP_ENV"] = "prod"
    env_valido["JWT_SECRET"] = ""

    with pytest.raises(ConfigError) as exc:
        load_settings(env_valido)

    mensaje = str(exc.value)
    assert "JWT_SECRET" in mensaje
    assert "falta" in mensaje

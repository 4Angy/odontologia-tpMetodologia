"""Tests del servicio de dominio de cancelación (Tasks 1.1+).

TDD estricto: estos tests se escriben ANTES de la implementación.
Datos 100% sintéticos (R14). Sin HTTP ni DB: servicio puro.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.modules.agenda.service import (
    AgendaCancelService,
    ForbiddenError,
    FueraDeTerminoError,
    MotivoInvalidoError,
    TerminalStateError,
    TurnoNotFoundError,
    TurnoPasadoError,
    Turno,
    User,
    resolver_antelacion,
    turno_activo,
)

TENANT_A = "tenant-demo-a"
PROFESIONAL_1 = "prof-demo-1"


def _ahora_utc() -> datetime:
    return datetime(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)


def _user_recepcion() -> User:
    return User(id="user-recep-1", tenant_id=TENANT_A, roles=("recepcion",))


def _turno_confirmado(inicio: datetime) -> Turno:
    return Turno(
        id="turno-1",
        tenant_id=TENANT_A,
        profesional_id=PROFESIONAL_1,
        profesional_usuario_id="user-odonto-1",
        prestacion_id=None,
        inicio=inicio,
        fin=inicio + timedelta(minutes=30),
        estado="confirmado",
    )


# --- 1.1: cancelación en término + liberación observable ---------------------

def test_cancel_en_termino_cambia_a_cancelado_con_auditoria():
    """GIVEN turno confirmado con inicio - now > antelación
    WHEN se cancela con motivo válido
    THEN estado=cancelado + cancelled_by/cancelled_at/motivo registrados."""
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    turno = _turno_confirmado(inicio=ahora + timedelta(hours=48))
    user = _user_recepcion()

    resultado = svc.cancel(
        tenant_id=TENANT_A,
        turno=turno,
        user=user,
        motivo="Paciente lo solicita por teléfono",
        now_utc=ahora,
        antelacion_hs=24,
        tiene_senia=False,
    )

    assert resultado.estado == "cancelado"
    assert resultado.cancelled_by == user.id
    assert resultado.cancelled_at is not None
    assert resultado.cancelled_at.tzinfo is not None, "cancelled_at debe ser aware (R7)"
    assert resultado.cancelled_at >= ahora
    assert resultado.motivo == "Paciente lo solicita por teléfono"


def test_cancel_libera_horario_no_cuenta_como_activo():
    """GIVEN query de activos por (tenant, profesional, rango) que incluía el turno
    WHEN el turno se cancela en término
    THEN ya no cuenta como activo (slot libre observable)."""
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    turno = _turno_confirmado(inicio=ahora + timedelta(hours=48))
    assert turno_activo(turno) is True

    # Segundo estado cancelable del spec: pendiente_confirmacion
    turno2 = _turno_confirmado(inicio=ahora + timedelta(hours=72))
    turno2.id = "turno-2"
    turno2.estado = "pendiente_confirmacion"
    assert turno_activo(turno2) is True

    svc.cancel(
        tenant_id=TENANT_A, turno=turno, user=_user_recepcion(),
        motivo="x", now_utc=ahora, antelacion_hs=24, tiene_senia=False,
    )
    svc.cancel(
        tenant_id=TENANT_A, turno=turno2, user=_user_recepcion(),
        motivo="y", now_utc=ahora, antelacion_hs=24, tiene_senia=False,
    )

    activos = [t for t in (turno, turno2) if turno_activo(t)]
    assert activos == []


# --- 1.3: antelación ---------------------------------------------------------

def test_cancel_fuera_de_termino_no_muta_y_devuelve_rn_ag_01():
    """GIVEN inicio - now < antelación WHEN se intenta cancelar
    THEN 409 RN-AG-01 con action reprogramar placeholder y el turno no muta."""
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    turno = _turno_confirmado(inicio=ahora + timedelta(hours=2))

    with pytest.raises(FueraDeTerminoError) as exc:
        svc.cancel(
            tenant_id=TENANT_A, turno=turno, user=_user_recepcion(),
            motivo="x", now_utc=ahora, antelacion_hs=24, tiene_senia=False,
        )

    assert exc.value.code == "RN-AG-01"
    assert exc.value.status == 409
    assert exc.value.action["type"] == "reprogramar"
    assert exc.value.action["hint"]
    assert turno.estado == "confirmado"
    assert turno.cancelled_by is None and turno.cancelled_at is None


def test_cancel_borde_exacto_igual_antelacion_acepta():
    """GIVEN inicio - now == antelación THEN la cancelación es aceptada (inclusivo)."""
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    turno = _turno_confirmado(inicio=ahora + timedelta(hours=24))

    resultado = svc.cancel(
        tenant_id=TENANT_A, turno=turno, user=_user_recepcion(),
        motivo="x", now_utc=ahora, antelacion_hs=24, tiene_senia=False,
    )
    assert resultado.estado == "cancelado"


def test_cancel_antelacion_cero_acepta_hasta_minuto_cero():
    """GIVEN tenant con antelacion=0 y turno aún no iniciado THEN acepta."""
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    turno = _turno_confirmado(inicio=ahora + timedelta(minutes=5))

    resultado = svc.cancel(
        tenant_id=TENANT_A, turno=turno, user=_user_recepcion(),
        motivo="x", now_utc=ahora, antelacion_hs=0, tiene_senia=False,
    )
    assert resultado.estado == "cancelado"

    # ...pero un turno ya iniciado (inicio == now → pasado en el margen) se rechaza
    turno2 = _turno_confirmado(inicio=ahora - timedelta(seconds=1))
    turno2.id = "turno-pasado-0"
    with pytest.raises(Exception) as exc2:  # noqa: PT011 - cualquier 409 terminal
        svc.cancel(
            tenant_id=TENANT_A, turno=turno2, user=_user_recepcion(),
            motivo="x", now_utc=ahora, antelacion_hs=0, tiene_senia=False,
        )
    assert getattr(exc2.value, "status", None) == 409


def test_resolver_antelacion_config_fallback_usa_24h_con_log(caplog):
    """GIVEN tenant sin fila en config WHEN se resuelve THEN fallback 24h + log."""
    with caplog.at_level("WARNING"):
        valor = resolver_antelacion(lambda _t: None, TENANT_A)
    assert valor == 24
    assert any("fallback" in r.message for r in caplog.records)

    # Config presente rige; prestacion se ignora (UNA global extensible).
    assert resolver_antelacion(lambda _t: 48, TENANT_A) == 48
    assert resolver_antelacion(lambda _t: 48, TENANT_A, prestacion="prest-x") == 48


# --- 1.5: idempotencia + orden + terminales -----------------------------------

def test_cancel_idempotente_doble_cancelacion_sin_duplicar_auditoria():
    """GIVEN turno activo cancelable WHEN doble cancel THEN 2× éxito y 1 auditoría."""
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    turno = _turno_confirmado(inicio=ahora + timedelta(hours=48))
    user = _user_recepcion()

    primero = svc.cancel(
        tenant_id=TENANT_A, turno=turno, user=user, motivo="A",
        now_utc=ahora, antelacion_hs=24, tiene_senia=False,
    )
    auditoria = (primero.cancelled_by, primero.cancelled_at, primero.motivo)
    segundo = svc.cancel(
        tenant_id=TENANT_A, turno=turno, user=user, motivo="A",
        now_utc=ahora + timedelta(minutes=1), antelacion_hs=24, tiene_senia=False,
    )
    assert segundo.estado == "cancelado"
    assert (segundo.cancelled_by, segundo.cancelled_at, segundo.motivo) == auditoria


def test_cancel_motivo_distinto_conserva_primera_auditoria():
    """GIVEN turno cancelado con motivo A WHEN otro POST con motivo B
    THEN 200 y conserva motivo A + auditoría original."""
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    turno = _turno_confirmado(inicio=ahora + timedelta(hours=48))
    user = _user_recepcion()
    svc.cancel(
        tenant_id=TENANT_A, turno=turno, user=user, motivo="Motivo A",
        now_utc=ahora, antelacion_hs=24, tiene_senia=False,
    )
    ts_original = turno.cancelled_at

    resultado = svc.cancel(
        tenant_id=TENANT_A, turno=turno, user=user, motivo="Motivo B distinto",
        now_utc=ahora + timedelta(hours=1), antelacion_hs=24, tiene_senia=False,
    )
    assert resultado.estado == "cancelado"
    assert resultado.motivo == "Motivo A"
    assert resultado.cancelled_at == ts_original


def test_cancel_terminal_presente_ausente_reprogramado_409():
    """GIVEN turnos en presente/ausente/reprogramado WHEN cancelar THEN 409 sin mutar."""
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    for estado in ("presente", "ausente", "reprogramado"):
        turno = _turno_confirmado(inicio=ahora + timedelta(hours=48))
        turno.id = f"turno-{estado}"
        turno.estado = estado
        with pytest.raises(TerminalStateError) as exc:
            svc.cancel(
                tenant_id=TENANT_A, turno=turno, user=_user_recepcion(),
                motivo="x", now_utc=ahora, antelacion_hs=24, tiene_senia=False,
            )
        assert exc.value.status == 409
        assert exc.value.code
        assert turno.estado == estado


def test_cancel_pasado_409_aunque_antelacion_cero():
    """GIVEN turno con inicio < now WHEN cancelar THEN 409 terminal sin mutar."""
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    turno = _turno_confirmado(inicio=ahora - timedelta(hours=1))
    with pytest.raises(TurnoPasadoError) as exc:
        svc.cancel(
            tenant_id=TENANT_A, turno=turno, user=_user_recepcion(),
            motivo="x", now_utc=ahora, antelacion_hs=0, tiene_senia=False,
        )
    assert exc.value.status == 409
    assert turno.estado == "confirmado"


def test_cancel_orden_tenant_existe_permiso_antes_que_resto():
    """Orden inmutable: tenant→existe→permiso preceden a terminales/antelación/motivo."""
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    user_sin_permiso = User(id="u-x", tenant_id=TENANT_A, roles=("paciente",))

    # Cross-tenant se trata como inexistente (404 indistinguible), aun con motivo inválido.
    turno_otro = _turno_confirmado(inicio=ahora + timedelta(minutes=10))
    turno_otro.tenant_id = "tenant-otro"
    with pytest.raises(TurnoNotFoundError):
        svc.cancel(
            tenant_id=TENANT_A, turno=turno_otro, user=_user_recepcion(),
            motivo="", now_utc=ahora, antelacion_hs=24, tiene_senia=False,
        )

    # Turno inexistente → 404 aunque todo lo demás fallaría.
    with pytest.raises(TurnoNotFoundError):
        svc.cancel(
            tenant_id=TENANT_A, turno=None, user=_user_recepcion(),
            motivo="", now_utc=ahora, antelacion_hs=24, tiene_senia=False,
        )

    # Sin permiso → 403 aunque el turno esté fuera de término y sin motivo.
    turno = _turno_confirmado(inicio=ahora + timedelta(minutes=10))
    with pytest.raises(ForbiddenError):
        svc.cancel(
            tenant_id=TENANT_A, turno=turno, user=user_sin_permiso,
            motivo="", now_utc=ahora, antelacion_hs=24, tiene_senia=False,
        )


# --- 1.7: motivo obligatorio como ÚLTIMA validación ---------------------------

def test_cancel_motivo_faltante_422_sin_mutar():
    """GIVEN turno que pasó tenant/existe/permiso/terminales/antelación
    WHEN falta motivo THEN 422 es-AR sin mutar."""
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    turno = _turno_confirmado(inicio=ahora + timedelta(hours=48))
    with pytest.raises(MotivoInvalidoError) as exc:
        svc.cancel(
            tenant_id=TENANT_A, turno=turno, user=_user_recepcion(),
            motivo=None, now_utc=ahora, antelacion_hs=24, tiene_senia=False,
        )
    assert exc.value.status == 422
    assert turno.estado == "confirmado"


def test_cancel_motivo_vacio_o_whitespace_422():
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    for i, motivo in enumerate(("", "   ", "z" * 501)):
        turno = _turno_confirmado(inicio=ahora + timedelta(hours=48))
        turno.id = f"t-motivo-{i}"
        with pytest.raises(MotivoInvalidoError):
            svc.cancel(
                tenant_id=TENANT_A, turno=turno, user=_user_recepcion(),
                motivo=motivo, now_utc=ahora, antelacion_hs=24, tiene_senia=False,
            )
        assert turno.estado == "confirmado"


def test_cancel_fuera_de_termino_precede_a_motivo():
    """GIVEN sin motivo + fuera de término THEN 409 RN-AG-01 (no 422)."""
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    turno = _turno_confirmado(inicio=ahora + timedelta(hours=2))
    with pytest.raises(FueraDeTerminoError) as exc:
        svc.cancel(
            tenant_id=TENANT_A, turno=turno, user=_user_recepcion(),
            motivo=None, now_utc=ahora, antelacion_hs=24, tiene_senia=False,
        )
    assert exc.value.code == "RN-AG-01"


# --- 1.9: seña intacta (desviación temporal RN-CO-03, Owner C-12) --------------

def test_cancel_con_senia_acreditada_no_la_mueve_y_marca_flag():
    """GIVEN turno con seña acreditada WHEN se cancela
    THEN la seña sigue acreditada (no-touch) y flag=True."""
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    turno = _turno_confirmado(inicio=ahora + timedelta(hours=48))
    senia_estado = {"estado": "acreditada"}  # la seña vive fuera del turno; no se toca

    resultado = svc.cancel(
        tenant_id=TENANT_A, turno=turno, user=_user_recepcion(),
        motivo="x", now_utc=ahora, antelacion_hs=24, tiene_senia=True,
    )
    assert resultado.estado == "cancelado"
    assert resultado.senia_pendiente_definicion is True
    assert senia_estado["estado"] == "acreditada"


def test_cancel_sin_senia_no_marca_flag():
    """GIVEN turno sin seña WHEN se cancela THEN flag=False y nada cambia."""
    svc = AgendaCancelService()
    ahora = _ahora_utc()
    turno = _turno_confirmado(inicio=ahora + timedelta(hours=48))

    resultado = svc.cancel(
        tenant_id=TENANT_A, turno=turno, user=_user_recepcion(),
        motivo="x", now_utc=ahora, antelacion_hs=24, tiene_senia=False,
    )
    assert resultado.estado == "cancelado"
    assert resultado.senia_pendiente_definicion is False


# --- 1.11: concurrencia -------------------------------------------------------

def test_cancel_concurrente_uno_transiciona_otro_idempotente():
    """GIVEN turno activo WHEN dos cancel() concurrentes
    THEN uno transiciona y otro cae en idempotencia sin duplicar auditoría."""
    import threading

    svc = AgendaCancelService()
    ahora = _ahora_utc()
    turno = _turno_confirmado(inicio=ahora + timedelta(hours=48))
    barrera = threading.Barrier(2)
    resultados: list = []

    def _cancelar(motivo: str):
        barrera.wait()  # máxima simultaneidad
        r = svc.cancel(
            tenant_id=TENANT_A, turno=turno, user=_user_recepcion(),
            motivo=motivo, now_utc=ahora, antelacion_hs=24, tiene_senia=False,
        )
        resultados.append((motivo, r.estado, r.cancelled_at, r.motivo))

    hilos = [
        threading.Thread(target=_cancelar, args=("hilo-A",)),
        threading.Thread(target=_cancelar, args=("hilo-B",)),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=10)

    assert len(resultados) == 2
    assert all(estado == "cancelado" for _, estado, _, _ in resultados)
    # Una sola auditoría: mismo cancelled_at y motivo ganador único.
    assert resultados[0][2] == resultados[1][2]
    assert resultados[0][3] == resultados[1][3]
    assert turno.motivo in ("hilo-A", "hilo-B")

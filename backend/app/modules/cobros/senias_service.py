"""Servicio de señas de Mercado Pago (C-12).

Reglas que aplica:
- R1: toda query lleva `tenant_id`; ningún dato cruzado entre tenants.
- R5/R7: montos en centavos enteros y fechas UTC aware.
- R8: idempotencia por `mp_payment_id` (unique). Un webhook repetido es no-op.
- RN-CO-03: política de devolución `no_devuelve|devuelve_50|devuelve_100`
  (default `devuelve_100` = saldo a favor completo).
- RN-GL-03: si MP falla, el flujo local se completa; la seña queda `pendiente`.

El saldo derivado del paciente resta las señas en `acreditada` y `aplicada`
(monto completo) y las `devuelta` únicamente por `monto_afavor_cents`
(crédito parcial que produce `devuelve_50`).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.modules.agenda.models import ConfigModel, PrestacionModel
from app.modules.cobros.models import ESTADOS_SENIA, SeniaModel

POLITICAS_DEVOLUCION = ("no_devuelve", "devuelve_50", "devuelve_100")

logger = logging.getLogger(__name__)

#: Client MP por defecto (inyectado vía `set_default_mp_client` en tests;
#: production lo construye perezosamente con el access token del settings).
_default_mp_client = None
_default_mp_client_built = False


def set_default_mp_client(client) -> None:
    global _default_mp_client, _default_mp_client_built
    _default_mp_client = client
    _default_mp_client_built = True


def _get_or_build_default_mp_client():
    global _default_mp_client
    if _default_mp_client:
        return _default_mp_client
    try:
        from app.core.config import get_settings

        from app.modules.cobros.mp_client import MercadoPagoClient

        settings = get_settings()
        token = settings.mp_access_token
        token_val = token.get_secret_value() if token else None
        _default_mp_client = MercadoPagoClient(access_token=token_val)
        return _default_mp_client
    except Exception as exc:  # noqa: BLE001 — dev/test sin settings
        logger.debug("client MP no disponible: %s", exc)
        return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SeniaError(RuntimeError):
    def __init__(self, code: str, message: str, *, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class SeniaService:
    def __init__(self, session, mp_client=None) -> None:
        self.session = session
        self.mp = mp_client if mp_client is not None else _get_or_build_default_mp_client()

    # ---------- Requerimiento de seña ----------

    def senia_requerida_para(self, tenant_id: str, prestacion) -> bool:
        """Prestación con override propio; `None` = config global del tenant."""
        config = self.session.get(ConfigModel, tenant_id)
        if prestacion.senia_requerida is not None:
            return bool(prestacion.senia_requerida)
        return bool(config and config.senia_requerida)

    # ---------- Creación (reserva pública) ----------

    def crear_para_booking(
        self,
        *,
        tenant_id: str,
        turno,
        prestacion,
        paciente_id: str,
        ahora: datetime,
    ) -> tuple[SeniaModel | None, str | None]:
        """Crea la seña + preferencia MP si la prestación la requiere.

        Devuelve `(senia, checkout_url)`; `(None, None)` si la prestación no
        requiere seña. Si MP falla (RN-GL-03) la seña queda `pendiente` y el
        checkout vacío: ninguna caída bloquea el flujo local.
        """
        if not self.senia_requerida_para(tenant_id, prestacion):
            return None, None
        monto = prestacion.senia_monto_cents or 0
        if monto <= 0:
            # Config global sin monto por prestación: se conserva el contrato
            # de C-08 (reserva pendiente sin seña) y se deja el warning.
            logger.warning(
                "seña requerida para prestación %s sin monto configurado",
                getattr(prestacion, "id", "?"),
            )
            return None, None
        # Una reprogramación que arrastra la seña no crea otra nueva.
        if turno.senia_id is not None:
            existente = self.get(tenant_id, turno.senia_id)
            return existente, None
        senia = SeniaModel(
            tenant_id=tenant_id,
            turno_id=turno.id,
            paciente_id=paciente_id,
            monto_cents=monto,
            estado="pendiente",
            mp_preference_id="",
        )
        self.session.add(senia)
        self.session.flush()
        preferencia = self._crear_preferencia_mp(senia)
        senia.mp_preference_id = preferencia.get("id") or f"local-{senia.id}"
        self.session.flush()
        turno.senia_id = senia.id
        return senia, preferencia.get("init_point") or None

    def _crear_preferencia_mp(self, senia: SeniaModel) -> dict:
        if self.mp is None:
            # Sin client configurado (dev/test): preferencia local segura.
            return {"id": f"local-{senia.id}", "init_point": ""}
        payload = self._payload_preferencia(senia)
        try:
            return self.mp.crear_preferencia(payload=payload)
        except Exception as exc:  # noqa: BLE001 — RN-GL-03
            logger.warning(
                "preferencia MP no creada para seña %s: %s", senia.id, exc
            )
            return {"id": f"local-{senia.id}", "init_point": ""}

    @staticmethod
    def _payload_preferencia(senia: SeniaModel) -> dict:
        payload: dict = {
            "external_reference": senia.id,
            "items": [
                {
                    "title": "Seña de turno",
                    "quantity": 1,
                    "unit_price": round(senia.monto_cents / 100.0, 2),
                    "currency_id": "ARS",
                }
            ],
        }
        webhook_url = SeniaService._webhook_url()
        if webhook_url:
            payload["notification_url"] = webhook_url
        return payload

    @staticmethod
    def _webhook_url() -> str | None:
        try:
            from app.core.config import get_settings

            base = get_settings().public_base_url
        except Exception as exc:  # noqa: BLE001 — fallback dev/test
            logger.debug("public_base_url no disponible: %s", exc)
            return None
        if not base:
            return None
        return f"{base.rstrip('/')}/webhooks/mercadopago"

    # ---------- Lectura / helpers ----------

    def get(self, tenant_id: str, senia_id: str) -> SeniaModel | None:
        return self.session.execute(
            select(SeniaModel).where(
                SeniaModel.tenant_id == tenant_id,
                SeniaModel.id == senia_id,
                SeniaModel.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def get_by_turno(self, tenant_id: str, turno_id: str) -> SeniaModel | None:
        return self.session.execute(
            select(SeniaModel).where(
                SeniaModel.tenant_id == tenant_id,
                SeniaModel.turno_id == turno_id,
                SeniaModel.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def get_by_preference(
        self, tenant_id: str, preference_id: str
    ) -> SeniaModel | None:
        return self.session.execute(
            select(SeniaModel).where(
                SeniaModel.tenant_id == tenant_id,
                SeniaModel.mp_preference_id == preference_id,
                SeniaModel.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def listar_por_turno_ids(
        self, tenant_id: str, turno_ids: list[str]
    ) -> dict[str, SeniaModel]:
        if not turno_ids:
            return {}
        senias = (
            self.session.execute(
                select(SeniaModel).where(
                    SeniaModel.tenant_id == tenant_id,
                    SeniaModel.turno_id.in_(turno_ids),
                    SeniaModel.deleted_at.is_(None),
                )
            )
            .scalars()
            .all()
        )
        return {s.turno_id: s for s in senias}

    def get_global(self, senia_id: str) -> SeniaModel | None:
        """Búsqueda sin tenant, solo para el webhook (fuente confiable: MP).

        El tenant del registro se usa después para todas las mutaciones.
        """
        return self.session.execute(
            select(SeniaModel).where(
                SeniaModel.id == senia_id,
                SeniaModel.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    # ---------- Acreditación desde el webhook ----------

    def acreditar_desde_webhook(
        self, *, payment_id: str, ahora: datetime | None = None
    ) -> bool:
        """Webhook-first: resuelve el pago vía API MP y acredita la seña.

        Devuelve True si se procesó una acreditación efectiva; False si el
        pago no está aprobado, ya estaba registrado (idempotencia R8) o no
        referencia ninguna seña conocida (en todos los casos responde 200).
        """
        if self.mp is None:
            logger.warning("webhook MP sin client configurado; no-op")
            return False
        try:
            pago = self.mp.obtener_pago(payment_id=payment_id)
        except Exception as exc:  # noqa: BLE001 — RN-GL-03
            logger.warning("no se pudo obtener el pago %s: %s", payment_id, exc)
            return False
        status = str(pago.get("status", ""))
        external_reference = pago.get("external_reference") or None
        senia = None
        if external_reference:
            senia = self.get_global(str(external_reference))

        if senia is None:
            # Fallback por preferencia embebida en algunos payloads.
            pref = (pago.get("additional_info") or {}).get("external_reference")
            if pref:
                senia = self.get_global(str(pref))
        if senia is None:
            # ¿Ya acreditada con este pago? Idempotencia pura.
            ya = self.session.execute(
                select(SeniaModel).where(SeniaModel.mp_payment_id == str(payment_id))
            ).scalar_one_or_none()
            if ya is not None:
                return False
            logger.warning("pago %s no referencia ninguna seña", payment_id)
            return False
        if status != "approved":
            logger.info("pago %s estado %s: no acredita", payment_id, status)
            return False
        # Idempotencia (R8): repetido es no-op.
        if senia.estado in ("acreditada", "aplicada"):
            return False
        self.acreditar(
            tenant_id=senia.tenant_id,
            senia=senia,
            mp_payment_id=str(payment_id),
            ahora=ahora,
        )
        return True

    # ---------- Acreditación (webhook, R8) ----------

    def acreditar(
        self,
        *,
        tenant_id: str,
        senia: SeniaModel,
        mp_payment_id: str,
        ahora: datetime | None = None,
    ) -> SeniaModel:
        """Acredita la seña y confirma el turno (si la seña era requerida).

        Idempotente (R8): un webhook repetido con el mismo pago es no-op.
        """
        if senia.estado in ("acreditada", "aplicada"):
            return senia
        ahora = ahora or _utc_now()
        senia.estado = "acreditada"
        senia.mp_payment_id = mp_payment_id
        senia.acreditada_at = ahora
        senia.monto_afavor_cents = None
        from app.modules.agenda.models import TurnoModel

        turno = self.session.get(TurnoModel, senia.turno_id)
        if turno is not None and turno.tenant_id == tenant_id:
            # Invariante: el turno referencia su seña (arrastre/saldo).
            if turno.senia_id is None:
                turno.senia_id = senia.id
            if turno.estado == "pendiente_confirmacion":
                turno.estado = "confirmado"
            # La acreditación del pago vale como acuse del paciente (C-09).
            if turno.confirmado_paciente_at is None:
                turno.confirmado_paciente_at = ahora
        self.session.flush()
        return senia

    def _sena_de_turno(self, turno) -> SeniaModel | None:
        """Resuelve la seña del turno: preferente por id, fallback por turno."""
        if turno.senia_id:
            senia = self.get(turno.tenant_id, turno.senia_id)
            if senia is not None:
                return senia
        return self.get_by_turno(turno.tenant_id, turno.id)

    # ---------- Arrastre (reprogramación, RN-AG-05) ----------

    def arrastrar(self, *, turno_viejo, turno_nuevo, prestacion_nueva) -> None:
        """Mueve la seña del turno viejo al nuevo.

        - `acreditada` + nuevo turno requiere seña → se reasigna (no se cobra
          dos veces).
        - `acreditada` + nuevo turno sin seña requerida → `aplicada` (saldo a
          favor del paciente).
        - `pendiente` (nunca pagó) → `devuelta` sin crédito; el nuevo turno se
          libera.
        """
        senia = self._sena_de_turno(turno_viejo)
        if senia is None:
            # Sin fila de seña resoluble (p. ej. puntero sintético de C-07):
            # no se toca nada.
            return
        requiere_en_nuevo = (
            prestacion_nueva is not None
            and self.senia_requerida_para(turno_nuevo.tenant_id, prestacion_nueva)
        )
        if senia.estado == "acreditada":
            if requiere_en_nuevo:
                senia.turno_id = turno_nuevo.id
                turno_nuevo.senia_id = senia.id
            else:
                senia.estado = "aplicada"
        else:
            senia.estado = "devuelta"
            senia.monto_afavor_cents = 0
        turno_viejo.senia_id = None
        turno_viejo.senia_pendiente_definicion = False
        self.session.flush()

    # ---------- Devolución (cancelación, RN-CO-03) ----------

    def aplicar_politica_cancelacion(self, turno) -> SeniaModel | None:
        """Aplica `politica_devolucion_senia` al cancelar un turno con seña.

        - `devuelve_100` (default) → `aplicada`: saldo a favor completo.
        - `devuelve_50` → `devuelta` con `monto_afavor_cents = monto // 2`.
        - `no_devuelve` → `devuelta` sin crédito.
        Una seña `pendiente` (nunca acreditada) pasa a `devuelta` sin crédito.
        """
        senia = self._sena_de_turno(turno)
        if senia is None or senia.estado in ("aplicada", "devuelta"):
            return senia
        config = self.session.get(ConfigModel, turno.tenant_id)
        politica = (
            (config.politica_devolucion_senia if config else None)
            or "devuelve_100"
        )
        if senia.estado == "acreditada":
            if politica == "no_devuelve":
                senia.estado = "devuelta"
                senia.monto_afavor_cents = 0
            elif politica == "devuelve_50":
                senia.estado = "devuelta"
                senia.monto_afavor_cents = senia.monto_cents // 2
            else:
                senia.estado = "aplicada"
        else:
            senia.estado = "devuelta"
            senia.monto_afavor_cents = 0
        self.session.flush()
        return senia

    # ---------- Timeout (C-08: libera la reserva sin pago) ----------

    def marcar_timeout(self, turno) -> SeniaModel | None:
        senia = self._sena_de_turno(turno)
        if senia is None:
            return None
        if senia.estado == "pendiente":
            senia.estado = "devuelta"
            senia.monto_afavor_cents = 0
            self.session.flush()
        return senia

    @staticmethod
    def total_afavor_sena(senia: SeniaModel) -> int:
        """Crédito que la seña aporta al saldo derivado, por estado."""
        if senia.estado in ("acreditada", "aplicada"):
            return senia.monto_afavor_cents or senia.monto_cents
        if senia.estado == "devuelta":
            return senia.monto_afavor_cents or 0
        return 0

    # ---------- Saldo derivado (extensión C-11) ----------

    def total_afavor_paciente(self, tenant_id: str, paciente_id: str) -> int:
        value = self.session.execute(
            select(
                func.coalesce(
                    func.sum(
                        func.coalesce(
                            SeniaModel.monto_afavor_cents, SeniaModel.monto_cents
                        )
                    ),
                    0,
                )
            ).where(
                SeniaModel.tenant_id == tenant_id,
                SeniaModel.paciente_id == paciente_id,
                SeniaModel.deleted_at.is_(None),
                SeniaModel.estado.in_(("acreditada", "aplicada")),
            )
        ).scalar_one()
        value_devuelta = self.session.execute(
            select(func.coalesce(func.sum(SeniaModel.monto_afavor_cents), 0)).where(
                SeniaModel.tenant_id == tenant_id,
                SeniaModel.paciente_id == paciente_id,
                SeniaModel.deleted_at.is_(None),
                SeniaModel.estado == "devuelta",
            )
        ).scalar_one()
        return int(value or 0) + int(value_devuelta or 0)


__all__ = ["ESTADOS_SENIA", "POLITICAS_DEVOLUCION", "SeniaError", "SeniaService"]

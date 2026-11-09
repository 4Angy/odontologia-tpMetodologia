"""Adapter de Mercado Pago (C-12, D1): Protocol + implementación real y fake.

Patrón idéntico a `notificaciones/whatsapp.py`: `httpx` directo (sin SDK),
timeout explícito y fake inyectable para tests. El adapter no toca la DB ni
decide estados: eso es responsabilidad del servicio de señas (RN-GL-03).
"""
from __future__ import annotations

import logging
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)

MP_API_BASE = "https://api.mercadopago.com"


class MPClienteError(RuntimeError):
    """Error transitorio o permanente llamando a la API de Mercado Pago."""

    def __init__(self, message: str, *, transitorio: bool = False) -> None:
        super().__init__(message)
        self.transitorio = transitorio


class MPClient(Protocol):
    def crear_preferencia(self, *, payload: dict[str, Any]) -> dict[str, Any]: ...

    def obtener_pago(self, *, payment_id: str) -> dict[str, Any]: ...

    def obtener_preferencia(self, *, preference_id: str) -> dict[str, Any]: ...

class MercadoPagoClient:
    """Adapter real contra la API de Mercado Pago."""

    def __init__(
        self,
        *,
        access_token: str | None,
        base_url: str = MP_API_BASE,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    def _cliente(self) -> httpx.Client:
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
            transport=self.transport,
        )

    def crear_preferencia(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            with self._cliente() as client:
                r = client.post("/checkout/preferences", json=payload)
        except httpx.HTTPError as exc:  # noqa: BLE001
            raise MPClienteError(f"MP no disponible: {exc}", transitorio=True) from exc
        if r.status_code >= 500:
            raise MPClienteError(
                f"MP error {r.status_code}", transitorio=True
            )
        if r.status_code >= 400:
            raise MPClienteError(f"MP rechazó la preferencia: {r.status_code}")
        return r.json()

    def obtener_pago(self, *, payment_id: str) -> dict[str, Any]:
        try:
            with self._cliente() as client:
                r = client.get(f"/v1/payments/{payment_id}")
        except httpx.HTTPError as exc:  # noqa: BLE001
            raise MPClienteError(f"MP no disponible: {exc}", transitorio=True) from exc
        if r.status_code >= 500:
            raise MPClienteError(
                f"MP error {r.status_code}", transitorio=True
            )
        if r.status_code >= 400:
            raise MPClienteError(f"MP pago no encontrado: {r.status_code}")
        return r.json()

    def obtener_preferencia(self, *, preference_id: str) -> dict[str, Any]:
        try:
            with self._cliente() as client:
                r = client.get(f"/checkout/preferences/{preference_id}")
        except httpx.HTTPError as exc:  # noqa: BLE001
            raise MPClienteError(f"MP no disponible: {exc}", transitorio=True) from exc
        if r.status_code >= 500:
            raise MPClienteError(
                f"MP error {r.status_code}", transitorio=True
            )
        if r.status_code >= 400:
            raise MPClienteError(f"MP preferencia no encontrada: {r.status_code}")
        return r.json()


class FakeMPClient:
    """Fake determinista para tests: registra llamadas y devuelve respuestas."""

    def __init__(
        self,
        *,
        preferencias: dict[str, dict[str, Any]] | None = None,
        pagos: dict[str, dict[str, Any]] | None = None,
        error: MPClienteError | None = None,
    ) -> None:
        self.preferencias = preferencias or {}
        self.pagos = pagos or {}
        self.error = error
        self.llamadas_preferencia: list[dict[str, Any]] = []
        self.llamadas_preferencia_get: list[str] = []
        self.init_point_por_preferencia: dict[str, str] = {}
        self.llamadas_pago: list[str] = []

    def crear_preferencia(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        self.llamadas_preferencia.append(payload)
        if self.error is not None:
            raise self.error
        external_reference = payload.get("external_reference", "")
        pref = self.preferencias.get(external_reference)
        if pref is not None:
            return pref
        return {
            "id": f"pref-{external_reference}",
            "init_point": f"https://sandbox.mercadopago.com/checkout/v1/redirect?pref-id=pref-{external_reference}",
        }

    def obtener_preferencia(self, *, preference_id: str) -> dict[str, Any]:
        self.llamadas_preferencia_get.append(preference_id)
        if self.error is not None:
            raise self.error
        return {"id": preference_id, "init_point": self.init_point_por_preferencia.get(preference_id, "")}

    def obtener_pago(self, *, payment_id: str) -> dict[str, Any]:
        self.llamadas_pago.append(payment_id)
        if self.error is not None:
            raise self.error
        pago = self.pagos.get(payment_id)
        if pago is None:
            return {"id": int(payment_id), "status": "approved"}
        return pago


__all__ = [
    "FakeMPClient",
    "MP_API_BASE",
    "MPClient",
    "MPClienteError",
    "MercadoPagoClient",
]

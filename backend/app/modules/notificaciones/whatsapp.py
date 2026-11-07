"""Adapter de WhatsApp (D5): Protocol + implementaciones real y fake."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, Protocol

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EnvioResultado:
    ok: bool
    provider_msg_id: Optional[str] = None
    error_code: Optional[str] = None
    transitorio: bool = False


class WhatsAppClient(Protocol):
    def enviar(
        self,
        *,
        telefono: str,
        cuerpo: str,
        idempotency_key: str,
    ) -> EnvioResultado: ...


class CloudApiClient:
    """Adapter real contra la Cloud API de Meta. Timeout explícito, sin logs del token."""

    def __init__(
        self,
        *,
        api_token: str | None,
        phone_id: str | None,
        base_url: str = "https://graph.facebook.com/v19.0",
        timeout: float = 10.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.api_token = api_token
        self.phone_id = phone_id
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    def enviar(self, *, telefono, cuerpo, idempotency_key) -> EnvioResultado:
        if not self.api_token or not self.phone_id:
            return EnvioResultado(
                ok=False, error_code="RN-GL-03", transitorio=True
            )
        url = f"{self.base_url}/{self.phone_id}/messages"
        headers = {"Authorization": f"Bearer {self.api_token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": telefono,
            "type": "text",
            "text": {"body": cuerpo},
        }
        try:
            with httpx.Client(
                timeout=self.timeout, transport=self.transport
            ) as client:
                respuesta = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:  # noqa: BLE001
            logger.warning("whatsapp http error: %s", type(exc).__name__)
            return EnvioResultado(ok=False, error_code="RN-GL-03", transitorio=True)
        if respuesta.status_code == 200:
            data = respuesta.json() if respuesta.content else {}
            msg_id = None
            try:
                msg_id = data["messages"][0]["id"]
            except (KeyError, IndexError, TypeError):
                msg_id = f"wamid-{idempotency_key[:12]}"
            return EnvioResultado(ok=True, provider_msg_id=msg_id)
        if respuesta.status_code == 429 or respuesta.status_code >= 500:
            return EnvioResultado(
                ok=False, error_code="RN-GL-03", transitorio=True
            )
        return EnvioResultado(ok=False, error_code="RN-PA-04", transitorio=False)


class FakeClient:
    """Client de tests y desarrollo. Registra llamadas y devuelve resultado configurable."""

    def __init__(self, *, ok: bool = True, provider_msg_id: str = "fake-msg-1", error_code: str | None = None, transitorio: bool = False) -> None:
        self.ok = ok
        self.provider_msg_id = provider_msg_id
        self.error_code = error_code
        self.transitorio = transitorio
        self.llamadas: list[dict] = []

    def enviar(self, *, telefono, cuerpo, idempotency_key) -> EnvioResultado:
        self.llamadas.append(
            {"telefono": telefono, "cuerpo": cuerpo, "idempotency_key": idempotency_key}
        )
        if self.ok:
            return EnvioResultado(ok=True, provider_msg_id=self.provider_msg_id)
        return EnvioResultado(
            ok=False,
            error_code=self.error_code or "RN-GL-03",
            transitorio=self.transitorio,
        )


__all__ = ["CloudApiClient", "EnvioResultado", "FakeClient", "WhatsAppClient"]

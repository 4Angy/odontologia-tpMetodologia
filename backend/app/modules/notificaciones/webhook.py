"""Webhook del proveedor de WhatsApp (D11, R8)."""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.notificaciones.models import NotificacionEnvioModel
from app.modules.notificaciones.repository import NotificacionEnvioRepository

RANKING = {"encolada": 0, "enviada": 1, "fallida": 1, "entregada": 2}


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def verify_signature(raw_body: bytes, header: str | None, app_secret: str | None) -> bool:
    if not app_secret or not header:
        return False
    if not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    received = header[len("sha256="):]
    return hmac.compare_digest(expected, received)


def verify_token(token: str | None, expected: str | None) -> bool:
    if not expected or not token:
        return False
    return hmac.compare_digest(token, expected)


def parse_events(payload: Any) -> list[tuple[str, str]]:
    """Devuelve lista de (provider_msg_id, status_normalizado)."""
    eventos: list[tuple[str, str]] = []
    # Formato simplificado para tests: {"provider_msg_id": "...", "status": "..."}
    if isinstance(payload, dict) and "provider_msg_id" in payload and "status" in payload:
        eventos.append((str(payload["provider_msg_id"]), _normalizar(payload["status"])))
        return eventos
    if not isinstance(payload, dict):
        return eventos
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {}) or {}
            for status in value.get("statuses", []) or []:
                msg_id = status.get("id") or status.get("provider_msg_id")
                if not msg_id:
                    continue
                eventos.append((str(msg_id), _normalizar(status.get("status"))))
    return eventos


def _normalizar(status: Any) -> str:
    s = str(status or "").lower()
    if s in ("sent", "accepted"):
        return "enviada"
    if s in ("delivered", "read"):
        return "entregada"
    if s in ("failed", "error"):
        return "fallida"
    return s


class WebhookService:
    def __init__(self, session: Session, now: datetime) -> None:
        self.session = session
        self.now = _utc(now)
        self.repo = NotificacionEnvioRepository(session)

    def procesar(self, payload: Any) -> int:
        actualizados = 0
        for provider_msg_id, status in parse_events(payload):
            envios = self.repo.buscar_por_provider_msg_id(provider_msg_id)
            for envio in envios:
                if self._aplicar(envio, status):
                    actualizados += 1
        self.session.flush()
        return actualizados

    def _aplicar(self, envio: NotificacionEnvioModel, nuevo: str) -> bool:
        actual = envio.estado
        # entregada es terminal: nunca retrocede
        if actual == "entregada":
            return False
        if nuevo == "entregada":
            envio.estado = "entregada"
            envio.entregado_at = self.now
            return True
        if nuevo == "enviada":
            if actual in ("encolada", "fallida"):
                envio.estado = "enviada"
                if envio.enviado_at is None:
                    envio.enviado_at = self.now
                return True
            return False
        if nuevo == "fallida":
            if actual != "entregada":
                envio.estado = "fallida"
                return True
            return False
        return False


__all__ = ["WebhookService", "parse_events", "verify_signature", "verify_token"]

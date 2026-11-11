"""Webhook de Mercado Pago (C-12, D3): POST /webhooks/mercadopago.

- Formatos aceptados: `{type: "payment", data: {id}}`, `{topic: "payment",
  resource: "..."}` y query params `?id=&topic=` (tolerante a MP).
- Firma HMAC SHA256 con `MP_WEBHOOK_SECRET` (R8): MP firma
  `id:<data.id>;request-id:<x-request-id>;ts:<ts>;` y la envía en el header
  `X-Signature: ts=<ts>,v1=<hex>`. Comparación en tiempo constante.
  Sin secreto configurado (dev/test) se acepta la llamada para poder probar
  el flujo con fakes.
- Idempotencia (R8): `mp_payment_id` unique; webhook repetido → 200 no-op.
- Resolución del pago: siempre vía `obtener_pago` de la API (webhook-first,
  no se confía en los datos del cuerpo).
- Pago no apto o seña no encontrada: se responde 200 para que MP no reintente
  eternamente (RN-GL-03); la caída de MP no bloquea el flujo local.

Este endpoint NO requiere JWT: la identidad proviene de la firma de MP y el
tenant se deriva del registro (la única fuente confiable disponible).
"""
from __future__ import annotations

import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app import deps
from app.modules.cobros.senias_service import SeniaService

router = APIRouter(tags=["webhooks"])


def webhook_secret() -> str | None:
    try:
        from app.core.config import get_settings

        secret = get_settings().mp_webhook_secret
    except Exception:  # noqa: BLE001 — dev/test sin settings completas
        return None
    return secret.get_secret_value() if secret else None


def parse_signature_header(header: str | None) -> tuple[str | None, str | None]:
    """Extrae `(v1, ts)` de un header `X-Signature: ts=...,v1=...` de MP."""
    if not header:
        return None, None
    v1: str | None = None
    ts: str | None = None
    for parte in header.split(","):
        if "=" not in parte:
            continue
        clave, valor = parte.strip().split("=", 1)
        if clave == "v1":
            v1 = valor
        elif clave == "ts":
            ts = valor
    return v1, ts


def build_manifest(data_id: str, request_id: str | None, ts: str | None) -> str:
    return f"id:{data_id};request-id:{request_id or ''};ts:{ts or ''};"


def verify_signature(
    *, data_id: str, request_id: str | None, ts: str | None, received_v1: str | None,
    secret: str | None,
) -> bool:
    """Valida la firma en tiempo constante (R8). Sin secreto → True (dev/test)."""
    if not secret:
        return True
    if not received_v1:
        return False
    manifest = build_manifest(data_id, request_id, ts)
    expected = hmac.new(
        secret.encode(), manifest.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, received_v1)


def extract_payment_id(payload: dict, query_id: str | None = None) -> str | None:
    """Extrae `payment_id` desde `data.id`, `resource` o query param `id`."""
    if not isinstance(payload, dict):
        payload = {}
    data = payload.get("data")
    if isinstance(data, dict) and data.get("id") is not None:
        return str(data["id"])
    resource = payload.get("resource")
    if isinstance(resource, str) and resource.strip():
        ultimo = [seg for seg in resource.split("/") if seg.strip()]
        if ultimo and ultimo[-1].isdigit():
            return ultimo[-1]
    if query_id and str(query_id).strip():
        return str(query_id).strip()
    return None


@router.post("/webhooks/mercadopago")
async def mercadopago_webhook(
    request: Request,
    data_id: str | None = Query(default=None, alias="data.id"),
    id_: str | None = Query(default=None, alias="id"),
    topic: str | None = Query(default=None, alias="topic"),
    session: Session = Depends(deps.get_session),
):
    cuerpo = await request.body()
    try:
        payload = json.loads(cuerpo.decode("utf-8")) if cuerpo else {}
    except (ValueError, UnicodeDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    # Los params de query llenan formatos que MP manda solo por URL.
    if not isinstance(payload.get("data"), dict) and data_id:
        payload.setdefault("type", topic or payload.get("topic") or "payment")
        payload.setdefault("data", {"id": data_id})
    if not payload.get("data") and id_ and topic == "payment":
        payload.setdefault("resource", f"/v1/payments/{id_}")

    payment_id = extract_payment_id(payload, query_id=id_)
    if not payment_id:
        # Evento que no refiere a un pago: 200 para no generar reintentos.
        return {"received": True}

    secret = webhook_secret()
    v1, ts = parse_signature_header(request.headers.get("X-Signature"))
    if not verify_signature(
        data_id=payment_id,
        request_id=request.headers.get("X-Request-Id"),
        ts=ts,
        received_v1=v1,
        secret=secret,
    ):
        raise HTTPException(
            status_code=401,
            detail={"code": "RN-CO-06", "message": "Firma del webhook inválida."},
        )

    service = SeniaService(session)
    acredito = service.acreditar_desde_webhook(payment_id=payment_id)
    session.commit()
    return {"received": True, "processed": bool(acredito)}


__all__ = [
    "build_manifest",
    "extract_payment_id",
    "parse_signature_header",
    "router",
    "verify_signature",
    "webhook_secret",
]

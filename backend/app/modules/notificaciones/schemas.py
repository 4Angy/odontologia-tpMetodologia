"""DTOs Pydantic v2 del motor de notificaciones (R3, R4)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.modules.agenda.schemas import Strict


class NotificacionEnvioResponse(Strict):
    id: str
    tenant_id: str
    paciente_id: str
    turno_id: Optional[str] = None
    canal: str
    plantilla_codigo: str
    ventana: Optional[str] = None
    estado: str
    motivo_code: Optional[str] = None
    intentos: int
    next_attempt_at: datetime
    provider_msg_id: Optional[str] = None
    costo_estimado_centavos: int
    ultimo_error_code: Optional[str] = None
    enviado_at: Optional[datetime] = None
    entregado_at: Optional[datetime] = None
    confirmado_paciente_at: Optional[datetime] = None


class ConsumoItem(Strict):
    canal: str
    estado: str
    cantidad: int
    costo_centavos: int


class ConsumoResponse(Strict):
    desde: datetime
    hasta: datetime
    items: list[ConsumoItem]


class ReintentarResponse(Strict):
    id: str
    estado: str


class NotificacionTestRequest(Strict):
    paciente_id: str = Field(min_length=1, max_length=64)
    canal: Optional[str] = Field(default=None)


class NotificacionTestResponse(Strict):
    id: str
    estado: str
    canal: str


class WebhookChallengeQuery(Strict):
    pass


class WebhookStatusEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    provider_msg_id: str
    status: str


__all__ = [
    "ConsumoItem",
    "ConsumoResponse",
    "NotificacionEnvioResponse",
    "NotificacionTestRequest",
    "NotificacionTestResponse",
    "ReintentarResponse",
]

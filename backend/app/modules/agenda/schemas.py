"""DTOs Pydantic v2: NUNCA exponer modelos SQLAlchemy (R3); extra='forbid' (R4)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CancelarTurnoRequest(Strict):
    motivo: str = Field(min_length=1, max_length=500)


class ErrorAction(Strict):
    type: str
    hint: str


class ErrorBody(Strict):
    code: str
    message: str
    action: Optional[ErrorAction] = None


class TurnoResponse(Strict):
    id: str
    estado: str
    cancelled_by: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    motivo: Optional[str] = None
    senia_pendiente_definicion: bool = False


class ConfigResponse(Strict):
    antelacion_cancel_hs: int


class ConfigUpdateRequest(Strict):
    antelacion_cancel_hs: int = Field(ge=0)

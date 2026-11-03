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


class ProfesionalCreate(Strict):
    nombre: str = Field(min_length=1, max_length=200)
    usuario_id: str | None = None
    color_agenda: str | None = None
    activo: bool = True


class ProfesionalResponse(ProfesionalCreate):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime


class PrestacionCreate(Strict):
    nombre: str = Field(min_length=1, max_length=120)
    duracion_min: int = Field(ge=5, le=240)
    precio_ref: int | None = Field(default=None, ge=0)
    activa: bool = True


class PrestacionResponse(PrestacionCreate):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime


class BloqueoCreate(Strict):
    profesional_id: str = Field(min_length=1)
    inicio: datetime
    fin: datetime
    motivo: str | None = Field(default=None, max_length=500)


class BloqueoResponse(Strict):
    id: str
    tenant_id: str
    profesional_id: str
    inicio: datetime
    fin: datetime
    motivo: str | None = None
    created_at: datetime
    updated_at: datetime


class ConfigResponse(Strict):
    antelacion_cancel_hs: int
    antelacion_reserva_hs: int = 2
    recordatorio_t_48h: bool = True
    recordatorio_t_24h: bool = True


class ConfigUpdateRequest(Strict):
    antelacion_cancel_hs: int = Field(ge=0)
    antelacion_reserva_hs: int = Field(default=2, ge=0)
    recordatorio_t_48h: bool | None = None
    recordatorio_t_24h: bool | None = None

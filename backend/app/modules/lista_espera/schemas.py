"""Schemas Pydantic v2 (R4: extra='forbid')."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListaEsperaCreate(_Base):
    paciente_id: str
    profesional_id: Optional[str] = None
    prestacion_id: Optional[str] = None
    prioridad: int = 0


class HuecoOferta(_Base):
    profesional_id: str
    inicio: datetime
    fin: datetime
    prestacion_id: Optional[str] = None


class OfrecerManualRequest(_Base):
    hueco: HuecoOferta


class ListaEsperaResponse(_Base):
    id: str
    tenant_id: str
    paciente_id: str
    profesional_id: Optional[str] = None
    prestacion_id: Optional[str] = None
    prioridad: int
    estado: str
    motivo_omision: Optional[str] = None
    hueco_profesional_id: Optional[str] = None
    hueco_inicio: Optional[datetime] = None
    hueco_fin: Optional[datetime] = None
    hueco_prestacion_id: Optional[str] = None
    ofrecido_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PublicListaEsperaResponse(_Base):
    turno_id: Optional[str] = None
    estado: str

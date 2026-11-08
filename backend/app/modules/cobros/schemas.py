from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


MedioPago = Literal["efectivo", "transferencia", "mp", "otro"]
OrdenDeudas = Literal["antiguedad", "monto"]


class CobroCreate(Strict):
    paciente_id: str = Field(min_length=1, max_length=64)
    turno_id: str | None = Field(default=None, max_length=64)
    monto_cents: int = Field(ge=0, le=2_147_483_647)
    medio: MedioPago
    concepto: str = Field(min_length=1, max_length=200)
    fecha: datetime | None = None

    @field_validator("fecha")
    @classmethod
    def fecha_aware_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("La fecha debe incluir zona horaria.")
        return value.astimezone(timezone.utc) if value is not None else None


class CobroUpdate(Strict):
    paciente_id: str | None = Field(default=None, min_length=1, max_length=64)
    turno_id: str | None = Field(default=None, max_length=64)
    monto_cents: int | None = Field(default=None, ge=0, le=2_147_483_647)
    medio: MedioPago | None = None
    concepto: str | None = Field(default=None, min_length=1, max_length=200)
    fecha: datetime | None = None

    @field_validator("fecha")
    @classmethod
    def fecha_aware_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("La fecha debe incluir zona horaria.")
        return value.astimezone(timezone.utc) if value is not None else None


class CobroResponse(Strict):
    id: str
    tenant_id: str
    paciente_id: str
    turno_id: str | None = None
    monto_cents: int
    medio: str
    concepto: str
    usuario_id: str
    fecha: datetime
    created_at: datetime
    updated_at: datetime


class CierreCajaCreate(Strict):
    fecha: datetime | None = None
    observaciones: str | None = Field(default=None, max_length=500)

    @field_validator("fecha")
    @classmethod
    def fecha_aware_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("La fecha debe incluir zona horaria.")
        return value.astimezone(timezone.utc) if value is not None else None


class CierreCajaResponse(Strict):
    id: str
    tenant_id: str
    fecha: datetime
    total_efectivo_cents: int
    total_transferencia_cents: int
    total_mp_cents: int
    total_otro_cents: int
    observaciones: str | None = None
    usuario_id: str
    cobros: list[CobroResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AjusteCreate(Strict):
    cierre_id: str = Field(min_length=1, max_length=64)
    nota: str = Field(min_length=1, max_length=500)
    monto_cents: int | None = Field(default=None, ge=0, le=2_147_483_647)


class DeudaResponse(Strict):
    paciente_id: str
    nombre: str
    apellido: str
    saldo_cents: int
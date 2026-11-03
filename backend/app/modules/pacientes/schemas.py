from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PacienteBase(Strict):
    nombre: str = Field(min_length=1, max_length=120)
    apellido: str = Field(min_length=1, max_length=120)
    dni: str | None = None
    telefono: str | None = None
    email: str | None = None
    fecha_nac: datetime | None = None
    notas: str | None = None


class PacienteCreate(PacienteBase):
    pass


class PacienteUpdate(PacienteBase):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    apellido: str | None = Field(default=None, min_length=1, max_length=120)


class PacienteResponse(Strict):
    id: str
    tenant_id: str
    nombre: str
    apellido: str
    dni: str | None = None
    telefono: str | None = None
    email: str | None = None
    fecha_nac: datetime | None = None
    notas: str | None = None
    saldo: int = 0
    created_at: datetime
    updated_at: datetime


class OptInUpsert(Strict):
    canal: str = Field(pattern=r"^(whatsapp|email)$")
    estado: bool = True


class OptInResponse(Strict):
    id: str
    paciente_id: str
    tenant_id: str
    canal: str
    estado: bool
    updated_at: datetime


class EvolucionCreate(Strict):
    motivo: str = Field(min_length=1, max_length=200)
    detalle: str = Field(min_length=1)
    firma_simple: bool = False


class EvolucionResponse(Strict):
    id: str
    paciente_id: str
    tenant_id: str
    motivo: str
    detalle: str
    firma_simple: bool = False
    firma_timestamp: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdjuntoCreate(Strict):
    nombre: str = Field(min_length=1, max_length=200)
    tipo: str = Field(min_length=1, max_length=100)
    tamano_bytes: int = Field(ge=0)
    url: str | None = None


class AdjuntoResponse(Strict):
    id: str
    paciente_id: str
    tenant_id: str
    nombre: str
    tipo: str
    tamano_bytes: int
    url: str | None = None
    created_at: datetime
    updated_at: datetime


class PresupuestoItemCreate(Strict):
    descripcion: str = Field(min_length=1, max_length=200)
    monto_cents: int = Field(ge=0)


class PresupuestoCreate(Strict):
    items: list[PresupuestoItemCreate] = Field(min_length=1)
    notas: str | None = None


class PresupuestoItemResponse(Strict):
    id: str
    presupuesto_id: str
    descripcion: str
    monto_cents: int
    created_at: datetime
    updated_at: datetime


class PresupuestoResponse(Strict):
    id: str
    paciente_id: str
    tenant_id: str
    total_cents: int
    estado: str = "activo"
    notas: str | None = None
    items: list[PresupuestoItemResponse]
    created_at: datetime
    updated_at: datetime

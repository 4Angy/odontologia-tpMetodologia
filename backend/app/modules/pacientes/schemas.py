from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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

    @field_validator("fecha_nac")
    @classmethod
    def fecha_nacimiento_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("La fecha debe incluir zona horaria.")
        return value.astimezone(timezone.utc) if value is not None else None


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
    version_texto: str | None = Field(default=None, min_length=1, max_length=80)


class OptInResponse(Strict):
    id: str
    paciente_id: str
    tenant_id: str
    canal: str
    estado: bool
    updated_at: datetime
    consentimiento_version: str | None = None
    consentimiento_actor_id: str | None = None
    consentimiento_at: datetime | None = None


class AuditoriaResponse(Strict):
    id: str
    actor_id: str
    accion: str
    recurso: str
    recurso_id: str
    campos: list[str]
    consentimiento_version: str | None = None
    rol_activo: str | None = None
    ocurrido_at: datetime


class ImportacionFilaResponse(Strict):
    fila: int = Field(ge=2)
    estado: str = Field(pattern=r"^(importada|duplicada|fallida)$")
    paciente_id: str | None = None
    code: str | None = None
    mensaje: str | None = None


class ImportacionResponse(Strict):
    importadas: int = Field(ge=0)
    duplicadas: int = Field(ge=0)
    fallidas: int = Field(ge=0)
    resultados: list[ImportacionFilaResponse]


class EvolucionCreate(Strict):
    profesional_id: str | None = Field(default=None, min_length=1, max_length=64)
    fecha: datetime | None = None
    motivo: str = Field(min_length=1, max_length=200)
    detalle: str = Field(min_length=1)
    pieza_fdi_slot: Literal["dent", "face", "tooth", "zone"] | None = None
    pieza_fdi_numero: int | None = Field(default=None, ge=1, le=32)
    odontograma_ref: str | None = Field(default=None, max_length=64)
    firma_simple: bool = False

    @field_validator("fecha")
    @classmethod
    def fecha_aware_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("La fecha debe incluir zona horaria.")
        return value.astimezone(timezone.utc) if value is not None else None

    @model_validator(mode="after")
    def ancla_fdi_completa(self) -> "EvolucionCreate":
        if (self.pieza_fdi_slot is None) != (self.pieza_fdi_numero is None):
            raise ValueError("La pieza FDI requiere slot y número juntos.")
        return self


class EvolucionResponse(Strict):
    id: str
    paciente_id: str
    tenant_id: str
    profesional_id: str | None = None
    fecha: datetime
    motivo: str
    detalle: str
    pieza_fdi_slot: Literal["dent", "face", "tooth", "zone"] | None = None
    pieza_fdi_numero: int | None = None
    odontograma_ref: str | None = None
    firma_simple: bool = False
    firmado_at: datetime | None = None
    alcance_firma: str
    updated_at: datetime


class AdjuntoResponse(Strict):
    id: str
    paciente_id: str
    tenant_id: str
    nombre: str
    tipo: str
    tamano_bytes: int
    created_at: datetime
    updated_at: datetime


class AdjuntoDownloadResponse(Strict):
    url: str
    expires_in_seconds: int = Field(ge=1, le=900)


class PresupuestoItemCreate(Strict):
    descripcion: str = Field(min_length=1, max_length=200)
    monto_cents: int = Field(ge=0, le=2_147_483_647)


class PresupuestoCreate(Strict):
    items: list[PresupuestoItemCreate] = Field(min_length=1)
    notas: str | None = None
    estado: Literal["borrador", "aprobado", "aceptado"] = "borrador"


class PresupuestoUpdate(Strict):
    items: list[PresupuestoItemCreate] = Field(min_length=1)
    notas: str | None = None


class PresupuestoEstadoUpdate(Strict):
    estado: Literal["borrador", "aprobado", "aceptado"]


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

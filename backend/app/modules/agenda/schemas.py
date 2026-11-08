"""DTOs Pydantic v2: NUNCA exponer modelos SQLAlchemy (R3); extra='forbid' (R4)."""
from __future__ import annotations

from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class TurnoIntervaloInput(Strict):
    profesional_id: str = Field(min_length=1, max_length=64)
    prestacion_id: str | None = Field(default=None, min_length=1, max_length=64)
    inicio: datetime
    fin: datetime

    @model_validator(mode="after")
    def validar_intervalo(self) -> TurnoIntervaloInput:
        for campo, valor in (("inicio", self.inicio), ("fin", self.fin)):
            if valor.tzinfo is None or valor.utcoffset() is None:
                raise ValueError(f"{campo} debe incluir zona horaria.")
        if self.fin <= self.inicio:
            raise ValueError("El fin debe ser posterior al inicio.")
        return self


class TurnoCreateRequest(TurnoIntervaloInput):
    paciente_id: str = Field(min_length=1, max_length=64)
    sobreturno: bool = False
    sobreturno_motivo: str | None = Field(default=None, max_length=500)


class TurnoReprogramarRequest(TurnoIntervaloInput):
    pass


class TurnoAgendaResponse(Strict):
    id: str
    paciente_id: str
    profesional_id: str
    profesional_usuario_id: str | None = None
    prestacion_id: str | None = None
    inicio: datetime
    fin: datetime
    estado: str
    origen: str
    sobreturno: bool
    sobreturno_motivo: str | None = None
    sobreturno_autorizado_por: str | None = None
    senia_id: str | None = None
    cancelled_by: str | None = None
    cancelled_at: datetime | None = None
    motivo: str | None = None
    confirmado_paciente_at: datetime | None = None


class ReprogramarTurnoResponse(Strict):
    turno_anterior: TurnoAgendaResponse
    turno_nuevo: TurnoAgendaResponse


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
    duracion_min: int = Field(ge=5, le=240, strict=True)
    precio_ref: int | None = Field(default=None, ge=0, strict=True)
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


class HorarioSemanalInput(Strict):
    dia_semana: int = Field(ge=0, le=6, strict=True)
    inicio: time
    fin: time

    @field_validator("inicio", "fin")
    @classmethod
    def horario_local_sin_offset(cls, value: time) -> time:
        if value.tzinfo is not None:
            raise ValueError("Los horarios semanales son horas locales sin offset.")
        return value


class HorariosSemanaUpdate(Strict):
    horarios: list[HorarioSemanalInput]


class HorarioSemanalResponse(Strict):
    id: str
    dia_semana: int
    inicio: time
    fin: time


class HorariosSemanaResponse(Strict):
    profesional_id: str
    zona_horaria: str
    horarios: list[HorarioSemanalResponse]


class ConfigResponse(Strict):
    antelacion_cancel_hs: int
    antelacion_reserva_hs: int = 2
    recordatorio_t_48h: bool = True
    recordatorio_t_24h: bool = True
    recordatorio_1_hs: int = 48
    recordatorio_2_hs: int = 24
    whatsapp_costo_centavos: int = 0


class ConfigUpdateRequest(Strict):
    antelacion_cancel_hs: int = Field(ge=0)
    antelacion_reserva_hs: int = Field(default=2, ge=0)
    recordatorio_t_48h: bool | None = None
    recordatorio_t_24h: bool | None = None
    recordatorio_1_hs: int | None = Field(default=None, ge=0)
    recordatorio_2_hs: int | None = Field(default=None, ge=0)
    whatsapp_costo_centavos: int | None = Field(default=None, ge=0)

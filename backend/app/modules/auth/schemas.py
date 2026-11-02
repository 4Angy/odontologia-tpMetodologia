"""DTOs Pydantic v2 de auth (R3/R4: nada de modelos SQLAlchemy, `extra='forbid'`)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Estricto(BaseModel):
    """Base de la API pública: rechaza campos no declarados (R4)."""

    model_config = ConfigDict(extra="forbid")


class LoginRequest(_Estricto):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)
    tenant_slug: str | None = None  # solo si el email se repite entre consultorios


class ResetSolicitarRequest(_Estricto):
    email: str = Field(min_length=3, max_length=255)


class ResetConfirmarRequest(_Estricto):
    token: str = Field(min_length=8, max_length=128)
    nueva_password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # segundos de vigencia del access


class MeResponse(BaseModel):
    sub: str
    email: str | None = None
    nombre: str | None = None
    roles: list[str]
    permisos: list[str]  # unión de roles (RN-AU-04)


class ResetSolicitudResponse(BaseModel):
    message: str
    token: str | None = None  # solo fuera de prod (el email real llega en C-09)

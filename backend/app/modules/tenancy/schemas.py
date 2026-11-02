"""DTOs Pydantic v2 de gestión de usuarios del tenant (R3/R4: nada de modelos SQLAlchemy, `extra='forbid'`)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Estricto(BaseModel):
    """Base de la API pública: rechaza campos no declarados (R4)."""

    model_config = ConfigDict(extra="forbid")


class InviteRequest(_Estricto):
    email: str = Field(min_length=3, max_length=255)
    nombre: str | None = Field(None, max_length=200)
    roles: list[str] = Field(min_length=1)


class UserResponse(BaseModel):
    id: str
    email: str
    nombre: str | None = None
    roles: list[str]
    activo: bool


__all__ = ["InviteRequest", "UserResponse"]

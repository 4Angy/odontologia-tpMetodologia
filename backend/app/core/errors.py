"""Contrato de error del proyecto (R9 / RN-GL-01).

Toda respuesta de error del backend tiene la forma `{code, message, action?}`:

- `code`: identificador de la regla de negocio que causa el error (`RN-XX`)
  o el código genérico documentado cuando no hay ninguna regla aplicable.
- `message`: texto en español-AR, mostrable al usuario final sin traducción.
- `action`: presente solo cuando hay una acción sugerible (p. ej. reprogramar).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

#: Código genérico para errores que no mapean a una regla de negocio (RN-GL-01).
GENERIC_ERROR_CODE = "RN-GL-00"

#: Mensaje genérico, mostrable al usuario final.
GENERIC_ERROR_MESSAGE = "Ocurrió un error inesperado. Probá de nuevo."

#: Mensaje para errores de validación de entrada (no hay regla de negocio).
VALIDATION_ERROR_MESSAGE = "Los datos enviados no son válidos."


@dataclass(frozen=True)
class ErrorAction:
    """Acción sugerible ante un error (p. ej. `reprogramar`)."""

    type: str
    hint: str

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "hint": self.hint}


class AppError(Exception):
    """Error de aplicación con `code` trazable a una regla de negocio."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        action: ErrorAction | Mapping[str, Any] | None = None,
        status_code: int = 400,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.action = action
        self.status_code = status_code
        self.context = dict(context or {})

    def to_body(self) -> dict[str, Any]:
        """Serializa al sobre `{code, message, action?}`."""
        body: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.action is not None:
            if isinstance(self.action, ErrorAction):
                body["action"] = self.action.to_dict()
            else:
                body["action"] = dict(self.action)
        return body

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"AppError(code={self.code!r}, status_code={self.status_code})"


def error_body(
    code: str,
    message: str,
    action: ErrorAction | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Construye el sobre de error sin necesidad de una excepción."""
    body: dict[str, Any] = {"code": code, "message": message}
    if action is not None:
        body["action"] = action.to_dict() if isinstance(action, ErrorAction) else dict(action)
    return body


__all__ = [
    "GENERIC_ERROR_CODE",
    "GENERIC_ERROR_MESSAGE",
    "VALIDATION_ERROR_MESSAGE",
    "AppError",
    "ErrorAction",
    "error_body",
]

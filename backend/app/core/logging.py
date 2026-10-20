"""Logging estructurado del backend (C-01).

Cada registro es una línea JSON con `ts` (UTC), `level`, `logger`, `message` y
`context` (campos separados). Los valores sensibles —tokens, claves, secretos y
contraseñas dentro de URIs— NUNCA aparecen en el log.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

#: Placeholder que reemplaza a todo valor sensible.
REDACTED = "***"

#: Claves cuyo valor se redacta siempre.
SENSITIVE_KEY_RE = re.compile(
    r"(secret|token|password|passwd|api[_-]?key|credential|private[_-]?key)",
    re.IGNORECASE,
)

#: Credenciales embebidas en una URI (`scheme://user:pass@host`).
_URI_CREDENTIALS_RE = re.compile(r"(?P<pre>[a-zA-Z0-9+.\-]+://[^:@/\s]*:)(?P<pw>[^@/\s]*)(?P<post>@)")

#: Handler instalado por `configure_logging` (para poder reemplazarlo).
_MARKER = "_c01_structured_handler"


def is_sensitive_key(key: Any) -> bool:
    """¿La clave representa un valor que nunca debe loguearse?"""
    return bool(SENSITIVE_KEY_RE.search(str(key)))


def scrub_uri(text: str) -> str:
    """Reemplaza la contraseña de una URI por el placeholder."""
    return _URI_CREDENTIALS_RE.sub(lambda m: f"{m.group('pre')}{REDACTED}{m.group('post')}", text)


def redact(value: Any, secrets: Iterable[str] = ()) -> Any:
    """Redacta valores sensibles de una estructura arbitraria."""
    literales = tuple(s for s in secrets if s)
    if isinstance(value, Mapping):
        return {
            clave: (REDACTED if is_sensitive_key(clave) else redact(valor, literales))
            for clave, valor in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [redact(v, literales) for v in value]
    if isinstance(value, str):
        for literal in literales:
            if literal in value:
                value = value.replace(literal, REDACTED)
        return scrub_uri(value)
    return value


class StructuredFormatter(logging.Formatter):
    """Formatea los registros como JSON con contexto en campos separados."""

    def __init__(self, *, secrets: Iterable[str] = ()) -> None:
        super().__init__()
        self._secrets = tuple(s for s in secrets if s)

    def format(self, record: logging.LogRecord) -> str:
        contexto = getattr(record, "context", None)
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if isinstance(contexto, Mapping) and contexto:
            payload["context"] = redact(dict(contexto), self._secrets)
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", *, secrets: Iterable[str] = ()) -> logging.Logger:
    """Instala el handler estructurado en el logger raíz.

    No elimina handlers ajenos (pytest los usa para `caplog`).
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, _MARKER, False):
            root.removeHandler(handler)
    handler = logging.StreamHandler(stream=sys.stdout)
    setattr(handler, _MARKER, True)
    handler.setFormatter(StructuredFormatter(secrets=secrets))
    root.addHandler(handler)
    root.setLevel(str(level).upper())
    return root


def log_event(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any,
) -> None:
    """Emite un registro con el contexto en campos separados."""
    logger.log(level, message, extra={"context": context})


__all__ = [
    "REDACTED",
    "StructuredFormatter",
    "configure_logging",
    "is_sensitive_key",
    "log_event",
    "redact",
    "scrub_uri",
]

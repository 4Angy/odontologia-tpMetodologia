"""Envío de email por SMTP (fallback RN-PA-04)."""
from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Optional, Protocol
from urllib.parse import urlparse

from app.core.config import get_settings


@dataclass(frozen=True)
class EmailResultado:
    ok: bool
    message_id: Optional[str] = None
    error_code: Optional[str] = None
    transitorio: bool = False


class EmailClient(Protocol):
    def enviar(self, *, destinatario: str, asunto: str, cuerpo: str) -> EmailResultado: ...


class SmtpEmailClient:
    def __init__(self, smtp_url: str | None = None, timeout: float = 10.0) -> None:
        self.smtp_url = smtp_url if smtp_url is not None else _smtp_url_from_settings()
        self.timeout = timeout

    def enviar(self, *, destinatario, asunto, cuerpo) -> EmailResultado:
        if not self.smtp_url:
            return EmailResultado(ok=False, error_code="RN-GL-03", transitorio=True)
        parsed = urlparse(self.smtp_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 587
        usuario = parsed.username
        clave = parsed.password
        mensaje = EmailMessage()
        mensaje["From"] = "no-reply@consultorio.local"
        mensaje["To"] = destinatario
        mensaje["Subject"] = asunto or "Recordatorio"
        mensaje.set_content(cuerpo)
        try:
            with smtplib.SMTP(host, port, timeout=self.timeout) as server:
                if usuario and clave:
                    server.starttls()
                    server.login(usuario, clave)
                server.send_message(mensaje)
        except (smtplib.SMTPException, OSError) as exc:  # noqa: BLE001
            return EmailResultado(ok=False, error_code="RN-GL-03", transitorio=True)
        return EmailResultado(ok=True, message_id=f"smtp-{hash(destinatario) & 0xffff:x}")


class FakeEmailClient:
    def __init__(self, *, ok: bool = True, error_code: str | None = None, transitorio: bool = False) -> None:
        self.ok = ok
        self.error_code = error_code
        self.transitorio = transitorio
        self.llamadas: list[dict] = []

    def enviar(self, *, destinatario, asunto, cuerpo) -> EmailResultado:
        self.llamadas.append({"destinatario": destinatario, "asunto": asunto, "cuerpo": cuerpo})
        if self.ok:
            return EmailResultado(ok=True, message_id="fake-email-1")
        return EmailResultado(
            ok=False, error_code=self.error_code or "RN-GL-03", transitorio=self.transitorio
        )


def _smtp_url_from_settings() -> str | None:
    try:
        settings = get_settings()
    except Exception:  # noqa: BLE001
        return None
    if settings.smtp_url is None:
        return None
    return settings.smtp_url.get_secret_value()


__all__ = ["EmailClient", "EmailResultado", "FakeEmailClient", "SmtpEmailClient"]

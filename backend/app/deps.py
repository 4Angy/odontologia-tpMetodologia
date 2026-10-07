"""Dependencias inyectables (sesión DB + reloj) para tests herméticos."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Request


def get_session(request: Request):  # type: ignore[no-untyped-def]  # resuelto por create_app
    return request.app.state.session_factory()


def get_now() -> datetime:
    return datetime.now(timezone.utc)

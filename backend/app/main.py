"""App FastAPI del slice (monolito modular, costo operativo bajo)."""
from __future__ import annotations

from typing import Callable

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app import deps
from app.modules.agenda.router import router as agenda_router


def create_app(*, session_factory=None, now_fn: Callable | None = None) -> FastAPI:
    app = FastAPI(title="Consultorio Odontológico — slice cancelación")

    if session_factory is not None:
        app.state.session_factory = session_factory

        def _session_override():  # type: ignore[no-untyped-def]
            s = session_factory()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[deps.get_session] = _session_override

    if now_fn is not None:
        app.dependency_overrides[deps.get_now] = now_fn

    # Errores HTTP con `detail` dict → shape {code, message, action?} directo.
    @app.exception_handler(HTTPException)
    async def _http_error(request, exc: HTTPException):  # type: ignore[no-untyped-def]
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content=detail)

    app.include_router(agenda_router)
    return app


app = create_app()

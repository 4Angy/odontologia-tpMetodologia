"""App FastAPI del proyecto (C-01 foundation + módulos de dominio).

Monolito modular, un solo deploy (DD-03). Este módulo arma la app, instala el
logging estructurado, expone los health checks y traduce **todo** error al
sobre `{code, message, action?}` (R9 / RN-GL-01).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Callable, Mapping

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import sessionmaker

from app import deps
from app.core.config import SERVICE_NAME, SERVICE_VERSION, ConfigError, get_settings
from app.core.errors import (
    GENERIC_ERROR_CODE,
    GENERIC_ERROR_MESSAGE,
    VALIDATION_ERROR_MESSAGE,
    AppError,
)
from app.core.logging import configure_logging, log_event
from app.modules.agenda.router import router as agenda_router
from app.modules.auth.router import router as auth_router
from app.modules.tenancy.router import router as tenancy_router

logger = logging.getLogger("odontologia.api")

#: Sonda de readiness: devuelve True si la dependencia está operativa.
Probe = Callable[[], bool]


def _sondas_por_defecto() -> dict[str, Probe]:
    return {"database": deps.database_probe, "redis": deps.redis_probe}


def create_app(
    *,
    session_factory: Any = None,
    now_fn: Callable | None = None,
    probes: Mapping[str, Probe] | None = None,
) -> FastAPI:
    """Construye la aplicación.

    `session_factory`, `now_fn` y `probes` son puntos de inyección para tests
    (app sin dependencias externas).
    """
    sondas = dict(probes) if probes is not None else _sondas_por_defecto()

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
        # Logging primero: así los avisos de la carga de configuración
        # (p. ej. el secreto temporal en dev/test) salen por el handler
        # estructurado y no por el handler por defecto de la librería.
        configure_logging()
        try:
            settings = get_settings()
        except ConfigError as exc:
            log_event(
                logger,
                logging.CRITICAL,
                "configuración inválida: la aplicación no arranca",
                detalle=str(exc),
            )
            raise
        configure_logging(settings.log_level, secrets=settings.sensitive_values())
        log_event(
            logger,
            logging.INFO,
            "servidor arrancando",
            env=settings.app_env,
            service=SERVICE_NAME,
            version=SERVICE_VERSION,
        )
        yield
        log_event(logger, logging.INFO, "servidor detenido")

    app = FastAPI(title="Consultorio Odontológico", lifespan=lifespan)

    if session_factory is not None:
        app.state.session_factory = session_factory

        def _session_override():  # type: ignore[no-untyped-def]
            s = session_factory()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[deps.get_session] = _session_override
    else:
        app.state.session_factory = sessionmaker(bind=deps.get_engine())

    if now_fn is not None:
        app.dependency_overrides[deps.get_now] = now_fn

    # --- Health checks ------------------------------------------------------

    @app.get("/health", tags=["runtime"])
    def health() -> dict[str, Any]:
        """Liveness: no toca la base de datos ni Redis (un fallo de dependencia
        no debe reiniciar el contenedor)."""
        return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}

    @app.get("/health/ready", tags=["runtime"])
    def readiness() -> JSONResponse:
        """Readiness: verifica cada dependencia e identifica la que falla."""
        componentes: dict[str, str] = {}
        for nombre, sonda in sondas.items():
            try:
                operativo = bool(sonda())
            except Exception:  # noqa: BLE001 - la sonda decide, no el handler
                operativo = False
            componentes[nombre] = "ok" if operativo else "fallo"

        listo = all(estado == "ok" for estado in componentes.values())
        return JSONResponse(
            status_code=200 if listo else 503,
            content={
                "status": "ready" if listo else "not_ready",
                "service": SERVICE_NAME,
                "version": SERVICE_VERSION,
                "components": componentes,
            },
        )

    # --- Errores: siempre `{code, message, action?}` ------------------------

    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        log_event(
            logger,
            logging.WARNING,
            "error de negocio",
            code=exc.code,
            status=exc.status_code,
            path=request.url.path,
            **exc.context,
        )
        return JSONResponse(status_code=exc.status_code, content=exc.to_body())

    @app.exception_handler(HTTPException)
    async def _http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, Mapping) and "code" in detail:
            cuerpo = {
                clave: detail[clave]
                for clave in ("code", "message", "action")
                if clave in detail
            }
        else:
            cuerpo = {"code": GENERIC_ERROR_CODE, "message": str(detail)}
        log_event(
            logger,
            logging.WARNING,
            "error http",
            code=cuerpo.get("code", GENERIC_ERROR_CODE),
            status=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(status_code=exc.status_code, content=cuerpo)

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        log_event(
            logger,
            logging.WARNING,
            "entrada inválida",
            code=GENERIC_ERROR_CODE,
            status=422,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=422,
            content={"code": GENERIC_ERROR_CODE, "message": VALIDATION_ERROR_MESSAGE},
        )

    @app.exception_handler(Exception)
    async def _unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        log_event(
            logger,
            logging.ERROR,
            "error inesperado",
            code=GENERIC_ERROR_CODE,
            status=500,
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={"code": GENERIC_ERROR_CODE, "message": GENERIC_ERROR_MESSAGE},
        )

    app.include_router(agenda_router)
    app.include_router(auth_router)
    app.include_router(tenancy_router)
    return app


app = create_app()

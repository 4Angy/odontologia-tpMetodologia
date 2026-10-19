# Proposal — C-01 `foundation-setup-decisiones`

> Change GATE 0. Sin dependencias. Governance **ALTO**: las decisiones que cierra condicionan todo el Sprint 1.
> Decisiones tomadas en `discovery/explore-c01-foundation-setup-decisiones.md` (selección del usuario: A / A / A / A + Postgres 16 real en dev y CI).

## Why

El Sprint 1 no puede arrancar con dos decisiones bloqueantes sin resolver (PA-01: proveedor de WhatsApp v1; PA-02: alcance exacto de "facturación" v1) y sin el andamiaje mínimo sobre el que se construyen C-02..C-13: configuración por variables de entorno, health check, errores con `code` trazable a RN-XX, CI en verde y un compose de un solo deploy.

Hoy el repo tiene un slice aislado (cancelación de turnos, archivado) construido **sin configuración por entorno, sin health check, sin CI y sin compose**, más dos huecos de contrato que este change cierra: (a) el alcance de "facturación" v1 nunca quedó operacionalizado —DD-02 lo decidió en abstracto, pero C-11 necesita el modelo exacto de `cobros/`— y (b) la garantía de migración v1→v2 hacia odontograma FDI (riesgo R1) no está escrita en ningún lado, sólo enunciada en DD-01.

## What Changes

**Decisiones (documentadas como ADR en `docs/adr/`, con owner y criterios de aplicación):**

- **ADR-001 — WhatsApp v1 = `official` (Cloud API de Meta).** Se implementa un único adaptador detrás de la interfaz `WhatsAppClient`; el valor `gateway` sobrevive en el enum `WHATSAPP_PROVIDER` documentado como camino de v2, sin implementar en v1. Fija `WHATSAPP_PROVIDER=official`, `WHATSAPP_API_TOKEN`, `WHATSAPP_PHONE_ID` y el runbook de onboarding por tenant (WABA + plantillas preaprobadas). Owner del comportamiento: **C-09**.
- **ADR-002 — "Facturación" v1 = caja manual, sin comprobante.** Sin tabla `recibo` ni campo `numero_comprobante`; el modelo de `cobros/` queda en `cobro` + `cierre_caja`. La UI declara el alcance. Owner del comportamiento: **C-11**.
- **ADR-003 — Contrato de migrabilidad FDI (cierre verificable de R1).** Se fija la lista cerrada de campos de `evolucion` v1 proyectables a odontograma FDI v2 y el criterio de aceptación que C-05 debe cumplir ("toda `evolucion` v1 es proyectable a FDI sin pérdida"), con test de proyección. Owner del comportamiento: **C-05**.

**Andamiaje (código e infraestructura):**

- **Backend**: settings por env vars (14 vars de `08_arquitectura_propuesta.md`) con validación y fail-fast en boot; `GET /health` (liveness) y `GET /health/ready` (readiness, verifica Postgres y Redis); logging estructurado; contrato de error `{code, message, action?}` con `code` trazable a RN-XX formalizado como regla transversal; estructura de directorios canónica (`core/`, `modules/{agenda,pacientes,cobros,notificaciones,tenancy}/`, `worker/`, `alembic/`, `tests/`).
- **Frontend**: scaffolding Vite + React 18 + TS 5 con `main.tsx`/`App.tsx`, router, `shared/api/client.ts` con manejo del `code` RN-XX, y scripts `dev`/`build`/`preview`/`test`/`typecheck`.
- **Infra**: `docker-compose.yml` con `api` + `worker` + `postgres:16` + `redis:7` (AOF); `.env.example` en raíz, backend y frontend sin secretos; GitHub Actions con jobs `backend` y `frontend` en paralelo, Postgres 16 y Redis 7 como services, y `alembic upgrade head → downgrade -1 → upgrade head` para probar reversibilidad (R6).
- **Esquema**: se respeta la migración `0001_cancelacion_turno` ya existente como base real del esquema. **C-02** pasa a ser la migración `002` (crea `usuario`, extiende `tenant` y `config`) y **C-07** pasa a extender `turno` en vez de crearla. La numeración 003-012 queda intacta.

**No breaking changes** sobre comportamiento de negocio existente: el spec `agenda/cancelacion-turno` no cambia sus requisitos.

## Capabilities

### New Capabilities

- `foundation/runtime`: contrato del runtime de la aplicación — carga y validación de settings desde variables de entorno, `GET /health` y `GET /health/ready`, logging estructurado y el sobre de error `{code, message, action?}` con `code` trazable a RN-XX como contrato transversal del proyecto.

### Modified Capabilities

- (ninguna — `agenda/cancelacion-turno` mantiene sus requisitos sin cambios)

## Impact

**Código afectado**

- `backend/app/core/`: nuevos `config.py` (settings), `errors.py` (contrato de error), `logging.py`; `security.py` deja de tener el secreto de fallback hardcodeado.
- `backend/app/main.py`: health checks, logging, wiring de settings; `backend/app/deps.py`: dependencia de sesión sobre Postgres.
- `backend/app/worker/`: esqueleto del worker (sin jobs; C-09 es su dueño).
- `backend/requirements.txt`: driver de Postgres, `pydantic-settings`, cliente Redis, `pytest`/configuración de tests.
- `backend/alembic/env.py`: metadata de todos los módulos y URL desde settings; `backend/tests/conftest.py` nuevo (fixtures sobre Postgres 16).
- `frontend/`: `src/main.tsx`, `src/App.tsx`, `src/shared/`, `src/pages/`, router, `package.json` (`react-router-dom`, scripts).

**Infraestructura**

- Nuevos: `docker-compose.yml`, `.env.example` (raíz/backend/frontend), `.github/workflows/ci.yml`, `docs/adr/ADR-001..003` + índice.
- Cambia: `CHANGES.md` (numeración de migraciones de C-02 y C-07, conteo de env vars, entregables de C-01), `knowledge-base/08_arquitectura_propuesta.md` (esquema de `DATABASE_URL` a psycopg), `knowledge-base/09_decisiones_y_supuestos.md` (PA-01 y PA-02 pasan a estar resueltas, con owner).

**APIs**: `GET /health` y `GET /health/ready` (nuevas, públicas, sin auth). Ninguna API de negocio cambia.

**Dependencias**: `psycopg` (sync, driver Postgres), `pydantic-settings`, `redis`, `react-router-dom`, `pytest-postgresql` no (fixtures propias sobre Postgres).

**Downstream**: C-02 (settings + migración `002`), C-03 (`JWT_*`), C-05 (ADR-003), C-06/C-07 (migración `006` como ALTER), C-09 (ADR-001), C-11 (ADR-002), C-12 (`MP_*`), C-13 (RLS futuro, backups).

**Datos y riesgo**: R14 (datos sintéticos), R6 (migraciones reversibles), R1/R2 (tenant siempre del JWT, sin cambios), R9 (`code` RN-XX). Sin datos de pacientes reales en seeds ni tests.

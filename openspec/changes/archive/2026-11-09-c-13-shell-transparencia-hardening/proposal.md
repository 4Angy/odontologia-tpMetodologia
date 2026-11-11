# Proposal

## Why

C-13 es el gate de salida a producción. El sistema ya cumple la cadena de valor v1 (agenda, recordatorios, caja, señas, ficha, lista de espera), pero falta el diferenciador de transparencia radical (US-012), la trazabilidad completa exigida por DD-06 (rol activo por acción en la auditoría), el hardening de lanzamiento (rate limit durable, headers de seguridad) y un seed demo operable para el onboarding en el día. Sin esto no se puede declarar el checklist de lanzamiento en verde.

## What Changes

- Auditoría: se agrega `rol_activo` a `audit_event` (migración `017`), se actualizan los call sites para registrar el rol usado y se cubren los módulos que hoy no auditan (lista de espera, auth/invitaciones, config). El endpoint `/auditoria` se registra a nivel de app (sin acoplamiento al módulo pacientes).
- Rate limiting: se implementa `RedisRateLimiter` detrás del `RateLimiter` Protocol existente y se selecciona por entorno (InMemory en tests, Redis en dev/prod); auth y `public_router` usan un factory en vez del global hardcodeado.
- Hardening HTTP: middleware de security headers (HSTS, X-Frame-Options, X-Content-Type-Options) y validación E.164/tamaños ya existentes se verifican en todas las rutas públicas.
- Transparencia: nueva página `/transparencia` (permiso `dueno`) con consumo WhatsApp, sección "qué no hace (aún)" (lista de fuera de alcance de v1) y precio ARS del plan visible in-app.
- Seed demo: se completa `seed_demo` (paciente + cobro + cierre de caja) y se invoca desde el lifespan cuando `SEED_DEMO=true`, sin bloquear el arranque si falla.
- Documentación: runbook de rotación manual de secretos, checklist de lanzamiento (métricas de éxito de `01_vision_y_objetivos.md`) y guía de onboarding en el día.

## Capabilities

### New Capabilities

- `transparencia`: página y contrato de transparencia radical (consumo WhatsApp, "qué no hace (aún)", precio ARS del plan) visible in-app para el dueño.
- `auditoria`: traza consultable por el dueño con rol activo por acción (DD-06), cubriendo todas las mutaciones del sistema.

### Modified Capabilities

- `tenancy/identidad`: la auditoría mínima de toda mutación ahora incluye el rol activo del actor (DD-06) y es consultable de forma unificada por el dueño.

## Impact

- Backend: `app/core/audit.py`, `app/core/rate_limit.py`, `app/main.py` (middleware + router de auditoría), `app/modules/*/service.py` y `router.py` (call sites), `app/modules/agenda/seed_demo.py`, nueva migración `017`.
- Frontend: nueva feature `transparencia`, `App.tsx` (ruta), `AppShell.tsx` (enlace), reuso de `ConsumoPage`.
- Base de datos: columna `rol_activo` en `audit_event` (nullable, backfill `NULL`).
- CI: sin cambios de infraestructura; se mantiene la validación de migraciones reversibles.
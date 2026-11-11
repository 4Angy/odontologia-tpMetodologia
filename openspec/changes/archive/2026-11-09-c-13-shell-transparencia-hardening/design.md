# Design

## Context

El sistema ya tiene auditoría transaccional por módulo (`registrar_auditoria` en `app/core/audit.py`) y un `RateLimiter` Protocol swapable (`app/core/rate_limit.py`) con implementación in-memory. El rate limit ya se aplica en login y rutas públicas. El panel de consumo WhatsApp (`ConsumoPage`) ya existe. El seed demo (`seed_demo`) existe pero incompleto y no se invoca automáticamente. El endpoint `/auditoria` está acoplado al módulo pacientes. Se adopta la **Opción B** (estandarización del contrato manual) frente a un middleware automático.

## Goals / Non-Goals

**Goals:**
- Agregar `rol_activo` a `audit_event` y registrarlo en todos los call sites, incluyendo módulos que hoy no auditan.
- Mover `/auditoria` a nivel de app, manteniendo el path y el RBAC (solo `dueno`).
- Implementar `RedisRateLimiter` detrás del Protocol existente, seleccionado por entorno.
- Agregar middleware de security headers.
- Completar `seed_demo` e invocarlo desde el lifespan cuando `SEED_DEMO=true`.
- Crear la página `/transparencia` en frontend.
- Documentar runbook, checklist de lanzamiento y guía de onboarding.

**Non-Goals:**
- No se renombra `audit_event` a `auditoria` (evita tocar 15+ call sites y tests); se documenta la decisión.
- No se implementa un middleware de auditoría automático (Opción A descartada).
- No se agrega facturación electrónica ni odontograma (siguen fuera de v1).
- No se cambia el contrato de las 14 variables de entorno canónicas; el precio ARS del plan es constante frontend con env var opcional.

## Decisions

### D1 — Auditoría: estandarización manual (Opción B)

Se extiende `registrar_auditoria` con parámetro `rol_activo: str | None = None`. Cada call site pasa el rol usado. Se cubren `lista_espera`, `auth` (invitaciones) y `tenancy` (config). Se mantiene la atomicidad transaccional (mutación revierte si falla el audit), que es lo que los tests `test_falla_de_auditoria_revierte_*` verifican.

Alternativa descartada (Opción A): middleware automático. Duplicaría filas con el audit manual y perdería atomicidad.

### D2 — Migración `017`: columna `rol_activo` nullable

`ALTER TABLE audit_event ADD COLUMN rol_activo VARCHAR(32) NULL`. Backfill `NULL` para históricos. Índice `(tenant_id, ocurrido_at)` ya existe. No se renombra la tabla.

### D3 — Rate limiter Redis por entorno

Se implementa `RedisRateLimiter` usando `INCR` + `EXPIRE` atómico (pipeline) detrás del mismo Protocol. Un factory `get_rate_limiter()` devuelve `InMemoryRateLimiter` cuando `APP_ENV=test` y `RedisRateLimiter` en caso contrario. Auth y `public_router` reciben el limiter vía factory en vez del global hardcodeado. Los tests que instancian `InMemoryRateLimiter` directamente no se ven afectados.

### D4 — Security headers middleware

Middleware Starlette que agrega `Strict-Transport-Security`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin` a todas las respuestas. Se instala en `create_app` junto a CORS.

### D5 — `/auditoria` a nivel app

Se crea `app/core/audit_router.py` (o se mueve el existente) con el endpoint `/auditoria` registrado en `main.py` fuera del módulo pacientes. El path y el RBAC (solo `dueno`) se mantienen. El módulo pacientes deja de exponer `audit_router`.

### D6 — Seed demo invocado por flag

En el lifespan, si `settings.seed_demo` es True, se ejecuta `seed_demo(session)` dentro de try/except que loguea pero no bloquea el arranque. Se completa el seed con 1 paciente demo, 1 cobro y 1 cierre de caja para que el tenant sea operable.

### D7 — Transparencia en frontend

Nueva feature `transparencia/` con página que reusa `getConsumo`, lista estática de fuera de alcance y constante `PLAN_PRICE_ARS_CENTS` (env var opcional `VITE_PLAN_PRICE_ARS_CENTS`). Ruta `/transparencia` con permiso `dueno`, enlace en `AppShell`.

## Risks / Trade-offs

- [Rol activo NULL en históricos] → la spec exige que la consulta lo tolere; tests de borde cubren el caso.
- [Redis no disponible en dev] → el factory cae a InMemory con log de warning; no bloquea el arranque.
- [Seed demo roto] → try/except en lifespan; el contenedor arranca igual y el error queda en log.
- [Duplicación de audit en módulos que ya auditan] → no se duplica porque se extiende el call site existente, no se agrega middleware.
- [Precio ARS hardcodeado] → aceptable para v1; env var opcional permite ajuste sin rebuild.

## Migration Plan

1. Aplicar migración `017` (add `rol_activo`) con downgrade que la elimina.
2. Desplegar backend (los call sites nuevos son backward-compatible porque `rol_activo` es opcional).
3. Desplegar frontend con la nueva ruta.
4. Verificar checklist de lanzamiento.

Rollback: downgrade `017` + revertir deploy; los eventos históricos no se pierden porque la columna es nullable.

## Open Questions

- ¿El precio ARS del plan se moverá a un endpoint configurable en v1.1? (diferible, no cambia el approach).
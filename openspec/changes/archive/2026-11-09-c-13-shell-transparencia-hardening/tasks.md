# Tasks

## 1. Migración y modelo de auditoría

- [x] 1.1 Crear migración `017_audit_rol_activo` que agrega `rol_activo VARCHAR(32) NULL` a `audit_event` con downgrade reversible; verificar ciclo `upgrade head → downgrade 016 → upgrade head` en Postgres 16.
- [x] 1.2 Agregar campo `rol_activo` a `AuditEventModel` en `app/core/audit.py` y actualizar `registrar_auditoria` con parámetro `rol_activo: str | None = None`; verificar import y typecheck backend.
- [x] 1.3 Extender `AuditoriaResponse` (schemas de pacientes o core) para incluir `rol_activo`; verificar serialización en tests existentes de `/auditoria`.

## 2. Auditoría: call sites y módulos faltantes

- [x] 2.1 Actualizar call sites en agenda, pacientes, cobros y notificaciones para pasar `rol_activo` con el rol usado en la acción; verificar tests de auditoría atómica siguen verdes.
- [x] 2.2 Agregar auditoría en lista_espera (alta, oferta, aceptación, declinación, vencimiento) con `rol_activo`; verificar test de transición registra actor y rol.
- [x] 2.3 Agregar auditoría en auth (invitación de usuario) y tenancy (cambio de config) con `rol_activo`; verificar RBAC y auditoría en tests de auth/tenancy.

## 3. Rate limiter Redis y factory

- [x] 3.1 Implementar `RedisRateLimiter` en `app/core/rate_limit.py` detrás del Protocol existente usando `INCR`+`EXPIRE` atómico; verificar test unitario con fakeredis o Redis real.
- [x] 3.2 Implementar factory `get_rate_limiter()` que devuelve InMemory en `APP_ENV=test` y Redis en dev/prod, con fallback logueado; verificar selección por entorno en tests.
- [x] 3.3 Actualizar `auth/router.py` y `agenda/public_router.py` para usar el factory en vez del global hardcodeado; verificar tests de rate limit (login y público) siguen verdes.

## 4. Hardening HTTP

- [x] 4.1 Agregar middleware de security headers (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy) en `create_app`; verificar presencia de headers en `/health` y rutas públicas.
- [x] 4.2 Verificar validación E.164 y límites de tamaño en adjuntos/CSV/importación en todas las rutas públicas; verificar tests de límites existentes.

## 5. Endpoint /auditoria a nivel app

- [x] 5.1 Crear `app/core/audit_router.py` con `/auditoria` (solo `dueno`) usando `listar_auditoria`; registrar en `main.py`. Remover `audit_router` de `pacientes/router.py` manteniendo compatibilidad de import; verificar endpoint responde 200 para dueño y 403 para no-dueño.

## 6. Seed demo completo

- [x] 6.1 Completar `seed_demo` con 1 paciente demo, 1 cobro y 1 cierre de caja; verificar idempotencia (ejecutar 2 veces sin duplicar).
- [x] 6.2 Invocar `seed_demo` desde el lifespan cuando `SEED_DEMO=true`, dentro de try/except que loguea pero no bloquea el arranque; verificar arranque con `SEED_DEMO=true` y con seed roto (no cae el contenedor).

## 7. Frontend transparencia

- [x] 7.1 Crear feature `transparencia/` con página que reusa consumo WhatsApp, lista "qué no hace (aún)" y precio ARS del plan; verificar render y llamadas a API con tests de componente.
- [x] 7.2 Agregar ruta `/transparencia` en `App.tsx` (permiso `dueno`) y enlace en `AppShell.tsx`; verificar navegación y ocultamiento para no-dueño.
- [x] 7.3 Configurar `VITE_PLAN_PRICE_ARS_CENTS` opcional con fallback a constante; verificar formateo ARS con 2 decimales.

## 8. Documentación de lanzamiento

- [x] 8.1 Crear runbook de rotación manual de secretos en `docs/runbooks/rotacion-secretos.md`; verificar que los pasos son ejecutables.
- [x] 8.2 Crear checklist de lanzamiento en `docs/launch/checklist.md` con las métricas de éxito de `01_vision_y_objetivos.md`; verificar que todos los items son verificables.
- [x] 8.3 Crear guía de onboarding en el día en `docs/onboarding/guia-dia.md`; verificar que cubre alta + CSV + prueba sin tarjeta.

## 9. Integración y validación

- [x] 9.1 Ejecutar suite backend (`pytest`) y frontend (`npm test`, `npm run typecheck`, `npm run build`) y verificar que todo queda en verde.
- [x] 9.2 Verificar migración `017` con ciclo completo en Postgres 16 y `openspec validate --strict` para el change.
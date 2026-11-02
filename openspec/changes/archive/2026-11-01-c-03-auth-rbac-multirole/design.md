# Design — c-03-auth-rbac-multirole

## Context

C-02 dejó: `UsuarioModel` (password_hash nullable, `roles[]`, único `(tenant_id, email)`, `activo`), el mixin de auditaría por timestamps, el stub de `app/core/security.py` (`mint_token`, `require_auth`, `require_roles` con unión — RN-AU-04) y el `UnitOfWork` con `tenant_id` obligatorio. PyJWT está en uso (HS256). No hay frontend todavía. Variables de entorno de auth ya definidas en C-01: `JWT_SECRET`, `JWT_ACCESS_MIN` / `JWT_REFRESH_DAYS` (default 15/7). Ver proposal.md para la motivación.

## Goals / Non-Goals

**Goals:**
- Sesión JWT completa (login/refresh/logout/me/reset) con detección de reuse y revocación de familia (RN-AU-02).
- RBAC aplicado por router según la matriz de `03_actores_y_roles.md`, con permiso efectivo = unión (RN-AU-04) y soporte de "3 roles en 1 persona" (Flujo 4).
- Gestión de usuarios del tenant solo por `dueno` (US-011 CA-2).
- Shell frontend mínimo con login y módulos visibles por unión de roles.

**Non-Goals:**
- RLS Postgres (endurecimiento post-v1).
- OAuth/social login, MFA, usuario multi-tenant.
- Panel de auditoría para el dueño (la auditoría visible del dueño llega con los módulos de negocio; acá solo se registra).
- Rate limiting global en todas las rutas públicas (eso es C-08; acá se cubre solo login).
- Emails transaccionales reales: el reset devuelve el token por el endpoint de forma controlable en dev (proveedor de email es C-09).

## Decisions

1. **Estado de familia de refresh en Postgres (tabla `auth_token`), no Redis.** Cada refresh es una fila: `id (jti)`, `usuario_id`, `tenant_id`, `familia_id`, `proposito` (`refresh`|`reset`), `revoked`, `used_at`, `expira`. Rotación: si la fila está `revoked`/`used` → reuse detectado → `UPDATE ... SET revoked WHERE familia_id = X` + revocación de la sesión vía nueva emisión de access (el viejo access muere por TTL de 15 min). Reset reutiliza la misma tabla con `proposito='reset'` y vigencia 1h (una tabla = una migración menos). Alternativa considerada: Redis (registro por TTL) — descartada en el explore, decisión confirmada por el usuario: el estado de revocación de un change CRITICO no puede desaparecer con una caída/eviction de Redis.
2. **JWT HS256 con PyJWT (ya en el repo).** Claims: `sub`, `tenant_id`, `roles`, `email`, `jti`, `type` (`access`|`refresh`), `iat`, `exp`. Vigencias tomadas de Settings (`JWT_ACCESS_MIN`/`JWT_REFRESH_DAYS`), R7 en todos los datetimes. Un refresh usado como access se rechaza por `type` — no se confía solo en la firma.
3. **Refresh solo en cookie HttpOnly (secure, samesite=lax, path del endpoint de refresh); access en memoria en el frontend.** Por qué: el access puede morir con el tab sin perder la sesión (rotación vía cookie imperceptible) y el refresh nunca es accesible a JS (mitiga XSS). Alternativa (ambos en localStorage) descartada: cualquier XSS roba la sesión completa por 7 días.
4. **Passwords con bcrypt** (`bcrypt` directo, cost 12). Alternativa razonada: Argon2id (más moderno) — se elige bcrypt por soporte estable en Windows/Python 3.14 del repo y sin dependencias nativas nuevas; migrar a Argon2id más adelante es transparente (`password_hash` es libre, R6 compatible).
5. **RBAC como dependencias por router** (estilo `require_roles` existente). La matriz de `03_actores_y_roles.md` entra como constantes (`PERMISOS_AGENDA = {recurso: roles}`) importadas por cada router; `has_effective_permission` ya implementa la unión. Por qué acá y no un middleware global de policies: cada endpoint declara qué exige (legible, testeable por endpoint), y no hay tabla de permisos editable en v1 (roles fijos).
6. **Rate-limit de login in-memory por instancia** (dict `ip+email → timestamps`, ventana 60s, máx 5). Alternativa: Redis — se posterga porque v1 corre en una instancia; la interfaz `RateLimiter` deja el swap a Redis cuando haya multi-instancia (C-13).
7. **Frontend: React 18 + Vite + React Router, sin estado global extra.** `AuthContext` guarda el access en memoria; `fetch` wrapper con retry silencioso vía `/auth/refresh` al 401; cookie HttpOnly lo hace posible en el shell dev vía proxy de Vite (same-origin). Módulos (`/agenda`, `/pacientes`, `/caja`, `/config`) renderizados según la unión de roles de `GET /me`. Caso 3-roles-en-1 (US-011): la nav muestra la unión completa sin selector de usuario.
8. **Rutas de auth en `backend/app/modules/auth/`** (login, refresh, logout, me, password-reset) y **gestión de usuarios en `tenancy`** (`/users/invite`, `/users`) — la identidad ya vive ahí.

## Risks / Trade-offs

- [La tabla de familias crece con cada sesión] → purge de `auth_token` vencidos en el mismo flujo de refresh (`DELETE WHERE expira < now`) — sin job nuevo.
- [El "quién hizo qué" en negocio depende de AuditMixin que hoy solo registra timestamps] → el quién se registra en log estructurado (user_id, tenant, endpoint, code RN-XX); añadir `created_by/updated_by` a las tablas de negocio es tarea subsiguiente con la auditoría de negocio (RN-GL-02 completo).
- [Reuse detection fuerza re-login a toda la familia] → comportamiento esperado (esto ES la protección RN-AU-02); el frontend on 401 de familia revocada redirige a login con mensaje.
- [Roles en el access quedan stale hasta 15 min] → aceptable; no hay "revoke roles inmediato" en v1 (el case crítico: inactividad revoca efectivamente vía login rechazado y refresh validado contra `activo` en DB en cada rotación).
- [SameSite=lax + cross-domain deploy] → v1 despliega API y front bajo mismo dominio; si cambia, revisar SameSite=None + CSRF token (queda documentado).

## Migration Plan

1. Migración 00X: tabla `auth_token` (up) con `downgrade` que la elimina (R6).
2. Deploy: backend primero (los routers viejos no cambian de contrato), frontend después.
3. Rollback: `alembic downgrade` una migración + redeploy del tag anterior; la cookie de refresh deja de usarse.

## Open Questions

- ¿BCrypt cost 12 vs 11 bajo carga del deploy más chico? Se decide con benchmark simple en dev al momento de implementar (no cambia specs ni tasks).
- ¿`samesite=lax` vs `lax+subdomain` con el dominio real de deploy? Pendiente de dominios reales; no bloquea.

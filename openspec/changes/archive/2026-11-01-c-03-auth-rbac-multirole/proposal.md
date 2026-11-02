# Proposal — c-03-auth-rbac-multirole

## Why

C-02 dejó el núcleo multi-tenant (tenants, usuarios, aislamiento por `tenant_id`) y un stub mínimo de JWT, pero no hay forma de iniciar sesión ni de gestionar usuarios del consultorio. Sin auth real ninguna historia de usuario puede ejecutarse: la matriz RBAC (`03_actores_y_roles.md`) existe en la KB pero no está aplicada por router, y el caso "todo en una persona" (DD-06) no tiene experiencia de usuario. C-03 es el change CRITICO que desbloquea TODO lo demás del roadmap (camino crítico C-03 → C-04 → C-07 → ... y rama comercial C-11/C-12).

## What Changes

Backend:
- `POST /auth/login` (email + password; 401 genérico sin revelar existencia del email), `POST /auth/refresh` (rotación con blacklist del anterior; reuse → revocación de familia RN-AU-02), `POST /auth/logout`, `GET /me`, `POST /auth/password-reset` (token 1h), `POST /users/invite` + `GET /users` (solo `dueno`).
- JWT: access 15 min + refresh 7 días; claims `sub`, `tenant_id`, `roles`, `email`, `jti`, `type`, `iat`, `exp`; refresh en cookie HttpOnly (secure, samesite=lax).
- Estado de rotación de refresh en tabla `refresh_token` (Postgres): `jti`, `familia_id`, `revoked`, expira — revocación de familia en cascada (decisión del explore, Opción A).
- Rate-limiting 5/60s por IP+email en login.
- `require_roles()` extendido a permiso efectivo por unión (RN-AU-04) aplicado como dependencia por router según la matriz RBAC.
- Migración Alembic con `downgrade` (tabla `refresh_token`, índice por `jti` y por `familia_id`).
- Auditoría: registros de seguridad (login fallido, reuse de refresh, reset pendiente) consultables por el dueño (RN-GL-02) y rol activo registrado por acción (DD-06).

Frontend:
- Página de login + auth context (access en memoria, refresh solo por cookie).
- App shell + routing base (`/agenda`, `/pacientes`, `/caja`, `/config`).
- Derivación de permisos por unión de roles soportando el caso "todo en una persona" (Flujo 4): los módulos visibles son la unión, sin exigir cambio de usuario.

Tests (TDD, R11): login ok/expirado/rate-limit, refresh rotation + reuse revoca familia, RBAC por rol y por unión acumulable (3 roles en 1 persona), aislamiento por tenant en auth.

## Capabilities

### New Capabilities

- `tenancy/auth`: contrato de autenticación y sesión — credenciales, tokens (access/refresh rotativo con familia en Postgres), cookie HttpOnly, logout, `GET /me`, reset de password, rate-limit de login, derivación de permisos por unión de roles en el frontend y shell mínimo visible según la unión.

### Modified Capabilities

- `tenancy/identidad`: se agrega el requisito de gestión de usuarios del tenant — invitación y listado de usuarios, y asignación de roles, operables solo por `dueno` (US-011 CA-2). Los requisitos existentes (aislamiento, 403 sin tenant, slug, unión de roles, auditoría, seed) no cambian.

## Impact

- `backend/app/core/security.py`: reemplazo del stub de C-02 por JWT completo (jti, type, exp) — misma interfaz `require_auth/require_roles` para no romper routers existentes.
- `backend/app/core/tenancy/`: nuevo `RefreshTokenRepository` (familias) + regla de tenant en queries existente.
- Nuevo módulo de rutas `backend/app/modules/auth/` (o dentro de `tenancy/`: routers de `/auth/*` y `/users*`).
- `backend/alembic/versions/`: migración nueva con downgrade.
- `frontend/`: nuevo (login, context, shell, routing base).
- Sin cambios de API breaking: los routers existentes (C-01/C-02) siguen aceptando el mismo esquema Bearer.
- Variables de entorno: reusa `JWT_SECRET`, `JWT_ACCESS_MIN`/`JWT_REFRESH_DAYS` (ya definidas en C-01); sinificación de mayores vigencias vía env, no hardcode.

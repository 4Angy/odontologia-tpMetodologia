# Tasks — c-03-auth-rbac-multirole

> R11: TDD estricto — cada task de backend/frontend se implementa con su test en rojo primero (mínimo 2 casos por comportamiento). R3/R4: DTOs Pydantic v2 con `extra='forbid'`. R7: UTC aware. R9: errores con code RN-XX. R14: datos de test sintéticos (seed `demo` de C-02).

## 1. Migración y modelo de tokens

- [x] 1.1 Migración Alembic de tabla `auth_token` (id/jti PK, usuario_id, tenant_id FK, familia_id, proposito, revoked, used_at, expira; índices por `jti` y por `(tenant_id, familia_id)`) con `downgrade` completo (R6); verificar `alembic upgrade` y `alembic downgrade` ida y vuelta en dev
- [x] 1.2 Extender `mint_token` (claims `jti`, `type`, `iat`, `exp`; vigencias desde Settings, no hardcode) con DTO Pydantic v2 `extra='forbid'`; verificar unit test de claims firmados en UTC aware, y test en rojo primero: access con `type=refresh` → 403 RN-AU-01

## 2. Auth core + endpoints de sesión

- [x] 2.1 `RefreshTokenRepository` (familias en Postgres, design decisión 1): rotar (marca usado + emite nuevo), detectar reuse, revocar familia en cascada, purge de expirados en el mismo flujo; verificar tests: rotación normal, reuse revoca familia completa, purge no borra filas vivas
- [x] 2.2 `POST /auth/login` con bcrypt (cost 12, benchmark en dev — design Open Question): 401 genérico idéntico para email inexistente y password incorrecta (tiempos comparables, anti-enumeración), 403 inactivo con contacto del dueño; verificar 4 tests: login válido emite pareja, credenciales inválidas idénticas en ambos casos, inactivo → 403, password vacía → 422
- [x] 2.3 `POST /auth/refresh`: cookie HttpOnly (secure, samesite=lax, path del endpoint), valida rotación contra el repositorio y `activo` en DB, emite pareja nueva; 401 con code RN-AU-02 en reuse con revocación cascada; verificar tests: rotación ok, reuse → familia completa revocada, usuario inactivo → rechazo, cookie ausente → 401
- [x] 2.4 `POST /auth/logout`: revoca familia, limpia cookie, idempotente sin cookie; verificar tests: logout → refresh posterior rechazado, logout sin cookie → 204
- [x] 2.5 `GET /me`: identidad + roles + permiso efectivo por unión (reusa `has_effective_permission`); verificar tests: 2 roles → unión correcta, 3-roles-en-1 → unión correcta (DD-06), sin token → 403 RN-AU-01
- [x] 2.6 `POST /auth/password-reset` (token uso único 1h con `proposito='reset'`): solicitud con respuesta genérica idéntica si el email no existe, cambio anula token y revoca familias previas; verificar tests: reset completo (password nueva + familias viejas revocadas), token expirado rechazado, token reutilizado rechazado, email inexistente → respuesta genérica

## 3. RBAC aplicado + gestión de usuarios + rate limit

- [x] 3.1 Constantes de la matriz RBAC de `03_actores_y_roles.md` como mapa compartido recurso→roles (disponible para registrar rol activo por acción, DD-06); verificar test: `dueno` cubre toda la matriz y la unión de 3 roles en 1 usuario la cubre entera
- [x] 3.2 `POST /users/invite` + `GET /users` en `modules/tenancy` con `require_roles('dueno')` (US-011 CA-2); verificar tests: dueno invita con rol acotado, no-dueno → 403 RN-AU-04, rol inexistente → 422 en español-AR, email duplicado en tenant rechazado sin filtrar otros tenants (R1)
- [x] 3.3 Rate-limit login 5/60s por IP+email, in-memory bajo interfaz `RateLimiter` swapable (design decisión 6); verificar tests: 6to intento → 429 antes de evaluar credenciales (aunque password correcta), ventana cumplida → login normal
- [x] 3.4 Eventos de seguridad en log estructurado (login fallido, reuse detectado, reset usado, invitaciones) con `user_id`, `tenant_id`, `endpoint`, `code`; verificar test: un login fallido emite el log esperado con su code

## 4. Frontend: login + shell por unión de roles

- [x] 4.1 Scaffold React 18 + TS 5 + Vite + React Router vacío en `frontend/` (sin `any`, R10) con proxy de Vite a la API para cookie same-origin; verificar login E2E en dev contra el backend
- [x] 4.2 `AuthContext`: access en memoria, wrapper de fetch con retry silencioso vía `/auth/refresh` al 401 (máx 1 reintento), redirect a login si la familia está revocada; verificar test de componente: 401 → refresh → reintento sin logout, familia muerta → redirect con mensaje
- [x] 4.3 Página de login + carga de `GET /me`: mensajes 401 genérico y 403 inactivo en español-AR; verificar flujo manual en dev con usuarios del seed `demo` (uno con 3 roles, uno solo-recepcion)
- [x] 4.4 App shell + rutas `/agenda`, `/pacientes`, `/caja`, `/config` con guard por unión de roles (Flujo 4): sección sin permiso bloqueada con mensaje; 3-roles-en-1 ve las 4 secciones sin cambio de usuario; verificar test de componente con usuario de 3 roles y uno de 1 rol
- [x] 4.5 Pantalla mínima de reset (pedir token + setear nueva password) contra `POST /auth/password-reset`; verificar test: flujo feliz y token inválido con mensaje en español-AR

## 5. Integración y cierre

- [x] 5.1 Aislamiento R1 en auth: usuario del tenant A no puede invitar ni listar sobre tenant B (cross-tenant → rechazo o sin filas); verificar suite completa `pytest` verde
- [x] 5.2 Seed `demo` idempotente también con auth activa (re-ejecución no duplica usuarios ni familias); verificar test de re-ejecución del seed (requisito ya existente en `tenancy/identidad`)
- [x] 5.3 README de módulo con endpoints `/auth/*` + vigencias 15 min/7 días + decisión A (familia en Postgres) referenciando design.md; verificar que el documento existe y las rutas coinciden con los routers

# Explore: C-03 `auth-rbac-multirole`

- Fecha: 2026-10-31
- Modo: `visual-explore-options` (thinking-partner, NO implementación, NO código)
- Change: `C-03 auth-rbac-multirole` (GATE 2, único, dependencia: C-02 ✓ archivado)
- Governance declarado: **CRITICO** (auth + tenancy sostienen todo; desbloquea TODO lo demás — C-04, C-06, C-07 y el resto esperan este change)
- Fuentes leídas: `knowledge-base/03_actores_y_roles.md` (RBAC matriz, 3-roles-1-persona), `knowledge-base/07_flujos_principales.md` (Flujo 4: Auth multi-rol), `knowledge-base/05_reglas_de_negocio.md` (RN-AU-02, RN-AU-04, RN-GL-01), `knowledge-base/08_arquitectura_propuesta.md` (§Seguridad, §Variables de entorno), `knowledge-base/04_modelo_de_datos.md` (§usuario), `CHANGES.md` (C-03), `backend/app/core/security.py`, `backend/app/core/config.py`, `backend/app/modules/tenancy/` (existe, vacío), `backend/app/modules/agenda/router.py` + `schemas.py` (patrones de router/DTO).

---

## 0. Decisiones tomadas (selección del usuario — pendiente)

| Eje | Opción elegida | Consecuencia |
|-----|----------------|--------------|
| 1 — Ubicación del código de auth | — | — |
| 2 — Blacklist / familias de refresh tokens | — | — |
| 3 — Hashing de contraseñas | — | — |
| 4 — Sesión y permisos en frontend | — | — |

---

## 1. Restricciones duras que acotan las opciones

- **R2**: el `tenant_id` siempre viene del JWT validado, **nunca** del frontend.
- **RN-AU-01**: sin `tenant_id` en el JWT → **403 con `code: RN-AU-01`**, no 404 con fuga.
- **RN-AU-02**: access 15 min + refresh rotativo 7 días; **refresh reuse = revocación de familia de tokens**.
- **RN-AU-04**: un usuario acumula roles; permiso efectivo = **unión** de roles.
- **RN-GL-01**: todo error de negocio devuelve `{code, message, action?}` con `code` trazable a RN-XX, mensaje en español-AR.
- **R3 / R4**: nunca exponer modelos SQLAlchemy; DTOs Pydantic v2 con `extra='forbid'`.
- **R5**: montos en centavos enteros (no aplica directo a auth, pero rige si hay precios de plan — fuera de C-03).
- **R6**: toda migración Alembic con `downgrade` reversible.
- **R7**: datetime naive prohibido; todo UTC con timezone.
- **R9**: todo error de negocio con `code` trazable a RN-XX.
- **R11**: TDD estricto; mínimo 2 casos por comportamiento; test en rojo antes del código.
- **R14**: solo datos sintéticos/demo en dev/tests.
- **Rate limiting login**: 5 intentos / 60s por IP + email (Flujo 4 de §07).
- **Estado real del repo**: `app/core/security.py` ya tiene `mint_token`, `require_auth`, `require_roles`, `AuthUser`, `has_effective_permission` (C-02 lo dejó como "auth mínima del slice — el auth completo es C-03"). `app/modules/tenancy/` existe pero está vacío (`__init__.py` solo). `UsuarioModel` ya tiene `password_hash`, `roles` (array enum), `activo`. `Settings` ya tiene `jwt_secret`, `jwt_access_min`, `jwt_refresh_days`. `app/modules/tenancy/` es el módulo natural para identidad (C-02 lo creó para `tenants, usuarios, roles, config` según §08).

---

## 2. El problema que las opciones resuelven

C-03 debe convertir la base de C-02 (`usuario` con `password_hash`, `roles`, `activo`) en un sistema de autenticación real:

1. **Login**: validar email+password, emitir access (15 min) + refresh rotativo (7 días, cookie HttpOnly), 401 genérico sin revelar si el email existe, 403 si `activo=false`.
2. **Refresh rotation + family revocation**: cada refresh rota el refresh token; si se presenta un refresh ya usado (reuse), se revoca toda la familia.
3. **Endpoints de identidad**: `/auth/login`, `/auth/refresh`, `/auth/logout`, `/me`, `/auth/password-reset`, `/users/invite` + `/users` (solo `dueno`).
4. **RBAC por dependencias de router**: `require_role()` aplicado por router, permiso = unión de roles.
5. **Frontend**: página de login, contexto de auth/tenant, derivación de permisos por unión de roles, caso "todo en una persona" (3 roles, 1 usuario).

Hay 4 ejes de decisión abiertos que definen cómo se implementa todo esto.

---

## 3. Eje 1 — Ubicación del código de auth en el backend

### Opción A: Extender `app/core/security.py` + router en `app/modules/tenancy/router.py`

**Qué es:** `app/core/security.py` (ya existente, C-02 lo dejó preparado) absorbe login, refresh, logout, password-reset, blacklist de refresh y hashing de contraseñas. Los endpoints HTTP (`/auth/*`, `/users/*`) viven en un nuevo `app/modules/tenancy/router.py`, siguiendo el mismo patrón que `app/modules/agenda/router.py`.

**Por qué y cómo:** `security.py` ya tiene `mint_token`, `require_auth`, `require_roles`, `JWT_ALG`, `_secret()`. Su docstring dice explícitamente *"el auth completo es C-03"*. Extenderlo evita crear un módulo nuevo solo para auth y aprovecha la inyección de `get_settings` ya resuelta. El router de tenancy usa `get_uow` (ya existente) para acceso a `usuario` y `get_session` para la sesión.

**Trade-off:**
- ✅ Pro: reusa código existente, un solo archivo de seguridad, patrón consistente con `agenda/router.py`
- ⚠️ Contra: `security.py` crece (responsabilidad mixta: bajo nivel JWT + servicio de auth)

**Esquema:**
```text
backend/app/
  core/
    security.py          <-- JWT + login/refresh/logout/blacklist/password-hash (extendido C-03)
    tenancy/
      repositories.py    <-- UnitOfWork, BaseRepository (C-02, existente)
  modules/
    tenancy/
      router.py          <-- POST /auth/login, /refresh, /logout, /me, /password-reset, /users/invite, /users (C-03, nuevo)
```

---

### Opción B: Nuevo `app/core/auth.py` (capa de servicio) + `app/core/security.py` solo bajo nivel + router en `app/modules/tenancy/router.py`

**Qué es:** `app/core/security.py` se queda con lo bajo nivel (firmar/decodificar JWT, `require_auth`, `require_roles`). Todo lo de mayor nivel (login, refresh rotation, blacklist, family revocation, hashing, password reset) va en un nuevo `app/core/auth.py`. El router de tenancy consume `app.core.auth`.

**Por qué y cómo:** Separa responsabilidades: `security.py` = criptografía JWT pura; `auth.py` = reglas de negocio de sesiones (rotación, familia, blacklist, rate limiting). Es más testeable: el servicio de auth se puede unit-testear sin HTTP, y `security.py` sigue siendo una fina capa de cifrado.

**Trade-off:**
- ✅ Pro: separación nítida (criptografía vs reglas de sesión), más testeable, `security.py` no crece desmesurado
- ⚠️ Contra: un módulo nuevo más; dos archivos en `core/` relacionados con auth

**Esquema:**
```text
backend/app/
  core/
    security.py          <-- JWT bajo nivel (firmar/decodificar, require_auth, require_roles) — C-02 existente
    auth.py              <-- servicio de auth: login, refresh, logout, blacklist, familias, password reset (C-03, nuevo)
    tenancy/
      repositories.py    <-- UnitOfWork, BaseRepository (C-02, existente)
  modules/
    tenancy/
      router.py          <-- endpoints /auth/*, /users/* que llaman a app.core.auth (C-03, nuevo)
```

---

## 4. Eje 2 — Dónde viven blacklist y familias de refresh tokens

### Opción A: Redis (claves `rt:{jti}`, `family:{id}`, rate-limit de login)

**Qué es:** Los refresh tokens válidos se almacenan en Redis como `rt:{jti} = family_id` con TTL de 7 días. Las familias son sets `family:{id}` con los jtis miembros. El rate-limit de login es un contador `rate:login:{ip}:{email}` con TTL 60s.

**Por qué y cómo:** Redis ya está en el stack (compose, worker, colas). Es rápido, efímero (los tokens expiran solos por TTL — no hay que limpiar manualmente), y la worker ya usa Redis para jobs persistentes con AOF. Al rotar: se lee `rt:{old_jti}`, se obtiene `family_id`, se emiten nuevos tokens, se guarda `rt:{new_jti} = family_id`, se borra `rt:{old_jti}`. Al detectar reuse (jti no está en `rt`): se revoca la familia completa borrando todos sus jtis de `rt` y el set `family:{id}`.

**Trade-off:**
- ✅ Pro: aprovecha infra existente, TTL automático (no acumula basura), rápido, consistente con el patrón worker/cola de C-09
- ⚠️ Contra: si Redis se reinicia sin AOF, los refresh tokens se pierden (los usuarios vuelven a hacer login — aceptable para v1, el access dura solo 15 min)

**Esquema:**
```text
Redis:
  rt:{jti_access}         = family_id   (TTL 15 min)   -- no, access no se guarda en Redis
  rt:{jti_refresh}        = family_id   (TTL 7 días)  -- refresh válido y sin usar
  family:{family_id}      = SET de jtis -- miembros de la familia
  rate:login:{ip}:{email} = contador    (TTL 60s)      -- rate limiting

Flujo refresh:
  cliente envía refresh cookie (jti_old)
  -> GET rt:{jti_old}  -> family_id  (si no existe: expirado o reuse)
  -> si reuse (jti en used:set): revocar familia (borrar rt:* de todos sus jtis)
  -> emitir access nuevo + refresh nuevo (jti_new, misma family_id)
  -> SET rt:{jti_new} = family_id (TTL 7d)
  -> DEL rt:{jti_old}
```

---

### Opción B: Tablas SQL (`token_blacklist`, `token_families`) + migración 003

**Qué es:** Se crean tablas en Postgres: `token_blacklist (jti PK, expires_at)` y `token_families (family_id, jti, created_at)`. El rate-limit de login puede ir en Redis o en otra tabla.

**Por qué y cómo:** Todo el estado de sesión vive en la misma base de datos que el resto del dominio. No depende de Redis para auth. Requiere migración Alembic 003 con `upgrade`/`downgrade` (R6). Las blacklist se limpian por `expires_at` (job o al consultar).

**Trade-off:**
- ✅ Pro: estado de auth consistente con el dominio, una sola fuente de verdad (DB), no hay que razonar sobre dos sistemas de almacenamiento
- ⚠️ Contra: migración extra (003) en un change ya CRITICO, consulta a DB en cada refresh (más lento que Redis), hay que implementar limpieza de filas expiradas

**Esquema:**
```text
Postgres (migración 003, C-03):
  token_blacklist(jti varchar PK, expires_at timestamptz)
  token_families(family_id varchar, jti varchar, created_at timestamptz, PK(family_id, jti))

Flujo refresh:
  cliente envía refresh cookie (jti_old)
  -> SELECT FROM token_blacklist WHERE jti = jti_old  (si está: reuse -> revocar familia)
  -> SELECT family_id FROM token_families WHERE jti = jti_old
  -> emitir access + refresh nuevo (jti_new)
  -> INSERT token_families(family_id, jti_new)
  -> INSERT token_blacklist(jti_old, expires_at)
```

---

## 5. Eje 3 — Hashing de contraseñas

### Opción A: `bcrypt` directo

**Qué es:** Agregar `bcrypt` a `backend/requirements.txt` y usar `bcrypt.hashpw` / `bcrypt.checkpw` en el servicio de auth.

**Por qué y cómo:** `bcrypt` es la librería estándar de facto para hashing de contraseñas en Python, simple, bien auditada y con un solo costo de trabajo configurable. No agrega abstracciones innecesarias.

**Trade-off:**
- ✅ Pro: simple, estándar, poco código, fácil de testear
- ⚠️ Contra: API de bajo nivel (hay que manejar `salt`/`gensalt` a mano), no tiene helpers de migración de algoritmo

---

### Opción B: `passlib[bcrypt]`

**Qué es:** Agregar `passlib[bcrypt]` a `backend/requirements.txt` y usar `CryptContext(schemes=["bcrypt"], deprecated="auto")`.

**Por qué y cómo:** `passlib` da una capa de abstracción sobre múltiples algoritmos (`bcrypt`, `argon2`, `pbkdf2`) y permite migrar de algoritmo sin romper contraseñas existentes (soporte para `deprecated`). Más futuro-proof si en v2 se quiere argon2.

**Trade-off:**
- ✅ Pro: abstraction, migración de algoritmos soportada, estándar en el ecosistema FastAPI
- ⚠️ Contra: dependencia más pesada, superficie de API más grande de lo que C-03 necesita

---

## 6. Eje 4 — Sesión y permisos en el frontend

### Opción A: `AuthContext` + `TenantContext` + hook `usePermiso(rol)` + route guard centralizado en `App.tsx`

**Qué es:** Un `AuthContext` guarda el access token, lo envía en cada request (Authorization: Bearer), y expone `login`, `logout`, `refresh`, `user`. Un `TenantContext` guarda `tenant_id` del JWT. Un hook `usePermiso(rol)` deriva el permiso por unión de roles (`recepcion` ∪ `odontologo` ∪ `dueno`). `App.tsx` tiene un route guard que redirige a `/login` si no hay sesión y filtra enlaces del `AppShell` según permisos.

**Por qué y cómo:** El access token viaja en memoria (o localStorage/sessionStorage) y se renueva con el refresh cookie. El route guard centraliza la protección: no hay que acordarse de poner `require_role` en cada página. Los enlaces del shell (Agenda, Pacientes, Caja, Configuración) se muestran u ocultan según el rol activo, reflejando la matriz RBAC de `03_actores_y_roles.md`.

**Trade-off:**
- ✅ Pro: protección centralizada, imposible olvidar proteger una ruta, UI coherente con permisos, cumple R10 (no `any`, TS estricto)
- ⚠️ Contra: más código en frontend (contextos, hook, guard), requiere manejar refresh de token en el cliente

---

### Opción B: Solo `AuthContext`, permisos derivados por componente (sin route guard centralizado)

**Qué es:** `AuthContext` expone `user` y `roles`. Cada página/componente llama `usePermiso("dueno")` y renderiza o no según el rol. No hay route guard en `App.tsx`; las rutas están abiertas pero el contenido se oculta si no hay permiso.

**Por qué y cómo:** Más simple de implementar inicialmente. Cada componente decide qué mostrar. El acceso a endpoints protegidos sigue siendo del backend (R1/R2), así que no hay fuga de datos.

**Trade-off:**
- ✅ Pro: menos código inicial, más rápido de entregar
- ⚠️ Contra: cada ruta es una oportunidad de olvidar el chequeo de permiso, UI puede mostrar rutas vacías o sin protección visual, menos alineado con "permiso por router" del backend

---

## 7. Consecuencias de la selección (pendiente — se llena tras la elección del usuario)

| Eje | Opción elegida | Consecuencia |
|-----|----------------|--------------|
| 1 — Ubicación del código de auth | — | — |
| 2 — Blacklist / familias de refresh tokens | — | — |
| 3 — Hashing de contraseñas | — | — |
| 4 — Sesión y permisos en frontend | — | — |

---

## 8. Qué queda diferido (y por qué)

| Deuda | Owner | Motivo |
|---|---|---|
| Rate limiting en rutas públicas (C-08) | C-08 | C-03 solo hace rate limiting en `/auth/login`; las rutas públicas son de C-08 |
| Webhook idempotencia (MP, WhatsApp) | C-09 / C-12 | Endpoints webhook de C-09 y C-12 |
| RLS de Postgres | C-13 | DD-04: endurecimiento posterior, no día 1 |
| `password-reset` envío de email real | C-09 | El token de reset se genera y guarda; el envío por email usa SMTP (C-09 tiene fallback email) |
| Auditoría de mutaciones de auth (quién creó qué usuario) | C-13 | La tabla `auditoria` y middleware son de C-13 |

---

### Siguiente paso

Una vez el usuario seleccione una opción por eje, se genera:
- `openspec/changes/C-03-auth-rbac-multirole/proposal.md`
- `openspec/changes/C-03-auth-rbac-multirole/design.md`
- `openspec/changes/C-03-auth-rbac-multirole/tasks.md`
- `openspec/specs/tenancy/identidad/spec.md` (o `specs/tenancy/auth/spec.md`)

y se ejecuta `/opsx:propose C-03-auth-rbac-multirole`.
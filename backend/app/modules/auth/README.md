# Módulo de Autenticación (tenancy/auth)

Este módulo implementa el contrato de autenticación y sesión del consultorio: credenciales, tokens de corta y larga vida con rotación y revocación de familia, gestión de sesiones en cookie HttpOnly, logout, identidad, reset de password, rate-limit de login y derivación de permisos por unión de roles.

## Endpoints

### POST /auth/login
Autentica un usuario por email + password dentro de su tenant y emite un access token (15 min) y un refresh token rotativo (7 días).

- **Request:** `{email, password, tenant_slug?}`
- **Response (200):** `{access_token, token_type: "bearer", expires_in}`
- **Cookie:** `refresh_token` (HttpOnly, secure, samesite=lax, path=/auth/refresh)
- **Error 401:** Credenciales inválidas (mensaje genérico, anti-enumeración)
- **Error 403:** Usuario inactivo (contactar al dueño)
- **Error 429:** Rate limit excedido (5 intentos / 60s por IP+email)

### POST /auth/refresh
Rota el refresh token: el refresh entregado queda marcado como usado y se emite un nuevo refresh de la misma familia.

- **Request:** Cookie `refresh_token`
- **Response (200):** `{access_token, token_type: "bearer", expires_in}`
- **Cookie:** Nuevo `refresh_token` (misma flags)
- **Error 401 (RN-AU-02):** Token expirado, revocado o reuse detectado (revoca toda la familia)

### POST /auth/logout
Cierra la sesión: revoca el refresh vigente con su familia y limpia la cookie.

- **Request:** Cookie `refresh_token` (opcional)
- **Response (204):** No content
- **Idempotente:** Devuelve 204 incluso sin cookie

### GET /me
Expone identidad y permisos derivados (unión de roles).

- **Request:** Header `Authorization: Bearer <access_token>`
- **Response (200):** `{sub, email, nombre, roles, permisos}`
- **Error 403:** Token inválido o ausente

### POST /auth/password-reset
Emite un token de uso único con vigencia de 1 hora para reset de password.

- **Request:** `{email}`
- **Response (200):** `{message, token?}` (token solo fuera de prod)
- **Comportamiento:** Respuesta genérica si el email no existe (anti-enumeración)

### POST /auth/password-reset/confirmar
Cambia la password con el token de reset; invalida el token y las familias previas.

- **Request:** `{token, nueva_password}`
- **Response (200):** `{message}`
- **Error 400:** Token inválido, expirado o ya usado

## Configuración

Variables de entorno (definidas en C-01):

- `JWT_SECRET`: Secreto de firma JWT (64 caracteres recomendado)
- `JWT_ACCESS_MIN`: Vigencia del access token en minutos (default: 15)
- `JWT_REFRESH_DAYS`: Vigencia del refresh token en días (default: 7)

## Decisiones de Diseño

Referencia: `openspec/changes/c-03-auth-rbac-multirole/design.md`

- **Estado de familia en Postgres:** La tabla `auth_token` guarda el estado duradero de las familias de refresh (no Redis). Una caída del servicio no revoca sesiones.
- **Refresh en cookie HttpOnly:** El access viaja en el body, el refresh exclusivamente en cookie HttpOnly (mitiga XSS).
- **Password con bcrypt:** Cost 12 (benchmark en dev). Migración a Argon2id transparente en el futuro.
- **Rate limit in-memory:** 5/60s por IP+email, interfaz `RateLimiter` swapable para Redis en C-13.
- **RBAC por router:** Dependencias `require_roles()` por endpoint según la matriz de `03_actores_y_roles.md`.

## Reglas Duras Aplicadas

- **R1:** Todo query de negocio incluye `tenant_id` del JWT (aislamiento por tenant).
- **R2:** El tenant SIEMPRE viene del JWT validado, nunca del frontend.
- **R4:** DTOs Pydantic v2 con `extra='forbid'`.
- **R7:** Todos los datetimes son UTC aware.
- **R8:** Webhooks con idempotencia (no aplica a auth, pero la tabla `auth_token` usa `jti` como PK).
- **R9:** Errores con code trazable a RN-XX (ej. `RN-AU-01`, `RN-AU-02`, `RN-AU-03`, `RN-AU-04`).
- **R11:** TDD estricto: tests en rojo antes del código.

## Seguridad

- **Anti-enumeración:** Login no revela si el email existe (mismo 401 para email inexistente y password incorrecta).
- **Reuse detection:** Un refresh reusado revoca toda la familia (RN-AU-02).
- **Reset de password:** Fuerza re-login revocando todas las familias previas.
- **Rate limiting:** 5 intentos de login por ventana de 60s por IP+email.
- **Logging estructurado:** Eventos de seguridad (login fallido, reuse, reset, invitaciones) con `user_id`, `tenant_id`, `endpoint`, `code`.

## Tests

- `test_jwt_claims.py`: Validación de claims del JWT
- `test_login_api.py`: Login, credenciales, rate limit
- `test_session_api.py`: Refresh, logout, reuse detection
- `test_reset_api.py`: Reset de password
- `test_rbac_matriz.py`: Matriz RBAC y unión de roles
- `test_rate_limit.py`: Rate limiter in-memory
- `test_security_logging.py`: Logging estructurado de seguridad

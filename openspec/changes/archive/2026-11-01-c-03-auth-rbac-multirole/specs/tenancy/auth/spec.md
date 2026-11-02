# Spec Delta — tenancy/auth

## Purpose

Define el contrato de autenticación y sesión del consultorio: credenciales, tokens de corta y larga vida con rotación y revocación de familia, gestion de sesiones en cookie HttpOnly, reset de password limitado por tiempo, rate-limit de login, la derivación de permisos por unión de roles en el frontend y el shell mínimo que expone módulos según esa unión.

## ADDED Requirements

### Requirement: Login con credenciales locales

El sistema SHALL autenticar a un usuario por `email` + `password` dentro de su tenant y, si las credenciales son válidas y el usuario está activo, SHALL emitir un access token (15 min por defecto, configurable) y un refresh token rotativo (7 días por defecto, configurable) con claims `sub`, `tenant_id`, `roles`, `email`, `jti`, `type`, `iat`, `exp`. Ante credenciales inválidas SHALL responder `401` con un mensaje genérico que no revela si el email existe. Ante usuario inactivo SHALL responder `403` con contacto sugerido al dueño del tenant.

#### Scenario: Login válido emite la pareja de tokens (funcionamiento esperado)

- **GIVEN** un usuario activo del tenant `A` con password válida y roles `recepcion` y `dueno`
- **WHEN** se ejecuta `POST /auth/login` con su email y password
- **THEN** la respuesta es `200` con el access token cuyo body contiene `sub`, `tenant_id`, roles, email, `jti` y `type=access`, y además queda emitido el refresh en una cookie HttpOnly (secure, samesite=lax) que no es accesible por JavaScript

#### Scenario: Credenciales inválidas no revelan existencia (borde)

- **GIVEN** un tenant `A` con un usuario registrado y otro email que no existe en ningún tenant
- **WHEN** se autentica con la password incorrecta del usuario y luego con el email inexistente
- **THEN** ambas respuestas son `401`, con el mismo código y el mismo mensaje genérico (sin distinguir email inexistente de password incorrecta), y el resultado llega en tiempo comparable para no filtrar por demora

#### Scenario: Usuario inactivo recibe 403 (borde)

- **GIVEN** un usuario del tenant `A` con password correcta pero `activo=false`
- **WHEN** se ejecuta `POST /auth/login` con sus credenciales
- **THEN** la respuesta es `403` con un mensaje en español-AR que indica contactar al dueño del consultorio, y no se emite ningún token

### Requirement: Refresh rotativo con familia para detección de reuse

El sistema SHALL rotar el refresh token en cada `POST /auth/refresh`: el refresh entregado queda marcado como usado y se emite un nuevo refresh de la misma familia. El estado de las familias SHALL almacenarse de forma duradera (base de datos), de modo que una caída o expulsión de caché no borre el estado de revocación. El sistema SHALL detectar el reuse de un refresh ya usado o revocado y, en ese caso, SHALL revocar TODA la familia —incluido el refresh más nuevo—, SHALL responder `401` y el usuario SHALL volver a autenticarse.

#### Scenario: Rotación normal emite pareja nueva (funcionamiento esperado)

- **GIVEN** un usuario del tenant `A` con access vencido y refresh vigente aún sin usar
- **WHEN** se ejecuta `POST /auth/refresh` con la cookie de refresh
- **THEN** la respuesta incluye un nuevo access token con los claims vigentes del usuario, el refresh anterior queda registrado como usado, y se emite un nuevo refresh en la cookie de la misma familia

#### Scenario: Reuse de refresh revoca toda la familia (error de negocio)

- **GIVEN** un usuario con un refresh que ya fue usado (y la familia renovada con un refresh más nuevo)
- **WHEN** se envía nuevamente el refresh viejo a `POST /auth/refresh`
- **THEN** la respuesta es `401`, y los tokens de la familia —incluido el refresh más nuevo que todavía era válido— quedan revocados de forma que una caída del servicio no restaure su validez

#### Scenario: El estado de familia sobrevive a una caída del cache (borde)

- **GIVEN** una sesión con refresh revocado por reuse y un cache externo que se reinicia o expulsa sus claves
- **WHEN** el refresh revocado se presenta de nuevo
- **THEN** sigue siendo rechazado, porque el estado de revocación vive en la base de datos y no en memoria caché

#### Scenario: Refresh usado como access token (borde)

- **GIVEN** un refresh token vigente firmado correctamente
- **WHEN** se presenta como `Bearer` en una operación de negocio
- **THEN** es rechazado, porque el `type` del token indica que es `refresh` y el cumpleaños del claim se verifica además de la firma

### Requirement: Logout invalida la sesión

El sistema SHALL permitir cerrar sesión vía `POST /auth/logout`: revoca el refresh vigente con su familia, limpia la cookie de refresh y deja de emitir pares de tokens para esa sesión. La operación SHALL ser idempotente.

#### Scenario: Logout cierra la sesión en el backend (funcionamiento esperado)

- **GIVEN** un usuario con sesión activa (refresh vigente en cookie)
- **WHEN** se ejecuta `POST /auth/logout`
- **THEN** el refresh queda revocado, la cookie se elimina, y un intento posterior de `POST /auth/refresh` con esa cookie es rechazado

#### Scenario: Logout sin cookie (borde)

- **GIVEN** una request sin cookie de refresh o con cookie ya revocada
- **WHEN** se ejecuta `POST /auth/logout`
- **THEN** la respuesta es `204` igual (idempotente) sin revelar el estado previo de la sesión

### Requirement: `GET /me` expone identidad y permisos derivados

El sistema SHALL exponer un endpoint autenticado `GET /me` que devuelve `sub`, `email`, `nombre`, roles y el permiso efectivo calculado como la unión de los roles del usuario, para que el frontend no vuelva a decidir el modelo de permisos.

#### Scenario: Usuario con varios roles (funcionamiento esperado)

- **GIVEN** un usuario del tenant `A` con roles `recepcion` y `odontologo`
- **WHEN** se ejecuta `GET /me` con su access token
- **THEN** la respuesta lista sus roles y su permiso efectivo es la unión, de modo que las secciones visibles del shell incluyen agenda/pacientes con ambos conjuntos sin cambio de cuenta

### Requirement: Reset de password con token de corta vida

El sistema SHALL permitir solicitar un reset `POST /auth/password-reset` que emita un token de uso único con vigencia de 1 hora para el usuario, y SHALL permitir el cambio de password con ese token. El token SHALL invalidarse tras su primer uso y SHALL verificar que la petición de reset no revele la existencia del email cuando no existe.

#### Scenario: Reset completo dentro de la ventana (funcionamiento esperado)

- **GIVEN** un usuario del tenant `A` que pide reset de password
- **WHEN** el usuario cambia su password con el token emitido dentro de la hora
- **THEN** la password queda actualizada, el token queda invalidado tras el uso, y los refresh tokens vigentes de sus familias anteriores quedan revocados para forzar re-login

#### Scenario: Token expirado o reutilizado (borde)

- **GIVEN** un token de reset emitido hace más de una hora (u otro que ya fue usado)
- **WHEN** se intenta cambiar la password con ese token
- **THEN** la petición es rechazada con un mensaje en español-AR sin revelar la fecha de emisión del token, y se pide emitir uno nuevo

#### Scenario: Reset solicitado con email inexistente (borde)

- **GIVEN** un email que no pertenece a ningún usuario del sistema
- **WHEN** se solicita el reset para ese email
- **THEN** la respuesta es exitosa genérica (idéntica a la de un email existente) sin emitir token, para no revelar qué emails están registrados

### Requirement: Rate limit de login

El sistema SHALL limitar los intentos de `POST /auth/login` a un máximo de 5 intentos por ventana de 60 segundos por par `IP + email`. Al exceder el límite SHALL responder `429` con un mensaje en español-AR antes de evaluar credenciales, y SHALL liberar el intento al cumplirse la ventana.

#### Scenario: Sexto intento dentro de la ventana (error de negocio)

- **GIVEN** cinco intentos fallidos de login desde la misma IP con el mismo email en menos de 60 segundos
- **WHEN** se intenta un sexto login con ese par IP + email
- **THEN** la respuesta es `429` con un mensaje en español-AR, sin evaluar si la password era correcta (aunque lo fuera)

#### Scenario: Ventana expirada (funcionamiento esperado)

- **GIVEN** un login que acaba de ser rechazado por rate limit
- **WHEN** se reintenta después de que la ventana de 60 segundos cumplió
- **THEN** el login se evalúa normalmente contra las credenciales (y si son válidas, emite tokens)

### Requirement: Frontend deriva permisos por unión de roles (Flujo 4)

El frontend SHALL autenticar con login, mantener el access token en memoria y el refresh exclusivamente en la cookie HttpOnly, renovarlo silenciosamente vía `POST /auth/refresh` cuando un `401` lo indica, y derivar los módulos visibles de la union de roles reportados por `GET /me`. El shell SHALL renderizar las secciones de `agenda`, `pacientes`, `caja` y `config` solo cuando la unión de roles del usuario lo permite, sin exigir cambio de usuario para operar tareas cruzadas.

#### Scenario: Consultorio unipersonal con 3 roles (funcionamiento esperado)

- **GIVEN** un usuario dueño de consultorio con los roles `recepcion`, `odontologo` y `dueno`
- **WHEN** inicia sesión en el frontend
- **THEN** el shell muestra agenda, pacientes, caja y configuración a la vez en el mismo usuario, sin selector de cuentas ni cambio de usuario para hacer tareas cruzadas

#### Scenario: Acceso a una ruta sin permiso (borde)

- **GIVEN** un usuario del tenant `A` cuyo permiso efectivo no incluye la gestión de caja
- **WHEN** navega manualmente a la ruta `/caja`
- **THEN** la ruta es bloqueada con un mensaje en español-AR y no se ejecutan consultas de negocio de caja

#### Scenario: Access vencido renueva sin logout (funcionamiento esperado)

- **GIVEN** un usuario con sesión activa cuyo access token venció (menos de 7 días)
- **WHEN** el frontend hace una operación protegida y recibe `401`
- **THEN** invoca el refresh vía la cookie HttpOnly, obtiene un nuevo access y reintenta la operación sin intervención del usuario ni pérdida de estado de la pantalla

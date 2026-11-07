# Explore: C-09 `notificaciones-whatsapp-worker`

- Fecha: 2026-11-06
- Modo: `visual-explore-options` (thinking partner — NO implementación, NO código, NO `design.md`)
- Change: `C-09 notificaciones-whatsapp-worker` (GATE 6; dependencias C-07 ✓ archivado, C-08 ✓ archivado 2026-11-05)
- Governance: **ALTO** (integración externa falible + costo por mensaje + anti-spam legal)

## Fuentes leídas

- **MCP `filesystem`** (`read_text_file`): `knowledge-base/07_flujos_principales.md` §Flujo 5.
- Lectura nativa: `05_reglas_de_negocio.md` (RN-PA-01/03/04, RN-GL-03), `06_funcionalidades.md` (US-003, US-012 CA-1), `04_modelo_de_datos.md` (`notificacion_envio`, `optin`, `plantilla`), `10_preguntas_abiertas.md` (PA-01), `08_arquitectura_propuesta.md` (cola + scheduler, idempotencia), `CHANGES.md` (C-09).
- Código real: `backend/app/worker/main.py` (tick 15 s, `JOBS=()`, Redis best-effort), `modules/agenda/models.py` (`TurnoModel`, `PublicTokenModel`), `modules/agenda/public_booking.py` (`PURPOSES`, `PUBLIC_TOKEN_TTL=72h`), `modules/agenda/public_router.py` (`POST /public/turnos/{token}/confirmar`), `modules/pacientes/models.py` (`OptInModel`), `core/config.py` (`WHATSAPP_*`, `SMTP_URL`, `REDIS_URL`), `core/rbac.py` (`recordatorios → recepcion|dueno`).
- **MCP `redis`** (`redis_health`): conectado — Redis 7.4.11, AOF activo, `DBSIZE 0` (todavía no hay claves de C-09).

> **Estado del repo al iniciar (2026-11-06).** C-09 no tiene artefactos SDD: `openspec list --json` devuelve `{"changes": []}` y no existe `openspec/changes/C-09-.../`. Hay una decisión previa en memoria (engram #55: "cola en DB, no Redis Streams") cuyos archivos no están ni en el repo ni en el historial de git, así que **se re-valida acá** en vez de darla por hecha. Derivas detectadas: `CHANGES.md` marca C-08 como `[ ]` pese a estar archivado, y le asigna a C-09 la migración **011**, que ya es de C-08 → la próxima libre es **012**.

---

## 0. Decisiones tomadas (selección del usuario, 2026-11-06)

| Eje | Opción elegida | Consecuencia |
|-----|----------------|--------------|
| 0 — Semántica de "confirmar" | **A — acuse del paciente** | `turno.confirmado_paciente_at` sin tocar `estado`; para `pendiente_confirmacion` se conserva la transición de C-08 |
| 1 — Cola y scheduler | **A — fila en DB** | `notificacion_envio` es la cola; scheduler marca `encolada` + `next_attempt_at`; worker con `FOR UPDATE SKIP LOCKED`; Redis solo lock del tick |
| 2 — Idempotencia + anti-spam | **A — constraints en DB** | `UNIQUE (tenant_id, provider_msg_id)` y `UNIQUE (tenant_id, turno_id, ventana)`; Redis solo pre-chequeo opcional |
| 3 — Adapter y test | **A — `WhatsAppClient` + fake** | `CloudApiClient` (httpx) y `FakeClient` inyectado por override; sin cambiar el enum `WHATSAPP_PROVIDER` |
| 4 — Confirmación de un toque | **A — reutilizar C-08** | Link a `POST /public/turnos/{token}/confirmar` con token `purpose="confirm"` ya existente |
| 5 — Fallback email | **A — fila encolada** | Segunda fila `canal="email"` cuando WhatsApp agota los 3 reintentos (RN-PA-04/RN-GL-03) |

> El desvío respecto de la letra del Flujo 5 de la KB (que describe Redis como cola) queda **explícito** y debe registrarse en `design.md` como decisión, mostrando que RN-GL-03 se cumple igual: la fila queda `encolada` y sobrevive reinicios.

## 0.1 Decisiones previas que condicionan (no se reabren)

| Decisión | Fuente | Consecuencia para C-09 |
|---|---|---|
| Proveedor WhatsApp = `official` (Cloud API de Meta), un adaptador detrás de `WhatsAppClient`; `gateway` queda como camino v2 | ADR-001 de C-01 (PA-01 resuelto) | Solo se implementa un adapter real + uno falso de test; no hay dos proveedores |
| `optin` por paciente/canal ya existe; sin opt-in no hay envío ni transaccional | C-04 + RN-PA-01 | El motor consulta `optin` y registra el motivo del salto |
| Tokens opacos por propósito (`confirm`/`cancel`/`reschedule`), TTL 72 h, hash no reversible, revocación por cambio de teléfono | C-08 (`PublicTokenModel`, RN-PA-02/RN-AU-03) | La confirmación "de un toque" **no necesita token nuevo**: se reutiliza el link de C-08 |
| Worker tick-based (`app/worker/main.py`, 15 s, `JOBS=()`) | C-01 | C-09 registra el job ahí; no se introduce otro runtime |
| RBAC `recordatorios → recepcion|dueno` | `core/rbac.py` | Los endpoints nacen con permisos ya declarados |

## 1. Restricciones duras

- **R1/R2**: toda fila y query con `tenant_id`; el tenant sale del JWT (o del slug en rutas públicas), nunca del body.
- **R3/R4**: DTOs Pydantic v2 con `extra='forbid'`; modelos ORM no salen de la API.
- **R5**: `costo_estimado` en **centavos enteros**; formateo ARS solo en la vista.
- **R6**: migración `012_notificaciones` reversible (upgrade/downgrade probados en Postgres 16).
- **R7**: todo datetime UTC aware (ventanas T-48/T-24 sobre `turno.inicio` timestamptz).
- **R8**: webhook idempotente por `provider_msg_id`.
- **R9**: errores con `code` trazable (`RN-PA-01`, `RN-PA-03`, `RN-PA-04`, `RN-GL-03`).
- **R11/R13**: TDD y análisis antes de código (este documento es parte de eso).
- **KB**: RN-PA-03 (≤1 mensaje por ventana/turno, T-48/T-24 configurables), RN-PA-04 (fallback email), RN-GL-03 (si el proveedor cae, la operación local se completa y el envío queda `encolada` con reintento), US-003 CA-2 (confirmación de un toque), US-012 CA-1 (panel de consumo/costo).
- **Volumen supuesto**: 300–3.000 mensajes/mes por tenant (CHANGES.md) ≈ 0,1 mensaje/minuto → la latencia no es el problema; la corrección y la auditabilidad sí.

## 2. El problema que resuelven las opciones

Convertir "recordar y confirmar" en un pipeline durable que: (a) no duplique mensajes, (b) no bloquee la operación local si Meta se cae, (c) deje el costo visible, y (d) sea verificable sin números de WhatsApp reales. Las decisiones abiertas son cinco.

---

## Eje 0 — Qué significa "confirmar" en el recordatorio

El hueco aparece al cruzar dos specs: `agenda/turnos-internos` hace nacer el turno
`confirmado` y `agenda/reserva-publica` solo define la confirmación para
`pendiente_confirmacion`. Para un turno ya confirmado, "pasa a confirmado" no
describe ninguna transición.

### Opcion A: acuse del paciente sin cambiar el estado
* **Que es?:** El click registra `turno.confirmado_paciente_at` y deja `estado` como está.
* **Por que y como:** Alembic agrega la columna en la migración 012; el link reutiliza el token `confirm` de C-08. Recepción ve "confirmó" vs "sin respuesta" sin reabrir la máquina de estados de C-07.
* **Trade-off:** Pro: conserva la señal anti-ausentismo sin tocar C-07 / Contra: "confirmar" no equivale literalmente al estado `confirmado`.
* **Esquema:**
```text
WhatsApp --> link --> POST /public/turnos/{token}/confirmar
                          |
                 marca confirmado_paciente_at
                 turno.estado sigue "confirmado"
```

### Opcion B: solo turnos `pendiente_confirmacion`
* **Que es?:** Link de confirmación solo para turnos no confirmados; al resto, mensaje informativo.
* **Por que y como:** Cero schema nuevo: se usa tal cual la transición de C-08.
* **Trade-off:** Pro: simple y ya especificado / Contra: la mayoría de los turnos nace `confirmado`, así que el "un toque" casi nunca hace nada.
* **Esquema:**
```text
estado = pendiente_confirmacion --> link C-08 --> confirmado
estado = confirmado             --> mensaje informativo (sin accion)
```

### Opcion C: estado nuevo `confirmado_por_paciente`
* **Que es?:** Se agrega un estado a la máquina de turnos.
* **Por que y como:** Cambia `turnos-internos` de C-07: transiciones, permisos y métricas.
* **Trade-off:** Pro: literal a US-003 / Contra: reabre un change archivado y multiplica los casos de estado.
* **Esquema:**
```text
pendiente_confirmacion --> confirmado --> confirmado_por_paciente --> presente
                                              ^ (nuevo estado, toca C-07)
```

**Recomendación del eje:** **A**. Es la única que conserva el valor del feature sin
gobernar de nuevo C-07.

---

## Eje 1 — Cola y scheduler: fila en DB vs cola durable en Redis

### Opcion A: `notificacion_envio` es la cola (polling en DB)
* **Que es?:** La fila del envío es el trabajo. El scheduler cada 15 min marca `encolada` + `next_attempt_at`; el worker toma filas con `FOR UPDATE SKIP LOCKED`. Redis solo aporta el lock del tick.
* **Por que y como:** SQLAlchemy 2.0 síncrono + Postgres 16 ya están en el stack; `SKIP LOCKED` da concurrencia segura sin dependencia nueva. Encaja con el worker tick-based de C-01 y deja un único estado auditable (la propia tabla que pide US-012). Redis se usa con `SET tick:{tenant} NX EX 840` para que dos instancias no programen dos veces.
* **Trade-off:** Pro: un solo estado, recuperación tras crash sin reconciliar, constraints SQL como red de seguridad / Contra: polling cada 15 min y contención si el volumen creciera mucho.
* **Esquema:**
```text
[scheduler tick 15m]--(SET NX lock)--> marca encolada + next_attempt_at
          |
          v
[worker loop]--(SELECT ... FOR UPDATE SKIP LOCKED)--> [notificacion_envio]
          |                                                  |
          +--> WhatsAppClient --> enviada | fallida <--------+
```

### Opcion B: Redis Streams como cola (DB como registro)
* **Que es?:** El scheduler publica en un stream; el worker consume con consumer group y hace `XACK`. La tabla guarda el resultado para el panel.
* **Por que y como:** Redis 7 ya está desplegado con AOF y el Flujo 5 de la KB lo describe textualmente ("scheduler Redis", "cola persistente en Redis con AOF"). `ioredis`/`redis-py` resuelven `XADD`/`XREADGROUP`/`XCLAIM` sin librerías extra.
* **Trade-off:** Pro: latencia baja y reintentos nativos del stream / Contra: duplica estado (fila + mensaje) y exige reconciliación cuando un `XACK` se pierde o el stream se recorta.
* **Esquema:**
```text
[scheduler]--> XADD recordatorios:stream
                     |
              [worker XREADGROUP]
                     |
        +------------+------------+
        v                         v
   envio OK                   envio falla
   XACK + UPDATE DB           XCLAIM reintento + UPDATE DB
```

**Recomendación del eje:** **A**. Con 300–3.000 mensajes/mes el stream no compra latencia que haga falta, y duplicar estado choca con governance ALTO. Si se elige A, el `design.md` debe registrar el desvío respecto de la letra del Flujo 5 (la KB describe Redis como cola) y mostrar que RN-GL-03 se cumple igual: la fila queda `encolada` y sobrevive reinicios.

---

## Eje 2 — Idempotencia (R8) y anti-spam (RN-PA-03)

### Opcion A: la DB es la fuente de verdad (constraints)
* **Que es?:** Dos unicidades hacen el trabajo: `UNIQUE (tenant_id, provider_msg_id)` para el webhook y `UNIQUE (tenant_id, turno_id, ventana)` para el anti-spam. Redis, si se usa, es solo un cache previo.
* **Por que y como:** Alembic agrega ambos índices en la migración 012. El reintento del webhook es un `INSERT ... ON CONFLICT DO NOTHING` + lectura del estado actual; una segunda pasada del scheduler choca contra el unique parcial y se descarta sin enviar.
* **Trade-off:** Pro: la garantía sobrevive a reinicios y a un `FLUSHALL`; auditoría directa / Contra: el webhook duplicado paga un round-trip a la DB antes de responder 200.
* **Esquema:**
```text
envio(turno, ventana) --> UNIQUE (tenant, turno, ventana) --> 2do intento = rechazo
webhook(provider_msg_id) --> UNIQUE (tenant, provider_msg_id) --> duplicado = no-op
```

### Opcion B: dedupe en Redis (SET NX)
* **Que es?:** Claves efímeras `dedupe:{tenant}:{provider_msg_id}` y `dedupe:{tenant}:{turno}:{ventana}` con `SET NX EX 7d`.
* **Por que y como:** Atómico y baratísimo; el webhook responde 200 sin tocar Postgres cuando la clave ya existe. Se apoya en el AOF que ya está activo.
* **Trade-off:** Pro: sin round-trip a la DB en el camino duplicado / Contra: si Redis se vacía o se pierde el AOF, se duplican envíos y no queda evidencia de la colisión.
* **Esquema:**
```text
webhook --> SET NX dedupe:{provider_msg_id} EX 7d
                  |
             true  -> procesa
             false -> 200 y descarta
(DB sin constraint -> un FLUSHALL puede duplicar envios)
```

**Recomendación del eje:** **A** como garantía + `SET NX` como pre-chequeo barato (cinturón y tiradores). Para RN-PA-03 la columna `ventana` (`t-48h`/`t-24h`) es la que hace verificable la regla y testeable el caso "segundo tick no reenvía".

---

## Eje 3 — Adapter WhatsApp y estrategia de test

### Opcion A: interfaz `WhatsAppClient` + fake inyectado
* **Que es?:** Un `Protocol` con dos implementaciones: `CloudApiClient` (httpx, Meta) y `FakeClient` (test). El worker depende del protocolo, no de httpx.
* **Por que y como:** `WHATSAPP_PROVIDER` ya es `Literal["official","gateway"]` en `core/config.py`; para no tocar el enum, el fake se inyecta por dependency override en los tests (mismo patrón que `get_now`/sesión en el repo). `httpx.MockTransport` cubre los códigos 200/429/500 del adapter real sin red.
* **Trade-off:** Pro: TDD sin credenciales, un solo punto para costo/plantillas/errores / Contra: el fake puede divergir del JSON real (mitigación: un test de contrato opcional contra sandbox).
* **Esquema:**
```text
worker --> WhatsAppClient (Protocol)
              |--> CloudApiClient (httpx)   [prod: official]
              |--> FakeClient              [tests: override]
httpx.MockTransport reproduce 200/429/500 sin red
```

### Opcion B: httpx + respx directo en cada test
* **Que es?:** Sin interfaz: el worker llama `httpx.post` y los tests interceptan con `respx`.
* **Por que y como:** Menos capas; los tests describen el payload exacto que espera Meta.
* **Trade-off:** Pro: cero abstracción y contrato HTTP explícito / Contra: acopla todos los tests al JSON del proveedor y no hay punto único para el fallback ni el cálculo de costo.
* **Esquema:**
```text
worker --> httpx.post(url)  <-- respx intercepta en cada test
```

**Recomendación del eje:** **A**. Governance ALTO pide una frontera explícita para todo lo que puede fallar; el fake además permite testear reintentos sin esperar.

---

## Eje 4 — Confirmación "de un toque": reutilizar C-08 o token nuevo

### Opcion A: reutilizar el token y la ruta de C-08
* **Que es?:** El mensaje incluye `{PUBLIC_BASE_URL}/r/{tenant_slug}/confirmar?token=...` con un token `purpose="confirm"` ya emitido por C-08 (TTL 72 h, hash, revocación).
* **Hueco detectado:** un link de WhatsApp se abre con un `GET` y la ruta de C-08 es `POST` con body. La solución es una página pública mínima que haga el `POST` al cargar (no un `GET` que mute estado, porque el prefetch de clientes de correo confirmaría turnos solo).
* **Por que y como:** `PublicTokenModel` y `POST /public/turnos/{token}/confirmar` ya existen y ya cambian el turno a `confirmado`. C-09 solo necesita emitir/recuperar el token al programar el envío y ponerlo en la plantilla. RN-PA-02 (cambio de teléfono revoca tokens) ya está resuelto por C-04/C-08.
* **Trade-off:** Pro: cero mecanismo nuevo, una sola fuente de verdad de tokens / Contra: la URL expone el `tenant_slug` en el path público (ya aceptado por C-08).
* **Esquema:**
```text
worker --> plantilla recordatorio --> link /public/turnos/{token}/confirmar
                                          |  (token C-08, purpose=confirm, TTL 72h)
paciente --click--> ruta publica existente --> turno.estado = confirmado
```

### Opcion B: token dedicado por envío
* **Que es?:** Columna nueva `turno.token_confirmacion` o tabla propia, con TTL corto atado al mensaje.
* **Por que y como:** Permite que cada recordatorio tenga su propio token y "muera" con el envío.
* **Trade-off:** Pro: ciclo de vida por mensaje / Contra: duplica el mecanismo de C-08, suma columnas y hay que reimplementar revocación y hash.
* **Esquema:**
```text
worker --> genera token propio --> tabla turno.token_confirmacion --> ruta nueva
```

**Recomendación del eje:** **A**. El "un toque" ya está construido; C-09 aporta el disparador y la plantilla, no un segundo sistema de tokens.

---

## Eje 5 — Fallback email (RN-PA-04)

### Opcion A: el email es otra fila del mismo motor
* **Que es?:** Cuando WhatsApp agota los 3 reintentos y el paciente tiene email, se inserta una fila `canal="email"`, `estado="encolada"`, y el mismo worker la envía por SMTP.
* **Por que y como:** Cumple RN-GL-03 al pie de la letra ("queda `encolada`"): si el worker muere entre el fallo y el email, la fila sobrevive. El panel suma ambos canales y separa el costo (WhatsApp tiene costo, email no).
* **Trade-off:** Pro: un solo pipeline, reintentos y auditoría uniformes / Contra: dos filas por turno cuando falla (el panel debe contar mensajes, no turnos).
* **Esquema:**
```text
whatsapp falla x3 --> INSERT notificacion_envio(canal=email, encolada)
                            |
                     worker toma la fila --> SMTP --> enviada | fallida visible
```

### Opcion B: email inline al detectar el fallo
* **Que es?:** El worker manda el email en el mismo momento, sin encolarlo.
* **Por que y como:** Menos filas y menos estados; el fallback "se resuelve" en la misma ejecución.
* **Trade-off:** Pro: simple y sin job extra / Contra: si el proceso cae entre el fallo y el SMTP, el email se pierde y no queda registro de la intención.
* **Esquema:**
```text
whatsapp falla x3 --> intento SMTP inline --> si el proceso muere, el email se pierde
```

**Recomendación del eje:** **A**, por RN-GL-03 y porque deja el "botón reintentar" de recepción con algo concreto que reintentar.

---

## 3. Decisiones menores (bajo impacto, se fijan en `design.md`)

| Tema | Propuesta | Por qué |
|---|---|---|
| Panel de consumo (US-012 CA-1) | `GET /notificaciones/consumo` con agregación SQL sobre `notificacion_envio` (`COUNT`, `SUM(costo_estimado)` por rango), índice `(tenant_id, created_at)` | Volumen bajo; una tabla materializada sería estado derivado a mantener |
| Lock del scheduler | `SET tick:{tenant} NX EX 840` (TTL < intervalo de 15 min) | Idempotencia del tick sin coordinador extra |
| Estados fuera de orden | Ranking `encolada < enviada < entregada`; nunca retroceder; `fallida` solo si no hubo `entregada` | Meta puede entregar eventos desordenados |
| Plantillas | Tabla `plantilla` (KB §04) seeded es-AR: confirmación, recordatorio, cancelación, lista de espera, seña | Editable por el dueño y auditable; no JSON suelto en `config` |
| Ventanas configurables | Columnas en `config`: `recordatorio_1_hs=48`, `recordatorio_2_hs=24` (migración 012) | RN-PA-03 las declara configurables |
| Costo | `costo_estimado` en centavos (R5) con tarifa versionada por categoría/país; el panel formatea ARS | No usar `float` en dinero |
| Reintentos | 3 intentos, backoff 1/5/15 min vía `next_attempt_at`; reintento manual solo desde `fallida` | Reintento exponencial de RN-GL-03, acotado y visible |
| Endpoints | `POST /notificaciones/test` (recepcion|dueno), `GET /notificaciones/consumo` (dueno), `POST /webhooks/whatsapp` (sin JWT, verificación de firma) | RBAC ya declarado en `core/rbac.py` |
| Códigos de error | `RN-PA-01` sin opt-in, `RN-PA-03` ventana duplicada, `RN-PA-04` fallback, `RN-GL-03` proveedor caído | R9 |

## 4. Trazabilidad regla → dónde se cumple

| Regla / criterio | Dónde |
|---|---|
| RN-PA-01 (sin opt-in no envía) | Scheduler consulta `optin` y registra `motivo` en la fila |
| RN-PA-03 (≤1 por ventana/turno) | Columna `ventana` + `UNIQUE (tenant_id, turno_id, ventana)` |
| RN-PA-04 (fallback email) | Fila `canal=email` tras agotar WhatsApp (Eje 5 A) |
| RN-GL-03 (proveedor caído no bloquea) | Fila `encolada` + `next_attempt_at`; turno ya confirmado por agenda |
| R8 (`provider_msg_id`) | `UNIQUE (tenant_id, provider_msg_id)` + `ON CONFLICT DO NOTHING` |
| US-003 CA-2 (confirmar de un toque) | Link a `POST /public/turnos/{token}/confirmar` de C-08 |
| US-012 CA-1 (panel consumo/costo) | `GET /notificaciones/consumo` |

## 5. Qué queda diferido (con dueño)

- **Sandbox real de Meta + plantillas aprobadas**: fuera del código; se documenta el runbook de onboarding (C-09 deja el adapter listo y el fake cubre los tests).
- **Email real**: `SMTP_URL` vacío en `.env`; para verificación local alcanza Mailhog/aiosmtpd, que se suma al compose de dev en el apply.
- **Rate-limit del webhook**: C-13 (hardening de superficies públicas).
- **Panel frontend completo**: si el alcance del apply lo exige, vista mínima en `frontend/src/features/`; el endpoint se entrega igual.
- **Deuda de `CHANGES.md`**: C-08 figura `[ ]` pese a estar archivado y C-09 conserva la migración 011 (la real es 012). Corregir antes de `/opsx:propose`.

---

## Recomendación global

**A en los cinco ejes.** Es la combinación que menos superficie nueva agrega (DB como cola y como garantía, un solo adapter, tokens y rutas ya existentes), mantiene Redis en el rol que el propio C-01 le dio (lock/cache, no segunda fuente de verdad) y hace testeable todo sin credenciales de Meta. El costo consciente es aceptar polling cada 15 min — irrelevante para 300–3.000 mensajes/mes.

## 6. Selección del usuario

**2026-11-06 — A en los seis ejes** (semántica de confirmar + los cinco del explore
original). Queda registrada en §0. El change se materializó como
`openspec/changes/c-09-notificaciones-whatsapp-worker/` con `proposal.md`,
`design.md` (D1–D16, incluida la justificación del desvío del Flujo 5 con evidencia
del MCP `redis`), tres specs delta y `tasks.md`.

> La elección del MCP es la ya tomada antes de este explore: **Redis**. El MCP se usó
> en tareas concretas de la preparación (`redis_health` y `CONFIG GET appendfsync` /
> `maxmemory-policy`) y su resultado es lo que justifica que la cola viva en Postgres.

# Informe de Preparación — Propuesta B: MCP Redis (Punto 7)

### Proyecto

SaaS multi-tenant de gestión para consultorios odontológicos (Argentina).

### Fecha

2026-11-06.

### Change

`C-09 notificaciones-whatsapp-worker` — implementado, verificado y archivado (2026-11-06).
Los artefactos SDD viven en `openspec/changes/c-09-notificaciones-whatsapp-worker/`
(`proposal.md`, `design.md`, 3 specs delta, `tasks.md` con 27 tareas marcadas `[x]`).

### Consigna del punto 7

> "Realicen la exploración del change pendiente y generen o revisen sus artefactos:
> `proposal.md`, `design.md`, especificaciones y `tasks.md`, respetando el flujo SDD
> del proyecto. Utilicen la skill propia y una herramienta del MCP en tareas
> concretas de esa preparación. Si cambian la elección respecto de la ficha inicial,
> expliquen el motivo. La especificación debe contener al menos tres escenarios
> verificables: uno de funcionamiento esperado, uno de error de negocio y uno de
> borde. Las tareas deben incluir cómo se verificará cada escenario cuando se
> implemente. Revisen las reglas contra la base de conocimiento y no incorporen
> decisiones de dominio sin justificarlas. Dejen el change preparado para implementar
> y actualicen su referencia en el roadmap según las convenciones existentes. No lo
> marquen como implementado, verificado o archivado."

## 1. Elección del change y motivo respecto de la ficha

La ficha de esta propuesta (`investigacionmcp.md` §1) declara la necesidad sobre
**Redis** y menciona a **C-9** como el change que lo usa: "cola de jobs y scheduler
de recordatorios (C-9)". Es decir, **no hay cambio de change respecto de la ficha
B**: el change preparado es el que la ficha anticipa.

El cambio es respecto de la **ficha A** (`investigacion.md` §2), que declara C-02.
Dos motivos:

1. C-02 está implementado y archivado; el punto 7 exige dejar un change
   **preparado**, no uno cerrado.
2. C-08 se archivó el 2026-11-05, lo que desbloquea el GATE 6 y deja a C-09 como el
   siguiente change del camino crítico que además **usa Redis de verdad**, que es lo
   que la propuesta B necesita para que el MCP aporte algo concreto.

## 2. Exploración con la skill propia

**Skill:** `visual-explore-options` (la misma de la propuesta A; esta propuesta no la
recrea). **Artefacto:** `discovery/explore-c09-notificaciones-whatsapp.md`.

**Procedimiento aplicado:** contexto del change y de la KB → restricciones duras →
al menos 2 alternativas por decisión → esquema ASCII → plantilla exacta →
recomendación → **pausa obligatoria**.

Seis ejes, con la opción elegida por el usuario (A en todos):

| Eje | Alternativas | Elegida | Consecuencia |
|---|---|---|---|
| 0 · Semántica de "confirmar" | acuse / solo `pendiente_confirmacion` / estado nuevo | **A** | `turno.confirmado_paciente_at` sin tocar la máquina de estados de C-07 |
| 1 · Cola y scheduler | fila en Postgres / Redis Streams | **A** | `notificacion_envio` es la cola; Redis solo coordina |
| 2 · Idempotencia y anti-spam | constraints en DB / dedupe en Redis | **A** | la garantía sobrevive a `FLUSHALL` |
| 3 · Adapter WhatsApp | `Protocol` + fake / `httpx` + `respx` | **A** | tests sin credenciales de Meta |
| 4 · Confirmación de un toque | reutilizar C-08 / token nuevo | **A** | se reutiliza token y ruta, con página pública que hace el POST |
| 5 · Fallback email | fila encolada / envío inline | **A** | la intención sobrevive a un corte del worker |

El eje 1 es donde el MCP de esta propuesta cambió la decisión: sin la evidencia de
`CONFIG GET`, la opción "Redis Streams" se sostenía en la letra del §Flujo 5 de la KB
("cola persistente en Redis con AOF"). Ver §3.

## 3. Herramienta del MCP utilizada en la preparación

**Servidor:** Redis (`@yawlabs/redis-mcp`), el elegido en `investigacionmcp.md` §3.

### 3.1 Solicitud y resultado

```
redis_health
  -> 7.4.11 · standalone · master · uptime 74.683 s
     keyspace.total_keys = 0
     persistence.aof_enabled = true · aof_last_write_status = ok
     memory.maxmemory = 0 · maxmemory_policy = noeviction · evicted_keys = 0

redis_command({ command: "CONFIG", args: ["GET", "appendfsync"] })
  -> ["appendfsync", "everysec"]

redis_command({ command: "CONFIG", args: ["GET", "maxmemory-policy"] })
  -> ["maxmemory-policy", "noeviction"]

redis_scan({ match: "tick:*" })      -> 0 claves
redis_scan({ match: "dedupe:*" })    -> 0 claves
redis_scan({ type: "stream" })       -> 0 streams
redis_advisor({ sampleSize: 200 })   -> 0 hallazgos, 0 claves muestreadas
redis_slowlog({ limit: 5 })          -> 2 entradas, ambas INFO, del propio MCP
```

### 3.2 Qué aportó al change

1. **Descartó Redis como cola con evidencia, no con opinión.** `appendfsync=everysec`
   implica que un corte puede perder hasta ~1 s de escrituras; `maxmemory-policy=noeviction`
   con `maxmemory 0` implica que, al fijarse un límite, las escrituras fallan en vez
   de desalojar. Para una cola cuya regla es "nada se pierde" (RN-GL-03), eso la
   descalifica. Quedó escrito en `design.md` D2 como justificación del **desvío
   explícito** respecto del §Flujo 5 de la KB.
2. **Fijó el rol de Redis en el diseño:** lock del tick
   (`SET tick:notificaciones:{tenant} NX EX 840`) con degradación a
   `pg_try_advisory_lock`, más un pre-chequeo opcional de deduplicación. No es una
   fuente de verdad.
3. **Dio la línea base del namespace.** `tick:*` y `dedupe:*` están libres, así que
   C-09 no colisiona con ninguna integración existente. El `slowlog` con solo
   comandos `INFO` confirma que no hay tráfico de aplicación: el "0 claves" no es un
   problema de visibilidad, es que la base está vacía.
4. **Definió la verificación post-implementación:** `redis_key_info
   tick:notificaciones:{tenant}` para comprobar TTL entre 1 y 840 s y su ausencia al
   vencer; `redis_scan` con `tick:*`, `dedupe:*` y `provider_msg_id:*` para confirmar
   el namespace. Está en `tasks.md` 8.2.

**Declaración de honestidad:** la lectura de la KB y de las specs se hizo con el
servidor de archivos (el MCP de la propuesta A), que sigue conectado. El aporte que
esta propuesta evalúa es el de Redis: durabilidad, namespace y baseline. Ambos usos
están declarados en `design.md` §Verification with MCP.

## 4. Artefactos generados

| Archivo | Tamaño | Contenido |
|---|---|---|
| `proposal.md` | 4,4 KB | Why / What Changes / Capabilities / Impact |
| `design.md` | 20,7 KB | Contexto, D1-D16, modelo de datos, API, integración con el worker, plan de migración, evidencia del MCP, riesgos y preguntas abiertas |
| `specs/notificaciones/motor-envios/spec.md` | 9,1 KB | 8 requirements nuevos, 22 escenarios |
| `specs/agenda/reserva-publica/spec.md` | 2,2 KB | delta: acuse sobre turno ya confirmado, 6 escenarios |
| `specs/agenda/turnos-internos/spec.md` | 1,4 KB | delta: `confirmado_paciente_at` en la agenda, 4 escenarios |
| `tasks.md` | 9,8 KB | 27 tareas `[ ]` con verificación + matriz de escenarios |

## 5. La especificación: 32 escenarios verificables

10 requirements, 32 escenarios. Los 8 requirements nuevos de
`notificaciones/motor-envios`:

1. El scheduler respeta opt-in y ventanas configuradas.
2. Como máximo un envío por turno, ventana y canal.
3. Los envíos pendientes se cancelan cuando dejan de ser válidos.
4. La entrega es durable, reintentable y con costo registrado.
5. El fallback a email conserva la intención de envío.
6. El webhook es autenticado, idempotente y monótono.
7. El acuse del paciente se registra sin cambiar el estado del turno.
8. El consumo y el costo son visibles por tenant.

Los deltas de `agenda/*` no inventan capabilities nuevas: modifican un requirement
existente en cada una y conservan todos sus escenarios previos.

## 6. Las tareas y cómo se verifica cada escenario

Matriz obligatoria (está al final de `tasks.md`):

| Tipo | Escenario | Tareas | Verificación |
|---|---|---|---|
| **Funcionamiento** | Turno a 48 h con opt-in → un envío `encolada` → `enviada` con `provider_msg_id` y costo en centavos | 2.1, 2.2, 3.1, 3.4 | Integración con `FakeClient`: scheduler + sender; se afirma una fila por ventana, estado `enviada`, costo > 0 y `enviado_at` UTC |
| **Error de negocio** | Sin opt-in de WhatsApp ni email → no se envía, queda `omitida` con `RN-PA-01` | 2.2, 3.5 | Cero llamadas al `FakeClient`, una fila `omitida`, `motivo_code="RN-PA-01"`, turno intacto |
| **Borde** | Dos schedulers concurrentes → un solo envío por turno y ventana | 2.3, 8.2 | Concurrencia contra PostgreSQL real: una sola fila por `(tenant, turno, ventana, canal)`; un solo `tick:*` visible con el MCP |

Bordes adicionales: turno cancelado entre encolado y envío (2.4), webhook duplicado
y fuera de orden (4.3), token expirado o revocado (5.2), Redis caído con degradación
a advisory lock (8.1).

## 7. Reglas revisadas contra la base de conocimiento

| Regla | De dónde sale | Dónde se cumple |
|---|---|---|
| RN-PA-01 (sin opt-in no se envía) | KB §05 | scheduler + envío `omitida` con motivo |
| RN-PA-03 (≤1 por ventana/turno) | KB §05 | columna `ventana` + unique `(tenant, turno, ventana, canal)` |
| RN-PA-04 (fallback email) | KB §05 | fila `canal="email"` tras agotar WhatsApp |
| RN-GL-03 (proveedor caído no bloquea) | KB §05 | fila `encolada` + `next_attempt_at`; el turno ya está confirmado |
| R1/R2, R3/R4, R5, R6, R7, R8, R9 | `AGENTS.md` | `tenant_id` del JWT, DTOs `extra='forbid'`, centavos enteros, migración reversible, UTC, idempotencia por `provider_msg_id`, códigos RN |
| US-003 CA-2 y US-012 CA-1 | KB §06 | acuse del paciente y panel de consumo |

**Decisión de dominio no cubierta por la KB**, declarada en vez de inventada: qué
pasa cuando un turno se crea dentro de la ventana. El diseño define omitir la
ventana cuyo instante de envío ya pasó (enviar un "T-24h" a 12 h contradice la
configuración del tenant) y lo deja como **PA-09** pendiente de registrar y validar
con el dueño del producto. No se editó la KB para no mezclar alcance.

## 8. Estado del change y del roadmap

- `openspec validate c-09-notificaciones-whatsapp-worker --strict` → **valid**.
- `openspec validate --all --strict` → **10/10 passed**.
- `openspec status` → `isPlanningComplete: true`, `proposal/specs/design/tasks: done`.
- `CHANGES.md`:
  - C-08 pasa a `[x]` archivado (2026-11-05) y su migración se corrige a **011**.
  - C-09 pasa a `[x]` **implementado, verificado y archivado** (2026-11-06), con la ruta de los artefactos,
    migración **012** y las 27 tareas completadas.
  - Se cierra la deriva de numeración: 012→013, 013→014, 014→015, 015→016.
  - Se corrigió el bullet de alcance que todavía decía "cola persistente Redis AOF".

## Archivos modificados y motivo

| Archivo | Motivo |
|---|---|
| `openspec/changes/c-09-notificaciones-whatsapp-worker/**` | Artefactos SDD del punto 7 |
| `discovery/explore-c09-notificaciones-whatsapp.md` | Artefacto de la skill con los 6 ejes y la selección |
| `CHANGES.md` | Referencia del change y corrección de la deriva del roadmap |
| `docs/skills-mcp/aplicacion-b.md` | Informe de aplicación de esta propuesta |
| `docs/skills-mcp/preparacion-b.md` | Este informe |
| `docs/skills-mcp/revision-critica-b.md` | Revisión crítica de esta propuesta |

## Limitaciones

- El MCP está en modo **read-only**: la verificación del lock con escritura
  (`SET ... NX EX`) queda como tarea del apply, no como evidencia de esta
  preparación.
- La base está vacía (`total_keys 0`), así que la evidencia es de configuración y de
  línea base, no de contenido real.
- El change está **implementado y verificado**: los 32 escenarios pasan (238 tests en verde).
  con los comandos que declara cada tarea.

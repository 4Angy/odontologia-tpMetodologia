# Revisión Crítica — Propuesta B: MCP Redis (Punto 8)

## Evidencia de la invocación de la skill y de la herramienta del MCP, y defectos detectados

### Proyecto

SaaS multi-tenant de gestión para consultorios odontológicos (Argentina).

### Fecha

2026-11-06.

### Alcance de esta revisión

La consigna pide guardar evidencia de la invocación de la skill y de la herramienta
del MCP —solicitud, resultado y qué aportó al change— e identificar al menos una
omisión, error o sugerencia inadecuada en los resultados del agente, explicando cómo
se detectó, qué fuente o regla permitió corregirla y mostrando el antes y el después.

Esta revisión cubre la **propuesta B**: MCP Redis aplicado al change **C-09
`notificaciones-whatsapp-worker`**. La revisión de la propuesta A (C-02 y el MCP de
archivos) sigue en `revision-critica.md` y no se modifica.

### 1. Evidencia de la invocación de la skill

**Solicitud realizada:** `skill({ id: "visual-explore-options" })` al iniciar el
explore de C-09.

**Resultado obtenido:** el `SKILL.md` completo con su procedimiento (contexto →
restricciones → ≥2 alternativas → esquema ASCII → plantilla exacta → recomendación →
pausa obligatoria). El resultado operativo es
`discovery/explore-c09-notificaciones-whatsapp.md`: 6 ejes con 2 o 3 opciones cada
uno, esquemas ASCII, alternativas descartadas con su razonamiento, tabla de
decisiones del usuario y pausa antes de `design.md`.

**Qué aportó al change:**

- Forzó a comparar antes de decidir. El eje 1 (fila en Postgres vs. Redis Streams)
  es la decisión estructural del change y quedó con evidencia, no con preferencia.
- Detectó el hueco de semántica de "confirmar" al cruzar el Eje 0 con las specs de
  agenda: sin eso, el CA-2 de US-003 no se cumplía para la mayoría de los turnos.
- Dejó por escrito por qué se descartó cada alternativa, que es lo que permite
  discutir la decisión después.

### 2. Evidencia de la invocación de la herramienta del MCP

**Servidor:** Redis (`@yawlabs/redis-mcp`, read-only por defecto), el elegido en
`investigacionmcp.md` §3.
**Instancia:** Redis 7.4.11 en `localhost:6379`, la del compose
(`docker-compose.yml:40`, `REDIS_URL: redis://redis:6379/0`).

#### 2.1 Solicitud y resultado

```
redis_health
  -> connected: true
     server: 7.4.11 · standalone · master · uptime 74.683 s
     keyspace: total_keys 0 · per_db []
     persistence: aof_enabled true · aof_last_write_status ok
     memory: maxmemory 0 · maxmemory_policy noeviction · evicted_keys 0
     clients: connected 1 · maxclients 10.000

redis_command({ command: "CONFIG", args: ["GET", "appendfsync"] })
  -> ["appendfsync", "everysec"]

redis_command({ command: "CONFIG", args: ["GET", "maxmemory-policy"] })
  -> ["maxmemory-policy", "noeviction"]

redis_scan({ match: "tick:*" })      -> keys: []  count: 0
redis_scan({ match: "dedupe:*" })    -> keys: []  count: 0
redis_scan({ type: "stream" })       -> keys: []  count: 0
redis_advisor({ sampleSize: 200 })   -> sampled_keys 0 · critical 0 · warn 0 · info 0
redis_slowlog({ limit: 5 })          -> 2 entradas, ambas "info", client_addr 172.18.0.1
```

#### 2.2 Qué aportó al change

1. **Rechazó Redis como cola con datos.** `everysec` pierde hasta ~1 s de escrituras
   ante un corte; `noeviction` con `maxmemory 0` hace que las escrituras fallen
   cuando se fije un límite. La cola quedó en `notificacion_envio` (D2).
2. **Definió el rol real de Redis:** lock del tick
   (`SET tick:notificaciones:{tenant} NX EX 840`) con degradación a advisory lock de
   Postgres, y pre-chequeo opcional de deduplicación (D3, D4).
3. **Dio la línea base del namespace** (`tick:*` y `dedupe:*` libres) y la prueba de
   que no hay tráfico de aplicación: el `slowlog` solo registra los `INFO` del propio
   MCP.
4. **Fijó la verificación post-implementación** en `tasks.md` 8.2.

#### 2.3 El otro MCP de la sesión

La lectura de la KB y de las specs se hizo con el servidor de archivos (el MCP de la
propuesta A), que sigue conectado. Se declara para no atribuir a Redis un aporte que
no tuvo: Redis aportó durabilidad, namespace y baseline; el servidor de archivos
aportó el dominio (RN-PA-01/03/04, RN-GL-03, el estado inicial del turno y los tokens
de C-08).

### 3. Defectos detectados en los resultados del agente

#### D1 — El explore recomendaba Redis Streams sin advertir su durabilidad

**Gravedad: alta.** Es la decisión estructural del change.

**Cómo se detectó:** al preparar la justificación del desvío respecto del §Flujo 5 de
la KB, en lugar de repetir "Redis tiene AOF" se consultó la configuración real de la
instancia con el MCP.

**Fuente o regla:** `redis_health` y `CONFIG GET` sobre la instancia del compose;
RN-GL-03 ("nada se pierde") como criterio de aceptación.

**Antes** (explore, Eje 1 Opción B):

> "Redis 7 ya está desplegado con AOF y el Flujo 5 de la KB lo describe textualmente
> ('scheduler Redis', 'cola persistente en Redis con AOF'). … Pro: latencia baja y
> reintentos nativos."

**Después** (`design.md` D2):

> "`appendfsync=everysec` → hasta ~1 s de escrituras se pierde ante un corte;
> `maxmemory-policy=noeviction` → al llenarse la memoria, las escrituras fallan en
> vez de desalojar. Una cola que no debe perder mensajes no puede vivir en un store
> con esas dos propiedades."

La opción B quedó descartada y el desvío del §Flujo 5 quedó documentado, en vez de
escondido.

#### D2 — "Confirmar" no podía significar "pasar a confirmado"

**Gravedad: alta.** Rompía el CA-2 de US-003 para la mayoría de los turnos.

**Cómo se detectó:** cruce de tres fuentes: `openspec/specs/agenda/turnos-internos/spec.md:16`
(el turno interno nace `confirmado`), `openspec/specs/agenda/reserva-publica/spec.md:115`
(la confirmación pública solo está definida para `pendiente_confirmacion`) y
US-003 CA-2 ("el paciente confirma… el turno pasa a `confirmado`").

**Fuente o regla:** las dos specs archivadas de agenda y la KB §06.

**Antes** (explore, Eje 4):

> `paciente --click--> ruta publica existente --> turno.estado = confirmado`

**Después** (`design.md` D1 y delta de `reserva-publica`):

> Sobre un turno `confirmado`, el click registra `turno.confirmado_paciente_at` y
> **no** cambia `estado`; sobre `pendiente_confirmacion` se conserva la transición de
> C-08 a `confirmado`.

#### D3 — El link de WhatsApp es GET y la ruta de C-08 es POST

**Gravedad: alta.** El "un toque" no funcionaba aunque el token existiera.

**Cómo se detectó:** al leer `agenda/reserva-publica/spec.md` y
`backend/app/modules/agenda/public_router.py`, la acción es
`POST /public/turnos/{token}/confirmar` con body y `tenant_slug`. Un link de WhatsApp
se abre con un `GET` del navegador o de la app.

**Fuente o regla:** el contrato de C-08 y el criterio de que las mutaciones no van
por `GET` (un prefetch de cliente de correo confirmaría turnos solo).

**Antes** (explore, Eje 4):

> "El mensaje incluye `{PUBLIC_BASE_URL}/public/turnos/{token}/confirmar` … y ya
> cambian el turno a `confirmado`. C-09 solo necesita emitir/recuperar el token."

**Después** (`design.md` D6 y tarea 7.2):

> El mensaje apunta a `{PUBLIC_BASE_URL}/r/{tenant_slug}/confirmar?token=...`; la
> página pública hace el `POST` de C-08 al cargar y muestra el resultado.

#### D4 — La llamada al MCP estaba mal formada

**Gravedad: media.** Bloqueaba la consulta de configuración.

**Cómo se detectó:** la primera llamada devolvió un error de validación del propio
servidor MCP.

**Fuente o regla:** el mensaje de error del tool, que además documenta la convención:
*"Command must be a single verb (letters and underscore, e.g. GET, HGETALL,
SORT_RO); pass subcommands as args."*

**Antes:**

```
redis_command({ command: "CONFIG GET appendfsync" })
-> MCP error -32602: Invalid arguments: Command must be a single verb …
```

**Después:**

```
redis_command({ command: "CONFIG", args: ["GET", "appendfsync"] })
-> ["appendfsync", "everysec"]
```

#### D5 — El roadmap asignaba a C-09 una migración ya usada

**Gravedad: media.** Deriva de numeración con impacto en el apply.

**Cómo se detectó:** cruce de `CHANGES.md` (decía "Migración 011" para C-09) contra
`backend/alembic/versions/`, donde `011_reserva_publica_tokens.py` ya existe y
pertenece a C-08.

**Fuente o regla:** la cadena real de Alembic y la convención de migraciones del repo.

**Antes:** `- Migración 011: tablas notificacion_envio, plantilla …`

**Después:** `- Migración 012: tablas notificacion_envio, plantilla …`, y C-10..C-13
renumerados a 013..016. C-08 pasó además a `[x]` archivado (2026-11-05), que era el
otro dato desactualizado del roadmap.

#### D6 — El puerto documentado del MCP no es el del proyecto

**Gravedad: baja, pero rompe la reproducibilidad.**

**Cómo se detectó:** `mcp-redis-integracion.md` e `investigacionmcp.md` decían
`6380` en 11 lugares (6 y 5 respectivamente), mientras `docker-compose.yml:40`,
`.env:57` y `.env.example:57` publican `6379`. La conexión del MCP solo funcionó al apuntarla a
`redis://localhost:6379/0`.

**Fuente o regla:** la configuración real del proyecto (`docker-compose.yml`,
`.env`) y la respuesta de `redis_health`, que confirma la instancia en 6379.

**Antes:** la ficha documentaba `REDIS_PORT: "6380"` y la config del cliente se armó
con ese puerto → el servidor no encontraba la instancia.
**Después:** la config real del cliente usa `REDIS_URL: redis://localhost:6379/0` →
`redis_health` conectado, 7.4.11, AOF activo.

**Corrección aplicada (2026-11-06):** los dos documentos se corrigieron a `6379` y,
al verificar el paquete instalado, aparecieron dos errores más del mismo bloque de
configuración:

- El servidor lee **solo `REDIS_URL`**; `REDIS_HOST`/`REDIS_PORT`/`REDIS_PASSWORD`
  no existen en `@yawlabs/redis-mcp` (verificado en `dist/` y en el `README` del
  paquete). Con las variables viejas el proceso arranca y muere con
  `REDIS_URL is not set`.
- OpenCode anida los servidores en `mcp.<nombre>` y declara el entorno en
  `environment`; la documentación usaba `mcp.servers.*` y `env` (formato de otro
  cliente).

También se corrigieron los ejemplos de uso: `KEYS` está **bloqueado** por diseño (se
usa `redis_scan`) y `SET`/`DEL`/`EXPIRE` exigen `ALLOW_WRITES=1`, que no está
configurado. Archivos tocados: `mcp-redis-integracion.md`, `investigacionmcp.md` y
`AGENTS.md` (§Integración MCP — Redis).

### 4. Prueba de borde: los límites del MCP en modo lectura

La consigna pide, cuando no se detectan defectos, probar un caso de borde y
documentarlo sin inventar un error. Acá se detectaron defectos, pero la prueba se
hizo igual porque evalúa otro límite: **hasta dónde sirve el MCP cuando la base está
vacía y el servidor es read-only**.

| Comprobación | Resultado | Lectura |
|---|---|---|
| `redis_health` sobre base vacía | responde correctamente, `total_keys 0` | el MCP **observa** estado, no lo crea |
| `redis_advisor` con 0 claves | `sampled_keys 0`, 0 hallazgos | el advisor es **vacuo** sin datos: no distingue "sano" de "sin datos" |
| `redis_scan type="stream"` | 0 streams | no se puede comparar contra un stream real todavía |
| `SET tick:prueba NX EX 60` | bloqueado (`ALLOW_WRITES` no configurado) | no se puede sembrar el escenario del lock desde el chat |
| `redis_command` con verbo compuesto | rechazado por el schema (`^[A-Za-z_]+$`) | la herramienta impone una convención que hay que conocer |

**Conclusión honesta:** el MCP es excelente para **verificar** estado y configuración
en un entorno real, y limitado para **preparar** escenarios cuando la base está vacía
y el servidor es read-only. Por eso la verificación del lock quedó como **tarea 8.2**
del change —ejecutable en el apply, cuando se habilite escritura en la base de
prueba— y no como evidencia inventada de esta preparación.

**Límite adicional del validador:** `openspec validate --strict` dio el change por
válido (y `--all --strict` 10/10) mientras los defectos D2 y D3 seguían presentes en
el explore. El validador chequea la forma de los artefactos, no la coherencia entre
la KB, las specs archivadas y el diseño. La verificación cruzada quedó como tarea 8.3.

### 5. Cómo reproducir la evidencia

```bash
# 1. Conexión: el cliente lee ~/.config/opencode/opencode.json (no el .jsonc)
opencode mcp list            # debe mostrar "redis connected"

# 2. Instancia real del proyecto
docker compose ps redis      # 0.0.0.0:6379->6379/tcp

# 3. Desde el chat del agente (MCP redis)
redis_health
redis_command({ command: "CONFIG", args: ["GET", "appendfsync"] })
redis_command({ command: "CONFIG", args: ["GET", "maxmemory-policy"] })
redis_scan({ match: "tick:*" })
redis_scan({ type: "stream" })
```

### 6. Conclusión

La propuesta B no usa el MCP para "mostrar que está instalado": lo usa para tomar una
decisión que el agente había tomado mal. El MCP desmintió la premisa "Redis con AOF
alcanza como cola" y eso reescribió el eje 1 del change, el rol de Redis en el
diseño y el plan de verificación. Los otros cinco defectos se detectaron cruzando
specs, código y roadmap, no confiando en el validador.

**Saldo:** 6 defectos, los 6 corregidos. Cinco en los artefactos del change y el
sexto (D6) en la documentación de la propuesta B, que se corrigió completa cuando el
usuario habilitó editar todo lo que mencionara Redis.

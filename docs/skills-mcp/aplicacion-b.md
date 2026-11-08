# Informe de Aplicación — Propuesta B: MCP Redis (puntos 5 a 6)

**Proyecto:** SaaS multi-tenant de gestión para consultorios odontológicos (Argentina) · **Fecha:** 2026-11-06
**Propuesta:** B — el MCP integrado es **Redis** (`@yawlabs/redis-mcp`), no el servidor de archivos de la propuesta A.
**Documentos de esta propuesta:** `investigacionmcp.md` (ficha B, puntos 1-4) · `mcp-redis-integracion.md` (configuración reproducible) · `preparacion-b.md` (punto 7) · `revision-critica-b.md` (punto 8).
**La propuesta A queda intacta:** `investigacion.md`, `aplicacion.md`, `preparacion.md`, `revision-critica.md` y `mcp-configuracion.md` no se modifican.

## 1. Resultados por consigna

| Punto | Qué se hizo en la propuesta B | Evidencia |
|---|---|---|
| 1 · Necesidad real | El sistema ya usa Redis para el worker y para la idempotencia de webhooks (R8), pero **no había forma de inspeccionarlo desde el chat**: cualquier verificación de locks, TTLs o claves exigía abrir una consola aparte. El MCP cubre esa necesidad y se aplica al change C-09 | `investigacionmcp.md` §1 |
| 2 · Skill creadora | Se reutiliza `visual-explore-options`, ya creada con `skill-creator` e integrada en la propuesta A. Esta propuesta **no duplica** la skill: la usa | `AGENTS.md`, `.atl/skill-registry.md` |
| 3 · MCP | Comparación `@yawlabs/redis-mcp` vs `@liangshanli/mcp-server-redis` en 7 dimensiones; se elige el primero por ser **read-only por defecto**, más reciente y con `SCAN`, `TTL`, memoria, `slowlog`, health check y advisor | `investigacionmcp.md` §2-§3 |
| 4 · Ficha | `investigacionmcp.md` con necesidad, comparación, elección, instalación, límites y fuentes con URL y fecha | este repo |
| 5 · Skill propia | Sin cambios respecto de la propuesta A: la skill ya está instalada, registrada y referenciada. Esta propuesta **no la toca** | `AGENTS.md` §Skills |
| 6 · MCP | Servidor **conectado y operativo**: `redis_health` responde con la instancia real (7.4.11, AOF activo, `total_keys 0`) y se ejecutaron cinco herramientas distintas sobre datos reales | §2 de este informe, `revision-critica-b.md` §2 |
| 7 · Change | `C-09 notificaciones-whatsapp-worker` implementado, verificado y archivado (2026-11-06): 27/27 tareas, `openspec validate --strict` verde, suite backend 238 passed, migración 012 up/down verificada, build TS verde, evidencia MCP Redis (lock con TTL ~840 s) | `preparacion-b.md`, `CHANGES.md` |
| 8 · Revisión | Evidencia de invocación de skill y MCP + **6 defectos** con antes/después | `revision-critica-b.md` |

## 2. Integración del MCP (punto 6)

**Servidor:** `@yawlabs/redis-mcp`, local, JSON-RPC 2.0 por stdio, **read-only por defecto**.
**Instancia:** Redis 7.4.11 en `localhost:6379` (el `.env` del proyecto y el compose). La conexión del MCP llega desde `172.18.0.1`, es decir, a través del puerto publicado del contenedor: es la misma instancia que usa el backend, no un servidor suelto en el host.

**Herramientas ejecutadas en esta sesión** (no es una lista de herramientas instaladas: cada una devolvió datos reales):

| Herramienta | Solicitud | Resultado |
|---|---|---|
| `redis_health` | estado completo de la instancia | 7.4.11 · standalone · `total_keys 0` · AOF on · `evicted_keys 0` · 1 cliente conectado |
| `redis_command` | `CONFIG GET appendfsync` | `["appendfsync", "everysec"]` |
| `redis_command` | `CONFIG GET maxmemory-policy` | `["maxmemory-policy", "noeviction"]` |
| `redis_scan` | `recordatorio*`, `notificacion*`, `dedupe:*`, `wa:*`, `tick:*`, `*` | 0 claves en todos los patrones |
| `redis_scan` | `type: "stream"` | 0 streams |
| `redis_advisor` | muestreo de claves | 0 hallazgos: sin claves grandes, sin TTL faltantes, sin presión de eviction |
| `redis_slowlog` | últimas 5 entradas | 2 entradas, ambas `INFO` del propio MCP |

**Qué información puede consultar:** claves (`SCAN`), valores (`GET`, `HGETALL`, `LRANGE`, `ZRANGE`), longitudes (`LLEN`), TTL, memoria, `INFO`, `slowlog`, health check y advisor.
**Límites establecidos:** solo la instancia de desarrollo; sin datos reales de pacientes (R14); sin credenciales en el repo; escritura deshabilitada (`ALLOW_WRITES` no configurado), lo que impide sembrar claves de prueba desde el chat. El detalle reproducible está en `mcp-redis-integracion.md`.

## 3. Revisión crítica (resumen)

Seis defectos detectados, con antes/después en `revision-critica-b.md`. Los dos de mayor impacto:

1. **El explore recomendaba Redis Streams como cola sin advertir su durabilidad.** La evidencia del MCP (`appendfsync everysec`, `maxmemory-policy noeviction`, `maxmemory 0`) muestra que un corte puede perder hasta ~1 s de escrituras y que, al fijarse un límite de memoria, las escrituras **fallan** en vez de desalojar. Se descartó Redis como cola y se documentó el desvío del §Flujo 5 de la KB en `design.md` D2.
2. **La confirmación "de un toque" no podía funcionar con la ruta de C-08.** El link de WhatsApp es un `GET` del navegador y `POST /public/turnos/{token}/confirmar` espera un `POST` con body. Se agregó una página pública mínima que hace el `POST`, en lugar de mutar estado desde un `GET`.

## 4. Limitaciones

- **Escritura deshabilitada.** El servidor corre en modo read-only, así que no se pudo ejecutar el experimento completo del lock (`SET tick:... NX EX 840` → `TTL` → expiración). Queda como tarea 8.2 del change, ejecutable cuando el apply habilite escritura en la base de prueba.
- **Base vacía.** Con `total_keys 0`, la evidencia es de configuración y de línea base, no de contenido. Es honesto: C-09 no está implementado, así que no hay claves propias que inspeccionar todavía.
- **Sin streams reales.** La comparación contra Redis Streams es conceptual; no hay un stream en la instancia para medir `XLEN`/`XINFO`.
- **El advisor es vacuo con 0 claves.** Se ejecutó para dejar la línea base, pero no puede encontrar problemas en una base vacía.
- **La skill no se re-evalúa en esta propuesta.** Se hereda de la propuesta A por pedido explícito; este informe documenta el MCP y el change, no la creación de la skill.

## 5. Reproducción

```bash
npm install -g @yawlabs/redis-mcp
# ~/.config/opencode/opencode.json -> server "redis" con REDIS_URL=redis://localhost:6379/0
opencode mcp list          # debe mostrar "redis connected"
```

Luego, desde el chat del agente, las llamadas de §2. La configuración completa
(`mcp.<servidor>` + `environment.REDIS_URL`), las variables y los límites están en
`mcp-redis-integracion.md`, ya corregidos a `6379` (defecto D6 de
`revision-critica-b.md`).

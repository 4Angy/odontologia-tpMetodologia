# Evidencias — Parte B (Skill propia + MCP Redis) — C-09

> Consolidado de la evidencia del TP para el change `c-09-notificaciones-whatsapp-worker`.
> Todo lo que sigue se ejecutó sobre la instancia de desarrollo (`localhost:6379`,
> base `odontologia`), con datos sintéticos (R14). No se commiteó nada (R12).

---

## 1. Invocación de la skill `visual-explore-options`

- **Cuándo:** fase `explore` del change, antes del `/opsx:propose`.
- **Artefacto:** `discovery/explore-c09-notificaciones-whatsapp.md`.
- **Resultado:** 6 ejes (incluido Eje 0 sobre la semántica de "confirmar"), cada uno con ≥2 opciones técnicas, por-qué, cómo se usa, esquema ASCII y pausa de selección del usuario.
- **Decisión final (A en los seis ejes):** acuse sin cambiar estado; fila en DB como cola; constraints en DB; `WhatsAppClient` Protocol + fake; reutilizar token de C-08 con página pública que hace el POST; email como fila encolada.
- **Qué aportó al change:** originó D1, D2, D5, D6, D7 y el delta de `reserva-publica`/`turnos-internos`.

---

## 2. Invocación del MCP `redis` (preparación)

| Herramienta | Solicitud | Resultado | Qué aportó al change |
|---|---|---|---|
| `redis.redis_health` | estado de la instancia de desarrollo | Redis 7.4.11, `standalone`, `total_keys = 0`, AOF on, `noeviction` | justificó D2 (Redis no es cola) y dio la línea base del namespace |
| `redis.redis_command CONFIG GET appendfsync` | durabilidad real | `everysec` | evidencia literal citada en D2 |
| `redis.redis_command CONFIG GET maxmemory-policy` | política de memoria | `noeviction` | evidencia literal citada en D2 |

Lectura: una cola que no debe perder mensajes no puede vivir en un store con `appendfsync=everysec` (hasta ~1 s de escrituras se pierden ante un corte) y `noeviction` (al llenarse la memoria, las escrituras fallan). Por eso la cola durable es la tabla `notificacion_envio` (D2).

---

## 3. Invocación del MCP `redis` (apply, fase 8 — lock del tick, D3)

Disparo determinístico de un solo tick (`run_tick_once.py`, `NOTIFICACIONES_ENABLED=true`) contra el tenant demo. El MCP solo **lee**; la app escribe la clave `tick:notificaciones:{tenant}`.

| Paso | Llamada MCP | Resultado |
|---|---|---|
| Antes | `redis_scan { match: "tick:*" }` | `keys: [], count: 0` |
| Antes | `redis_health` | `total_keys: 0` |
| Disparo | `run_tick_once.py` (un tick) | `{encolados: 0, procesados: 0}` (plantillas inactivas + paciente sin opt-in → solo `omitida`/`plantilla_inactiva`, sin envíos reales) |
| Después | `redis_key_info { key: "tick:notificaciones:tenant-demo" }` | `exists: true`, `type: string`, `ttl_seconds: ~840`, `has_expiry: true` |
| Después | `redis_scan { match: "tick:*" }` | `keys: ["tick:notificaciones:tenant-demo"], count: 1` |
| Después | `redis_health` | `total_keys: 1` |
| Expiración | `redis_key_info` / `redis_scan` / `redis_health` | `exists: false`, 0 claves, `total_keys: 0` |

**Conclusión:** el namespace es exclusivo (`tick:notificaciones:{tenant}`), sin colisión con otros prefijos del proyecto (`dedupe:*`, `provider_msg_id:*`), y el lock expira limpiamente al vencer el TTL. Valida D3 y la fila "borde" de la matriz (dos instancias concurrentes → un solo lock `tick:*`).

---

## 4. Validaciones ejecutadas

| Check | Resultado |
|---|---|
| `openspec validate c-09-notificaciones-whatsapp-worker --strict` | valid |
| `openspec validate --all --strict` | 10/10 passed |
| Suite backend (`pytest`) | 238 passed, 1 skipped |
| Suite frontend (`vitest`) | 57 passed |
| `tsc --noEmit && vite build` | OK (58 módulos) |
| Migración `012_notificaciones` up/down/up | OK contra PostgreSQL 16 |
| `git diff --check` | sin errores |
| `test_c09_core.py` | 8/8 passed (scheduler, sender, webhook, acuse, API/permisos) |

---

## 5. Capturas sugeridas (para adjuntar)

1. Invocación de `visual-explore-options` en el chat (skill cargada) + el archivo `discovery/explore-c09-...md`.
2. Llamada a `redis_health` (preparación) mostrando `total_keys: 0` / AOF `everysec` / `noeviction`.
3. Llamada a `redis_scan tick:*` **antes** (0 claves) y **después** (1 clave).
4. `redis_key_info tick:notificaciones:tenant-demo` con `exists: true` y TTL ~840 s.
5. `redis_health` con `total_keys: 1`.
6. `redis_key_info` final con `exists: false` (expiración).
7. Salida de `openspec validate --strict` ("valid") y `--all --strict` ("10 passed, 0 failed").

> Las imágenes se guardan localmente y se referencian desde este dossier; el texto
> anterior contiene los resultados literales para que la evidencia sea verificable
> sin depender de las capturas.

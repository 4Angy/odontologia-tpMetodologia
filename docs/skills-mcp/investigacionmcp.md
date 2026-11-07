# Ficha de Investigación — Servidor MCP Adicional (Parte B)

**Proyecto:** SaaS multi-tenant de gestión para consultorios odontológicos (Argentina) · **Fecha:** 31/10/2026 · **Actualizado:** 06/11/2026 (configuración verificada contra `@yawlabs/redis-mcp` instalado: `REDIS_URL`, puerto 6379 y modo read-only)
**Relación con la Parte A:** este documento es una propuesta adicional e independiente. No modifica ni reemplaza `investigacion.md` ni el servidor `filesystem` ya configurado.

---

## 1. Necesidad detectada

El proyecto ya cuenta con un servidor MCP de filesystem para leer archivos del repositorio, pero no tiene visibilidad MCP sobre **Redis**, que se usa para:

- Cola de jobs y scheduler de recordatorios (C-9).
- Claves de idempotencia de webhooks (`mp_payment_id`, `provider_msg_id`) para Mercado Pago y WhatsApp (regla dura R8).
- Caja y señas (C-11, C-12).

Se necesita un segundo servidor MCP que permita inspeccionar claves, colas y scheduled jobs desde el chat de OpenCode, sin salir del entorno, para validar cambios que dependen de Redis.

---

## 2. Comparación de dos servidores MCP (mismo dominio, distinto implementación)

Ambos servidores hacen **más o menos lo mismo**: exponen mediante MCP las operaciones de un almacén clave-valor Redis (claves, colas, TTL, pub/sub, idempotencia). La diferencia está en el paquete de npm y sus capacidades específicas.

| Dimensión | **A — `@yawlabs/redis-mcp`** (elegido) | **B — `@liangshanli/mcp-server-redis`** |
|-----------|----------------------------------------|-----------------------------------------|
| **Propósito** | Servidor MCP para Redis con operaciones de datos, exploración de claves (SCAN), inspección de memoria y TTL, slowlog, health check y asesor DBA. **Read-only por defecto.** | Servidor MCP para Redis con operaciones básicas de datos (`GET`, `SET`, `DEL`, `KEYS`) y control de permisos + logs de operaciones. |
| **Capacidades disponibles** | `GET`, `SET`, `DEL`, `KEYS`, `SCAN`, `LLEN`, `LRANGE`, `ZRANGE`, `HGETALL`, `EXPIRE`, `TTL`, `INFO`, inspección de memoria, slowlog, health check, DBA advisor, soporte Valkey. | `GET`, `SET`, `DEL`, `KEYS`, operaciones de lista y conjunto, control de permisos y logs de operaciones. |
| **Compatibilidad con el agente** | Compatible con OpenCode (MCP estándar JSON-RPC 2.0 por stdio/HTTP). | Compatible con OpenCode (MCP estándar JSON-RPC 2.0 por stdio/HTTP). |
| **Requisitos de instalación / conexión** | `npm install -g @yawlabs/redis-mcp`. Una sola variable, `REDIS_URL` (p. ej. `redis://localhost:6379/0`). En dev, puerto **6379**. | `npm install -g @liangshanli/mcp-server-redis`. Variables `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`. En dev, puerto **6379**. |
| **Permisos** | **Read-only por defecto** (más seguro para datos de prueba). Acotable por rol de usuario. | Control de permisos y logs de operaciones. Acotable por rol. |
| **Credenciales** | `REDIS_URL` (contiene usuario y contraseña si la instancia los exige). | `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`. |
| **Posibles costos** | Gratuito, código abierto, publicado 31/10/2026. | Gratuito, código abierto, publicado 25/10/2025. |

---

## 3. Elección justificada

**Se elige `@yawlabs/redis-mcp`.**

**Ventaja clara sobre `@liangshanli/mcp-server-redis`:**
- Es más reciente (31/10/2026 vs 25/10/2025).
- Es **read-only por defecto**, lo que reduce el riesgo de escritura accidental en la base de datos de prueba (respeta mejor los límites del TP).
- Tiene más capacidades de inspección útiles para el proyecto: `SCAN` para explorar claves, `TTL` y `memory inspection` para validar expiración de claves de idempotencia, `slowlog` y `health check` para monitorear el scheduler de recordatorios (C-09).
- Soporta tanto **Redis como Valkey**, manteniendo coherencia con la comparación de la ficha.

---

## 4. Pasos de instalación y configuración

### 4.1 Instalación del servidor

```bash
npm install -g @yawlabs/redis-mcp
```

### 4.2 Configuración del cliente OpenCode

Archivo externo/global (no en el repo): `~/.config/opencode/opencode.json`

```json
{
  "mcp": {
    "redis": {
      "type": "local",
      "command": ["node", "<ruta-absoluta-al-entry-point>/dist/index.js"],
      "environment": {
        "REDIS_URL": "redis://localhost:6379/0"
      }
    }
  }
}
```

> **Formato del cliente:** OpenCode anida los servidores en `mcp.<nombre>` y declara
> el entorno en `environment`. El paquete lee **solo** `REDIS_URL`; no reconoce
> `REDIS_HOST`/`REDIS_PORT`/`REDIS_PASSWORD` por separado. Si la instancia pide
> contraseña, va dentro de la URL: `redis://:password@host:6379/0`.

> **Nota Windows:** usar `node` + ruta absoluta al entry point (no `npx`) para evitar que el shim de Windows parta el path con espacios (`C:\Users\Cara Palida\...`), tal como ya se documentó para el servidor anterior.

### 4.3 Comprobación de conexión

```bash
opencode mcp list
```

Debe aparecer `redis connected`.

### 4.4 Ejecutar una herramienta real

Contra la base de prueba (`localhost:6379`, la instancia del compose). Las
herramientas se invocan por nombre; el comando crudo va por `redis_command` con el
verbo simple y los subcomandos en `args`:

```text
redis_health
  -> 7.4.11 · standalone · total_keys 0 · AOF on · maxmemory_policy noeviction

redis_command({ command: "GET", args: ["mp_payment_id:test123"] })
  -> (nil) si la clave de idempotencia no existe

redis_scan({ match: "recordatorio*" })
  -> keys: []  count: 0
```

> `KEYS` está bloqueado a propósito; la enumeración se hace con `redis_scan`. La
> escritura (`SET`, `DEL`, `EXPIRE`) requiere `ALLOW_WRITES=1` y no está habilitada
> en esta integración: el servidor es read-only.

---

## 5. Información consultable o modificable, y límites para datos de prueba

### Consultable
- Claves existentes (`redis_scan`; `KEYS` está bloqueado).
- Type, TTL, encoding y memoria de una clave (`redis_key_info`).
- Contenido de una clave por tipo (`redis_get`: string, hash, list, set, zset, stream).
- Longitud de colas (`LLEN` vía `redis_command`).
- Información del servidor (`redis_health` / `INFO`: memoria, clientes, política de eviction, persistencia).
- Claves de idempotencia (`mp_payment_id:<id>`, `provider_msg_id:<id>`).

### Modificable (solo en prueba, con `ALLOW_WRITES=1`)
- Crear/actualizar claves de prueba (`SET`, `SETEX` con TTL) por `redis_command`.
- Eliminar claves de prueba (`DEL`).
- **En esta integración la escritura está deshabilitada**: `ALLOW_WRITES` no está definido, así que el servidor solo lee. Habilitarla es una decisión aparte, limitada a la base de prueba, con limpieza posterior para no dejar claves sueltas.

### Límites establecidos para trabajar con datos de prueba
1. **No datos reales de pacientes (regla dura R14):** solo claves y valores sintéticos/demo.
2. **No credenciales en el repo:** si la instancia pide contraseña, va dentro de `REDIS_URL` y ese valor vive solo en el `opencode.json` local o en el entorno; nunca se commitea.
3. **Sin escritura en producción:** el MCP se conecta exclusivamente a la instancia de desarrollo (`localhost:6379`).
4. **Solo lectura en archivos sensibles:** el MCP no gestiona archivos del repositorio.

---

## 6. Fuentes consultadas

| Fuente | URL | Fecha de consulta |
|--------|-----|-------------------|
| MCP Specification | https://modelcontextprotocol.io | 31/10/2026 |
| OpenCode Config (MCP local) | https://opencode.ai/config.json | 31/10/2026 |
| Redis 7 Documentation | https://redis.io/docs | 31/10/2026 |
| @yawlabs/redis-mcp (npm) | https://npm.im/@yawlabs/redis-mcp | 31/10/2026 |
| @liangshanli/mcp-server-redis (npm) | https://npm.im/@liangshanli/mcp-server-redis | 31/10/2026 |
| Repositorio MCP servers (oficial) | https://github.com/modelcontextprotocol/servers | 31/10/2026 |

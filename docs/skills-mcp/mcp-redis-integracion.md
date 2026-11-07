# Integración MCP — Redis (Parte B)

> Documento enlazado desde `README.md`. Configuración externa al repositorio; no se commitean secretos.
> **Actualizado 06/11/2026:** `REDIS_URL` (única variable), puerto 6379 y modo read-only, verificados contra el paquete instalado y la instancia real.

## 1. Requisitos

| Requisito | Detalle |
|-----------|---------|
| Node.js | Necesario para ejecutar el servidor MCP mediante `node`. |
| Servidor MCP de Redis | `npm install -g @yawlabs/redis-mcp` (o paquete comunitario equivalente). |
| Instancia Redis | Corriendo en `localhost:6379`, el puerto que publica `docker-compose.yml` (`REDIS_HOST_PORT=6379` en `.env`). |
| Cliente OpenCode | Con soporte de servidores MCP locales (`opencode mcp list`). |

## 2. Pasos de configuración

### 2.1 Instalación del servidor

```bash
npm install -g @yawlabs/redis-mcp
```

### 2.2 Configuración del cliente OpenCode

La configuración vive en el archivo global del cliente (no en el repositorio):

`~/.config/opencode/opencode.json`

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

> **Nombres de las claves:** OpenCode usa `mcp.<servidor>` (no `mcp.servers.<servidor>`) y `environment` (no `env`). Con `env` el servidor arranca sin `REDIS_URL` y sale con `REDIS_URL is not set`.
>
> **Configuración de ejemplo sin secretos:** `REDIS_URL` es un placeholder de desarrollo local. Si la instancia pide contraseña, la URL lleva el formato `redis://:password@host:6379/0` y ese valor se inyecta por variable de entorno del sistema o por el archivo local del cliente; nunca se commitea.

### 2.3 Comprobación de conexión

```bash
opencode mcp list
```

Resultado esperado: `redis connected` (junto a los demás servidores ya configurados).

### 2.4 Ejecutar una herramienta real

Contra la base de prueba (puerto 6379). El servidor expone herramientas con nombre
propio; un comando crudo va por `redis_command` con el verbo simple y los
subcomandos en `args`:

```text
redis_health
  -> 7.4.11 · standalone · total_keys 0 · AOF on · maxmemory_policy noeviction

redis_command({ command: "GET", args: ["mp_payment_id:test123"] })
  -> (nil) si la clave de idempotencia no existe

redis_scan({ match: "recordatorio*" })
  -> keys: []  count: 0

redis_key_info({ key: "dedupe:test123" })
  -> exists: false; con la clave presente devuelve type, TTL, encoding y memoria
```

> `KEYS` está **bloqueado** por diseño: la enumeración se hace con `redis_scan`
> (cursor-based). Los comandos que mutan (`SET`, `DEL`, `EXPIRE`) exigen
> `ALLOW_WRITES=1`, que no está configurado: el servidor corre en modo read-only y
> por eso la siembra de claves de prueba queda fuera de esta integración.

## 3. Variables de entorno necesarias

| Variable | Descripción | Ejemplo | Sensible |
|----------|-------------|---------|----------|
| `REDIS_URL` | Cadena de conexión completa (**obligatoria**) | `redis://localhost:6379/0` | Sí si incluye contraseña |
| `ALLOW_WRITES` | `1`/`true` habilita un conjunto curado de comandos que mutan | (sin definir) | No |
| `REDIS_COMMAND_TIMEOUT_MS` | Timeout por comando | `10000` | No |
| `REDIS_CONNECT_TIMEOUT_MS` | Timeout de conexión TCP | `10000` | No |
| `REDIS_MAX_KEYS` | Tope de claves/elementos devueltos por una lectura | `1000` | No |

> El servidor **no** lee `REDIS_HOST`, `REDIS_PORT` ni `REDIS_PASSWORD` por separado:
> todo va dentro de `REDIS_URL` (`redis://:password@host:6379/0`). Si `REDIS_URL`
> falta, el proceso termina al arrancar con `REDIS_URL is not set`.

## 4. Solución de problemas de instalación

| Problema | Causa probable | Solución |
|----------|----------------|----------|
| El servidor no arranca en Windows | El shim `npx.cmd` parte el path con espacios (`C:\Users\Cara Palida\...`). | Usar `node` + ruta absoluta al entry point del servidor (no `npx`). |
| `REDIS_URL is not set` y el proceso termina | El cliente lanzó el servidor sin la variable: `env` en lugar de `environment`, o `mcp.servers` en lugar de `mcp`. | Declarar `REDIS_URL` dentro de `environment` en `mcp.redis`. |
| `redis connected` no aparece en `opencode mcp list` | Ruta incorrecta en `command` o `opencode.json` mal formado. | Verificar que `<ruta-absoluta>` apunte a `dist/index.js` y que el JSON sea válido. |
| No se pueden ejecutar herramientas | El servidor no está corriendo o la URL no apunta a la instancia. | Confirmar que Redis esté en `localhost:6379` (`docker compose ps redis`) y que `REDIS_URL` use ese puerto. |
| `KEYS is blocked` | `KEYS` está fuera del allowlist a propósito. | Usar `redis_scan` con `match` y cursor. |
| `<CMD> mutates state and is blocked` | `ALLOW_WRITES` no está definido (modo read-only). | Es el comportamiento esperado; para escribir en la base de prueba, definir `ALLOW_WRITES=1`. |

## 5. Ubicación de la configuración

- **Externa/global:** `~/.config/opencode/opencode.json` (fuera del repositorio).
- **Cómo reproducirla:** copiar el bloque JSON de §2.2 dentro de `mcp` en ese archivo (clave `redis`), ajustando `<ruta-absoluta>` a la ubicación real del entry point instalado por `npm`.

## 6. Propósito, capacidades, momento de uso y límites

| Ítem | Descripción |
|------|-------------|
| **Propósito** | Inspeccionar claves y estado de Redis para validar idempotencia de webhooks (R8) y el estado de notificaciones (C-09) sin salir del chat. |
| **Herramientas disponibles** | `redis_health`, `redis_scan`, `redis_key_info`, `redis_get`, `redis_command`, `redis_slowlog`, `redis_advisor`. La lectura siempre está habilitada; la escritura requiere `ALLOW_WRITES=1`. |
| **Capacidades que se usarán** | `SCAN` y `redis_key_info` para localizar claves y TTL; `redis_get` para leer valores por tipo; `redis_command` con verbos de lectura (`GET`, `HGETALL`, `LRANGE`, `ZRANGE`, `LLEN`, `INFO`); `redis_health` y `redis_slowlog` para estado. |
| **Momento de uso** | Durante la preparación e implementación de changes que usen Redis (C-9, C-11, C-12). |
| **Límites de acceso** | Solo base de datos de prueba (`localhost:6379`, la instancia del compose); nunca producción. No almacenar datos reales de pacientes (R14). No credenciales en el repo. |
| **Tipo de documentación** | Integración MCP (no se registra como skill). |

# Ficha de Investigación — Servidor MCP Adicional (Parte B)

**Proyecto:** SaaS multi-tenant de gestión para consultorios odontológicos (Argentina) · **Fecha:** 31/10/2026  
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
| **Requisitos de instalación / conexión** | `npm install -g @yawlabs/redis-mcp`. Variables `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`. Puerto 6380 en dev. | `npm install -g @liangshanli/mcp-server-redis`. Variables `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`. Puerto 6380 en dev. |
| **Permisos** | **Read-only por defecto** (más seguro para datos de prueba). Acotable por rol de usuario. | Control de permisos y logs de operaciones. Acotable por rol. |
| **Credenciales** | `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`. | `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`. |
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
    "servers": {
      "redis": {
        "type": "local",
        "command": ["node", "<ruta-absoluta-al-entry-point>/dist/index.js"],
        "env": {
          "REDIS_HOST": "localhost",
          "REDIS_PORT": "6380",
          "REDIS_PASSWORD": ""
        }
      }
    }
  }
}
```

> **Nota Windows:** usar `node` + ruta absoluta al entry point (no `npx`) para evitar que el shim de Windows parta el path con espacios (`C:\Users\Cara Palida\...`), tal como ya se documentó para el servidor anterior.

### 4.3 Comprobación de conexión

```bash
opencode mcp list
```

Debe aparecer `redis connected`.

### 4.4 Ejecutar una herramienta real

Contra la base de prueba (puerto 6380 según `.env`):

```bash
# Listar claves existentes
redis KEYS '*'

# Verificar idempotencia de un webhook MP (regla dura R8)
redis GET mp_payment_id:test123

# Inspeccionar cola de recordatorios programados (C-9)
redis ZRANGE recordatorios:programados 0 -1 WITHSCORES
```

---

## 5. Información consultable o modificable, y límites para datos de prueba

### Consultable
- Claves existentes (`KEYS`, `SCAN`).
- Contenido de una clave (`GET`, `HGETALL`, `LRANGE`, `ZRANGE`).
- Longitud de colas (`LLEN`).
- TTL de claves (`TTL`).
- Información del servidor (`INFO`: memoria, clientes conectados, eviction policy).
- Claves de idempotencia (`mp_payment_id:<id>`, `provider_msg_id:<id>`).

### Modificable (solo en prueba)
- Crear/actualizar claves de prueba (`SET`, `SETEX` con TTL).
- Eliminar claves de prueba (`DEL`).
- Siempre dentro de una transacción con `ROLLBACK` o limpieza posterior, para no dejar basura en la base de prueba.

### Límites establecidos para trabajar con datos de prueba
1. **No datos reales de pacientes (regla dura R14):** solo claves y valores sintéticos/demo.
2. **No credenciales en el repo:** `REDIS_PASSWORD` vive solo en `opencode.json` local o `.env`, nunca se commitea.
3. **Sin escritura en producción:** el MCP se conecta exclusivamente a la instancia de desarrollo (`localhost:6380`).
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

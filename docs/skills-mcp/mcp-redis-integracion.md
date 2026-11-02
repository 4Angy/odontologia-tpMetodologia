# Integración MCP — Redis (Parte B)

> Documento enlazado desde `README.md`. Configuración externa al repositorio; no se commitean secretos.

## 1. Requisitos

| Requisito | Detalle |
|-----------|---------|
| Node.js | Necesario para ejecutar el servidor MCP mediante `node`. |
| Servidor MCP de Redis | `npm install -g @yawlabs/redis-mcp` (o paquete comunitario equivalente). |
| Instancia Redis | Corriendo en `localhost:6380` (puerto definido en `.env` del proyecto). |
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

> **Configuración de ejemplo sin secretos:** los valores arriba son placeholders. `REDIS_PASSWORD` se deja vacío para desarrollo local; en producción se inyecta por variable de entorno y nunca se commitea.

### 2.3 Comprobación de conexión

```bash
opencode mcp list
```

Resultado esperado: `redis connected` (junto a los demás servidores ya configurados).

### 2.4 Ejecutar una herramienta real

Contra la base de prueba (puerto 6380):

```bash
# Listar claves existentes
redis KEYS '*'

# Verificar idempotencia de webhook MP (regla dura R8)
redis GET mp_payment_id:test123

# Inspeccionar cola de recordatorios programados (C-9)
redis ZRANGE recordatorios:programados 0 -1 WITHSCORES
```

## 3. Variables de entorno necesarias

| Variable | Descripción | Ejemplo | Sensible |
|----------|-------------|---------|----------|
| `REDIS_HOST` | Host de la instancia Redis | `localhost` | No |
| `REDIS_PORT` | Puerto de la instancia | `6380` | No |
| `REDIS_PASSWORD` | Contraseña si la instancia la requiere | (vacío en dev) | Sí |

## 4. Solución de problemas de instalación

| Problema | Causa probable | Solución |
|----------|----------------|----------|
| El servidor no arranca en Windows | El shim `npx.cmd` parte el path con espacios (`C:\Users\Cara Palida\...`). | Usar `node` + ruta absoluta al entry point del servidor (no `npx`). |
| `redis connected` no aparece en `opencode mcp list` | Ruta incorrecta en `command` o `opencode.json` mal formado. | Verificar que `<ruta-absoluta>` apunte a `dist/index.js` y que el JSON sea válido. |
| No se pueden ejecutar herramientas | El servidor no está corriendo o el puerto no coincide. | Confirmar que Redis esté en `localhost:6380` y que `REDIS_PORT` coincida. |

## 5. Ubicación de la configuración

- **Externa/global:** `~/.config/opencode/opencode.json` (fuera del repositorio).
- **Cómo reproducirla:** copiar el bloque JSON de §2.2 en el `mcp.servers` de ese archivo, ajustando `<ruta-absoluta>` a la ubicación real del entry point instalado por `npm`.

## 6. Propósito, capacidades, momento de uso y límites

| Ítem | Descripción |
|------|-------------|
| **Propósito** | Inspeccionar claves, colas y scheduled jobs de Redis para validar idempotencia de webhooks (R8) y estado de notificaciones (C-9). |
| **Capacidades que se usarán** | `GET`, `SET`, `KEYS`, `LLEN`, `LRANGE`, `ZRANGE`, `INFO`. |
| **Momento de uso** | Durante la preparación e implementación de changes que usen Redis (C-9, C-11, C-12). |
| **Límites de acceso** | Solo base de datos de prueba (puerto 6380); nunca producción. No almacenar datos reales de pacientes (R14). No credenciales en el repo. |
| **Tipo de documentación** | Integración MCP (no se registra como skill). |

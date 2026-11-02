# Configuración e Integración del MCP

## Estado: CONFIGURADO Y OPERATIVO (verificado 2026-10-19)

> Verificación: `opencode mcp list` muestra **3 servidores conectados** (`context7`, `engram`, `filesystem`) y el handshake JSON-RPC contra el server lee `CHANGES.md` a través del protocolo (ver §5).

### 1. Instalación (completada)

```bash
npm install -g @modelcontextprotocol/server-filesystem
```
Resultado: 12 paquetes añadidos correctamente. Paquete: `@modelcontextprotocol/server-filesystem@2.0.0`.

### 2. Configuración del cliente (completada)

El cliente lee **`~/.config/opencode/opencode.json`** (no el `.jsonc`). La entrada de `filesystem` vive ahí:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "filesystem": {
        "type": "local",
        "command": [
          "node",
          "C:\\Users\\Cara Palida\\AppData\\Roaming\\npm\\node_modules\\@modelcontextprotocol\\server-filesystem\\dist\\index.js",
          "C:\\Users\\Cara Palida\\Documents\\projects\\odontologia-tpMetodologia"
        ]
      }
    }
  }
}
```

> **Por qué `node` + ruta absoluta y no `npx`:** el shim `npx.cmd` de Windows re-escapa mal los argumentos y **parte el path del workspace en el espacio** (`C:\Users\Cara Palida` + `Palida\Documents\...`). El server arrancaba y moría con `Error: None of the specified directories are accessible`. Invocando `node` con el entry point absoluto, el argumento llega íntegro.

### 3. Comprobación de conexión (completada)

```bash
opencode mcp list
```
```
●  ✓ context7  connected
●  ✓ engram    connected
●  ✓ filesystem connected
     node C:\Users\Cara Palida\AppData\Roaming\npm\node_modules\@modelcontextprotocol\server-filesystem\dist\index.js C:\Users\Cara Palida\Documents\projects\odontologia-tpMetodologia
└─ 3 server(s)
```

Desde el cliente, las herramientas quedan disponibles como `mcp.filesystem.*`:
`list_directory`, `read_file`, `read_text_file`, `read_media_file`, `read_multiple_files`, `write_file`, `edit_file`, `create_directory`, `list_directory_with_sizes`, `directory_tree`, `move_file`, `search_files`, `get_file_info`, `list_allowed_directories` (14 en total).

### 4. Raíz del proyecto: cliente MCP reutilizable

La instancia que abre el cliente de OpenCode queda rooteada en el **workspace de la sesión**, que no es el repositorio del proyecto. Para consultar el repo con el MCP se incluye un cliente stdio mínimo:

```bash
node docs/skills-mcp/tools/mcp-fs.js "<raiz_del_repo>" list_directory  # argumentos por stdin
node docs/skills-mcp/tools/mcp-fs.js "<raiz_del_repo>" read_text_file '{"path":"<raiz>\\CHANGES.md"}'
```

Habla JSON-RPC 2.0 por stdio contra el mismo server oficial (`initialize` → `tools/list` → `tools/call`) y evita el shim de Windows. **Sólo imprime el resultado de la herramienta** (`tools/call`): las respuestas de `initialize` y de `tools/list` las descarta.

Para ver esas dos respuestas —nombre y versión del server y listado de herramientas— está la sonda `mcp-handshake.js`, que hace el mismo camino por stdio y sí las imprime:

```bash
node docs/skills-mcp/tools/mcp-handshake.js "<raiz_del_repo>"
```

Salida del 2026-10-27:

```
INIT secure-filesystem-server 2.0.0
14 tools: read_file, read_text_file, read_media_file, read_multiple_files, write_file, edit_file, create_directory, list_directory, list_directory_with_sizes, directory_tree, move_file, search_files, get_file_info, list_allowed_directories
READ CHANGES.md -> 34908 chars
```

Las dos salidas (esta y la de `mcp-fs.js`) quedaron registradas en `evidencias/mcp-filesystem-verificacion.txt`.

## Servidor seleccionado

`@modelcontextprotocol/server-filesystem` (oficial de Anthropic)

## Por qué este servidor

- No requiere credenciales ni conexión a internet.
- Ideal para inspeccionar el repositorio del proyecto sin exponer secretos.
- Oficial y estable.
- Se alinea con la restricción del TP de no incluir claves, tokens ni secretos en el repositorio.

## Información consultable

- Estructura de carpetas del proyecto
- Contenido de `CHANGES.md`, `ROADMAP.md`, `AGENTS.md`
- `knowledge-base/` (10 archivos de documentación)
- `openspec/` (specs y changes)

## Límites establecidos

- Solo lectura en carpetas del proyecto.
- No escritura en archivos sensibles.
- No acceso a datos reales de pacientes (usar solo datos ficticios).
- No credenciales ni tokens en el repositorio.

## Archivos relacionados

- `docs/skills-mcp/investigacion.md` — Ficha de investigación completa (puntos 1-4 del TP)
- `docs/skills-mcp/aplicacion.md` — Informe de aplicación (puntos 5-6)
- `docs/skills-mcp/revision-critica-punto-8.md` — Revisión crítica (punto 8), con la evidencia de invocación
- `docs/skills-mcp/tools/mcp-fs.js` — Cliente MCP stdio reutilizable, con la raíz del proyecto
- `AGENTS.md` — Sección de integración MCP y registro de la skill `visual-explore-options`
- `.opencode/skills/visual-explore-options/SKILL.md` — Skill instalada en el proyecto

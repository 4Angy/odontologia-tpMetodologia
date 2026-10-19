# Configuración e Integración del MCP

## Servidor seleccionado

`@modelcontextprotocol/server-filesystem` (oficial de Anthropic)

## Por qué este servidor

- No requiere credenciales ni conexión a internet.
- Ideal para inspeccionar el repositorio del proyecto sin exponer secretos.
- Oficial y estable.
- Se alinea con la restricción del TP de no incluir claves, tokens ni secretos.

## Pasos de instalación y configuración

### 1. Instalación

```bash
npm install -g @modelcontextprotocol/server-filesystem
```

### 2. Configuración del cliente (ejemplo `opencode.jsonc`)

```jsonc
{
  "mcp": {
    "servers": {
      "filesystem": {
        "command": "npx",
        "args": [
          "@modelcontextprotocol/server-filesystem",
          "C:\\Users\\Cara Palida\\Downloads\\odontologia-tpMetodologia-main\\odontologia-tpMetodologia-main"
        ]
      }
    }
  }
}
```

### 3. Comprobación de conexión

Ejecutar una herramienta real del servidor, por ejemplo `mcp.filesystem.list_directory` sobre la raíz del proyecto, para verificar que el servidor responde y lista los archivos.

### 4. Ejecución de al menos una herramienta real

Ejemplo de uso real en el contexto del change `C-01 foundation-setup-decisiones`:

```
mcp.filesystem.read_file("CHANGES.md")
mcp.filesystem.read_file("knowledge-base/04_modelo_de_datos.md")
```

Esto permite al agente consultar la documentación del proyecto y el estado de los changes sin salir del chat.

## Información consultable

- Estructura de carpetas del proyecto
- Contenido de `CHANGES.md`, `ROADMAP.md`, `AGENTS.md`
- `knowledge-base/` (10 archivos de documentación)
- `openspec/` (specs y cambios)

## Límites establecidos

- Solo lectura en carpetas del proyecto.
- No escritura en archivos sensibles.
- No acceso a datos reales de pacientes (usar solo datos ficticios).
- No credenciales ni tokens en el repositorio.

## Archivos relacionados

- `docs/skills-mcp/investigacion.md` — Ficha de investigación completa (puntos 1-4 del TP)
- `AGENTS.md` — Sección de integración MCP y registro de la skill `visual-explore-options`
- `.opencode/skills/visual-explore-options/SKILL.md` — Skill instalada en el proyecto

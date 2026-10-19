# Ficha de Investigación — Skills y MCP

## Proyecto
SaaS multi-tenant de gestión para consultorios odontológicos (Argentina)

## Fecha
2026-10-17

---

## 1. Necesidad detectada

En el flujo de desarrollo del proyecto (Spec-Driven Development con OPSX), cada change requiere una fase de `explore` donde el agente debe presentar opciones técnicas, de arquitectura, de base de datos o de desarrollo antes de avanzar a `design.md`. Actualmente no hay un procedimiento estandarizado para presentar esas opciones de forma sencilla, con esquema visual y pausa obligatoria de selección del usuario.

Además, el agente necesita acceso a documentación externa del stack y a recursos de desarrollo sin salir del entorno de chat. Un servidor MCP permitiría consultar documentación o inspeccionar recursos de desarrollo disponibles.

## 2. Change elegido (para el punto 7)

**Nota**: La selección del change se realiza en el punto 7 del TP. Esta ficha solo declara la intención de usarlo cuando se llegue a esa instancia.

**Cambio candidato**: `C-01 foundation-setup-decisiones` (primer change, sin dependencias)

**Por qué**: Es el change inicial del camino crítico. Resuelve las decisiones bloqueantes PA-01 (WhatsApp) y PA-02 (facturación) que condicionan todo el Sprint 1. La skill `visual-explore-options` puede usarse en su fase `explore` para comparar opciones (proveedor WhatsApp oficial vs gateway artesanal, alcance de facturación v1) y el MCP puede consultar documentación del stack FastAPI/PostgreSQL.

## 3. Skill creadora y diseño de la skill propia

**Skill creadora utilizada**: `skill-creator` (OpenCode)

**Skill propia creada**: `visual-explore-options`

- **Propósito**: Estandarizar la fase `explore` de SDD presentando al menos 2 opciones técnicas con por-qué, cómo se usa y esquema ASCII, pausando por selección del usuario antes de avanzar a `design.md`.
- **Cuándo se activa**: Al iniciar la fase de exploración de un cambio que implique decisiones de arquitectura, frontend, backend, base de datos, APIs o componentes.
- **Entradas necesarias**: Contexto del change (proposal.md o roadmap), alternativas viables evaluadas.
- **Procedimiento**: Identificar al menos 2 alternativas → explicitación práctica (por-qué y cómo) → generación de representación visual/ASCII → presentación clara → pausa de selección obligatoria.
- **Resultado esperado**: Documento de exploración con plantilla exacta, opciones comparables y pausa obligatoria.
- **Criterios de revisión**: Cada opción justifica por-qué y cómo; esquemas ASCII limpios; flujo detenido hasta selección.

**Ubicación**: `C:\Users\Cara Palida\Downloads\odontologia-tpMetodologia-main\odontologia-tpMetodologia-main\.opencode\skills\visual-explore-options\SKILL.md` (y replicas en `.devin/skills/`, `.claude/skills/`, `skills/visual-explore-options.md`)

**Registro en .atl/skill-registry.md**: Pendiente de registro por el orquestador (no versionado).

**AGENTS.md / CLAUDE.md**: Documentado en sección "Skills Disponibles" y reglas duras del proyecto.

---

## 4. Comparación de servidores MCP y elección

### Opción A: Modelo Context Protocol — Filesystem Server (oficial de Anthropic)

- **Propósito**: Permite al agente leer, escribir y explorar archivos y directorios del sistema local.
- **Capacidades**: listar directorios, leer archivos, crear archivos, buscar por patrón, obtener información de archivos.
- **Compatibilidad**: Servidor oficial de Anthropic, compatible con OpenCode V2 y otros clientes MCP.
- **Instalación**: `npx @modelcontextprotocol/server-filesystem` o instalar desde npm.
- **Requisitos**: Node.js, permisos de lectura/escritura en carpetas del proyecto.
- **Credenciales**: Ninguna (local).
- **Costo**: Gratuito, código abierto.
- **Límites**: Solo acceso al sistema de archivos local; no acceso a APIs externas.

### Opción B: Modelo Context Protocol — GitHub Server

- **Propósito**: Permite al agente interactuar con la API de GitHub (repositorios, issues, pull requests, etc.).
- **Capacidades**: Listar repos, crear issues, leer PRs, comentar, etc.
- **Compatibilidad**: Servidor comunitario/oficial, compatible con clientes MCP.
- **Instalación**: `npx @modelcontextprotocol/server-github` o similar.
- **Requisitos**: Token de GitHub (PAT), conexión a internet.
- **Credenciales**: GITHUB_TOKEN requerido.
- **Costo**: Gratuito (API pública de GitHub con límites de rate).
- **Límites**: Requiere credenciales; dependencia de conexión a internet; límites de rate de GitHub API.

### Elección justificada

**Se elige: Filesystem Server (Opción A)**

**Motivos**:
1. No requiere credenciales ni conexión a internet para funcionar.
2. Es ideal para inspeccionar el repositorio del proyecto (archivos de configuración, CHANGES.md, ROADMAP.md, knowledge-base/) sin exponer secretos.
3. Es oficial de Anthropic y estable.
4. Se alinea con la restricción del TP de no incluir claves, tokens ni secretos en el repositorio.

**Información que podrá consultar**: Estructura de carpetas, contenido de archivos de configuración, CHANGES.md, ROADMAP.md, knowledge-base/, archivos de cambios.
**Límites establecidos**: Solo lectura en carpetas de prueba; no escritura en archivos sensibles; no acceso a datos reales de pacientes.

---

## 5. Pasos de instalación y configuración del MCP

```bash
# 1. Instalar el servidor MCP de filesystem
npm install -g @modelcontextprotocol/server-filesystem

# 2. Configurar en el cliente (OpenCode u otro) — ejemplo opencode.jsonc
{
  "mcp": {
    "servers": {
      "filesystem": {
        "command": "npx",
        "args": ["@modelcontextprotocol/server-filesystem", "C:\\Users\\Cara Palida\\Downloads\\odontologia-tpMetodologia-main\\odontologia-tpMetodologia-main"]
      }
    }
  }
}
```

**Comprobación de conexión**: Ejecutar `tools/ls` o equivalente para listar archivos del proyecto vía MCP.
**Ejemplo de herramienta real**: `mcp.filesystem.read_file` para leer `CHANGES.md` o `knowledge-base/04_modelo_de_datos.md`.

**Configuración de ejemplo sin secretos**: Incluida arriba (no hay secretos).

---

## 6. Archivos de la fundación que se prevén actualizar

| Archivo | Modificación | Motivo |
|---------|--------------|--------|
| `AGENTS.md` | Agregar `visual-explore-options` a la tabla de skills disponibles | El agente debe saber que existe y cuándo usarla |
| `AGENTS.md` | Agregar sección de integración MCP (propósito, capacidades, límites) | Documentar el servidor MCP como integración del proyecto |
| `docs/skills-mcp/investigacion.md` | Crear este archivo | Ficha de investigación (Parte 1 del TP) |
| `docs/skills-mcp/aplicacion.md` | Crear en etapa posterior | Informe de aplicación (Parte 2 del TP) |

**Nota**: No se regenera toda la fundación ni se marcan como ejecutadas etapas no realizadas.

---

## 7. Fuentes consultadas

| Fuente | URL | Fecha de consulta | Contenido |
|--------|-----|-------------------|-----------|
| OpenCode V2 Docs — Skills | https://opencode.ai/v2/docs/skills/ | 2026-10-17 | Creación, ubicación, discovery y frontmatter de skills |
| OpenCode V2 Docs — Commands | https://opencode.ai/v2/docs/commands/ | 2026-10-17 | Comandos slash y plantillas de prompt |
| OpenCode V2 Docs — Config | https://opencode.ai/v2/docs/config/ | 2026-10-17 | Configuración global y de proyecto |
| Model Context Protocol — Filesystem Server | https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem | 2026-10-17 | Servidor MCP oficial de filesystem |
| Modelo Context Protocol — Especificación | https://modelcontextprotocol.io | 2026-10-17 | Especificación general de MCP |

---

## 8. Pendientes / No verificados

- [ ] Registro en `.atl/skill-registry.md` (no versionado, resuelto por el orquestador al cargar la skill)
- [ ] Conexión real del servidor MCP en el entorno de ejecución (pendiente de instalación en la máquina del usuario)
- [ ] Ejecución real de una herramienta MCP en el proyecto (pendiente de configuración del cliente)
- [ ] Selección final del change (se realiza en el punto 7 del TP)

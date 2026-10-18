# Informe de Aplicación — Skills y MCP (hasta punto 6 del TP)

## Proyecto
SaaS multi-tenant de gestión para consultorios odontológicos (Argentina)

## Fecha
2026-10-17

## Alcance cumplido (Puntos 1 al 6 del TP)

### Punto 1 — Identificar una necesidad real

**Necesidad**: Estandarizar la fase `explore` de Spec-Driven Development (SDD) para que el agente presente opciones técnicas con por-qué, cómo y esquema visual, y se detenga en pausa obligatoria antes de generar `design.md`.

**Evidencia**: Skill `visual-explore-options` creada con plantilla exacta y pausa obligatoria.

### Punto 2 — Investigar cómo crear una skill

**Investigación**: Se revisó la documentación oficial de OpenCode V2 (skills, commands, config). Se identificó que una skill requiere `SKILL.md` con frontmatter `name` + `description`, ubicado en `~/.config/opencode/skills/`, `.opencode/skills/`, `.claude/skills/` o `.agents/skills/`.

**Evidencia**: Archivos `SKILL.md` creados en las 4 ubicaciones del proyecto y global.

### Punto 3 — Investigar y seleccionar un servidor MCP

**Comparación**: Filesystem Server (oficial Anthropic, sin credenciales, local) vs GitHub Server (requiere token, dependencia de internet).

**Elección**: Filesystem Server.

**Evidencia**: `docs/skills-mcp/investigacion.md` sección 4.

### Punto 4 — Elaborar la ficha de investigación

**Archivo**: `docs/skills-mcp/investigacion.md` (hasta dos páginas, con necesidad, change elegido, skill creadora, comparación MCP, pasos de instalación, archivos de la fundación, fuentes).

**Evidencia**: Archivo creado en `docs/skills-mcp/investigacion.md`.

### Punto 5 — Crear e integrar la skill propia

**Skill creada**: `visual-explore-options`

**Ubicaciones instaladas**:
- `C:\Users\Cara Palida\Downloads\odontologia-tpMetodologia-main\odontologia-tpMetodologia-main\.opencode\skills\visual-explore-options\SKILL.md`
- `...\.devin\skills\visual-explore-options\SKILL.md`
- `...\.claude\skills\visual-explore-options\SKILL.md`
- `...\skills\visual-explore-options.md`
- Global: `C:\Users\Cara Palida\.config\opencode\skills\visual-explore-options\SKILL.md`

**AGENTS.md actualizado**: Tabla de skills disponibles + sección dedicada a `visual-explore-options` + sección de integración MCP.

**Evidencia de uso**: Se generaron 6 pruebas (3 with_skill + 3 baseline) con skill-creator. Resultado: with_skill 15/15 (100%) vs baseline 6/15 (40%) en assertions de plantilla, ASCII, pausa obligatoria y recomendación.

### Punto 6 — Configurar e integrar el MCP

**Servidor**: `@modelcontextprotocol/server-filesystem`

**Configuración**: Documentada en `docs/skills-mcp/mcp-configuracion.md` con comando `npx`, args de carpeta del proyecto, y JSON de ejemplo sin secretos.

**Comprobación**: Documentada como paso pendiente de ejecución real en el entorno del usuario (requiere instalación local de npm).

**Evidencia**: `docs/skills-mcp/mcp-configuracion.md`.

## Archivos modificados y motivo

| Archivo | Motivo |
|---------|--------|
| `AGENTS.md` | Agregar `visual-explore-options` a skills disponibles y sección de integración MCP |
| `docs/skills-mcp/investigacion.md` | Crear ficha de investigación (TP punto 4) |
| `docs/skills-mcp/mcp-configuracion.md` | Crear configuración del MCP (TP punto 6) |
| `.opencode/skills/visual-explore-options/SKILL.md` | Instalar skill en proyecto |
| `.devin/skills/visual-explore-options/SKILL.md` | Replicar skill para Devin |
| `.claude/skills/visual-explore-options/SKILL.md` | Replicar skill para Claude |
| `skills/visual-explore-options.md` | Copia plana en skills/ del proyecto |

## Revisión crítica

**Omisión detectada**: La skill `visual-explore-options` no aparece como entrada de tabla en `.atl/skill-registry.md` porque ese archivo es gestionado por el orquestador (no versionado). Se documentó como pendiente.

**Corrección aplicada**: Se agregó la skill manualmente a la tabla de "Skills Disponibles" en `AGENTS.md` y se documentó la ubicación en todas las rutas de descubrimiento.

## Limitaciones

- El servidor MCP no se pudo ejecutar realmente en este entorno (requiere instalación local de npm y configuración del cliente OpenCode).
- La conexión real y ejecución de una herramienta MCP quedan pendientes para el usuario.
- El registro en `.atl/skill-registry.md` es gestionado por el orquestador y no se versiona.
- La selección del change se realiza en el punto 7 del TP (pendiente).

## Conclusión

Se completaron los puntos 1 al 6 del TP: necesidad identificada, change candidato declarado (`C-01 foundation-setup-decisiones` para el punto 7), skill `visual-explore-options` creada e integrada en el proyecto, servidor MCP seleccionado y documentado, ficha de investigación elaborada, y configuración del MCP documentada. La skill está disponible para cualquier agente que trabaje en el proyecto mediante `@visual-explore-options`.

# Ficha de Investigación — Skills y MCP

**Proyecto:** SaaS multi-tenant de gestión para consultorios odontológicos (Argentina) · **Elaborada:** 2026-10-17 · **Actualizada:** 2026-10-19
**Detalle ampliado:** `aplicacion.md` (puntos 5-6) · `preparacion.md` (punto 7) · `revision-critica.md` (punto 8) · `mcp-configuracion.md` (config del MCP)

## 1. Necesidad detectada

En el flujo Spec-Driven Development con OPSX, cada change exige una fase `explore` donde el agente debe **presentar opciones técnicas antes de escribir `design.md`**. No había procedimiento estandarizado: cada agente comparaba con formato variable y, sobre todo, **no se detenía a esperar la decisión del usuario** — el mayor riesgo de esa fase es decidir por el usuario. Además necesitaba consultar la KB del proyecto **sin salir del chat**.

## 2. Change elegido

**Inicialmente `C-01 foundation-setup-decisiones`** (primer change del camino crítico; resolvía PA-01 y PA-02, que bloqueaban el Sprint 1). **El change preparado en esta TP es `C-02 tenancy-core-models`. Motivo del cambio:** C-01 quedó implementado, verificado y archivado durante esta TP, y el punto 7 exige dejar un change *preparado para implementar*, no implementado ni archivado. C-02 es el siguiente del roadmap (GATE 1, desbloqueado, camino crítico).

## 3. Skill creadora y diseño de la skill propia

**Skill creadora:** `skill-creator` (OpenCode) — fuente oficial <https://opencode.ai/v2/docs/skills/>; requiere cliente con *discovery* de skills (`SKILL.md` con frontmatter `name` + `description`); verificado con OpenCode V2.

**Skill propia `visual-explore-options`.** Propósito: estandarizar la fase `explore` con ≥2 opciones técnicas (por-qué, cómo, esquema visual) y **pausa obligatoria** antes de `design.md`. Cuándo se activa: al iniciar el `explore` de un change con decisiones abiertas. Entradas: contexto del change y alternativas evaluadas. Procedimiento: restricciones duras → ≥2 alternativas comparables → explicitación práctica → esquema ASCII → plantilla exacta → recomendación → **pausa obligatoria**. Resultado esperado: documento con la plantilla exacta y el flujo detenido. Criterios de revisión: cada opción justifica por-qué y cómo; esquemas ASCII limpios (≤10 líneas); flujo detenido.

**Ubicación:** `.opencode/skills/visual-explore-options/SKILL.md` (repo) + réplicas en `.claude/skills/`, `.devin/skills/`, `skills/visual-explore-options.md` + global en `~/.config/opencode/skills/`. Registrada en `.atl/skill-registry.md` y en `AGENTS.md`.

## 4. Comparación de servidores MCP y elección justificada

| | **A — Filesystem Server** (oficial Anthropic) | B — GitHub Server |
|---|---|---|
| Propósito | Leer, escribir e inspeccionar archivos | API de GitHub (issues, PRs) |
| Capacidades | 14 tools de archivos | Issues, PRs, repos, código |
| Compatibilidad | Oficial de Anthropic; verificado en OpenCode V2 | Compatible, requiere token |
| Instalación | `npm i -g @modelcontextprotocol/server-filesystem` | `npx server-github`; PAT |
| Permisos | Archivos, acotable a un directorio raíz | Permisos del token sobre los repos |
| Credenciales | **Ninguna** | PAT |
| Costos | Gratuito, local, sin internet | Gratuito, pero **requiere internet** y expone token |

**Elección: A (Filesystem Server).** No requiere credenciales ni internet; permite inspeccionar el repo —`knowledge-base/`, `CHANGES.md`, `openspec/`— sin exponer secretos; es oficial y estable; cumple la restricción del TP de no incluir claves ni tokens. **Consultable:** carpetas, `CHANGES.md`, `AGENTS.md`, `knowledge-base/` (10 archivos), `openspec/`. **Límites:** sólo lectura; sin escritura en sensibles; sin datos reales de pacientes; sin credenciales en el repo.

## 5. Instalación y configuración del MCP

```bash
npm install -g @modelcontextprotocol/server-filesystem
# ~/.config/opencode/opencode.json (el cliente lee este archivo, NO el .jsonc):
"filesystem": { "type": "local", "command": ["node", "<ruta>/server-filesystem/dist/index.js", "<raiz>"] }
opencode mcp list                                    # comprobar: filesystem connected
node docs/skills-mcp/tools/mcp-handshake.js "<raiz>"  # INIT + lista de tools (14)
node docs/skills-mcp/tools/mcp-fs.js "<raiz>" read_text_file   # herramienta real
```

> Problema resuelto y documentado en `mcp-configuracion.md`: con `npx` falla en Windows si el path tiene espacios.

> **Qué muestra cada comando:** `mcp-handshake.js` imprime `INIT secure-filesystem-server 2.0.0` y la lista de las 14 herramientas del server; `mcp-fs.js` sólo imprime el **resultado** de la herramienta invocada, porque descarta las respuestas de `initialize` y de `tools/list`. Salidas del 2026-10-27 en `evidencias/mcp-filesystem-verificacion.txt`.

## 6. Archivos de la fundación a actualizar

`AGENTS.md` · `.atl/skill-registry.md` · `docs/skills-mcp/` · `.opencode/`, `.claude/`, `.devin/`, `skills/` · `openspec/changes/` · `CHANGES.md` · `.engram/config.json`.

## 7. Fuentes consultadas

| Fuente | URL | Fecha |
|---|---|---|
| OpenCode V2 — Skills / Commands / Config | <https://opencode.ai/v2/docs/skills/> · <https://opencode.ai/v2/docs/config/> | 2026-10-17 |
| MCP — Filesystem Server (oficial) | <https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem> | 2026-10-17 |
| MCP — Especificación general | <https://modelcontextprotocol.io> | 2026-10-17 |
| Schema de config de OpenCode (MCP local) | <https://opencode.ai/config.json> | 2026-10-19 |
## 8. Pendientes / no verificados

Ninguno: registro en `.atl/skill-registry.md` creado; conexión del MCP verificada (`opencode mcp list` + handshake) y ejecución real de herramientas documentada; change final: `C-02`.

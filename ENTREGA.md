# ENTREGA — TP Skills y MCP (Metodología I)

**Proyecto:** SaaS multi-tenant de gestión para consultorios odontológicos (Argentina)
**Fecha de entrega:** 2026-10-19

---

## 1. Integrantes

> **Completar antes de entregar.** Escribí los apellidos tal como deben ir en el nombre del `.zip`.

| Integrante | Contribución principal |
|---|---|
| Apellido1, Nombre | _(completar)_ |
| Apellido2, Nombre | _(completar)_ |
| Apellido3, Nombre | _(completar)_ |

## 2. Enlaces

| Qué | Enlace |
|---|---|
| **Repositorio** | https://github.com/4Angy/odontologia-tpMetodologia |
| **Commit de entrega** | `4ec1cc5` (C-01 implementado) · `c78cdff` (artefactos de C-02) · `d3e6964` (configuración del MCP y limpieza) · `_<hash final>_` _(completar con el commit final)_ |
| **Video de demostración** | _(completar: enlace accesible, máx. 5 minutos)_ |
| **Ficha de investigación** | [`docs/skills-mcp/investigacion.md`](docs/skills-mcp/investigacion.md) · [PDF](docs/skills-mcp/TP-investigacion-puntos-1-a-4.pdf) |
| **Informe de aplicación** | [`docs/skills-mcp/aplicacion.md`](docs/skills-mcp/aplicacion.md) · [PDF](docs/skills-mcp/TP-aplicacion-puntos-5-a-6.pdf) |
| **Informe del punto 7** (change preparado) | [`docs/skills-mcp/preparacion.md`](docs/skills-mcp/preparacion.md) · [PDF](docs/skills-mcp/TP-preparacion-puntos-7.pdf) |
| **Informe del punto 8** (revisión crítica) | [`docs/skills-mcp/revision-critica.md`](docs/skills-mcp/revision-critica.md) · [PDF](docs/skills-mcp/TP-revision-critica-puntos-8.pdf) |
| **Evidencias** | [`docs/skills-mcp/evidencias/`](docs/skills-mcp/evidencias/) |

## 3. Qué contiene esta entrega

| Artefacto | Requisito del TP | Dónde |
|---|---|---|
| Skill propia | Punto 5 | `.opencode/skills/visual-explore-options/SKILL.md` + réplicas en `.claude/`, `.devin/`, `skills/` |
| Registro de la skill | Punto 5 | [`.atl/skill-registry.md`](.atl/skill-registry.md) |
| Instrucciones del agente | Punto 5 y 6 | [`AGENTS.md`](AGENTS.md) §Skills disponibles y §Integración MCP |
| Configuración reproducible del MCP | Punto 6 | [`docs/skills-mcp/mcp-configuracion.md`](docs/skills-mcp/mcp-configuracion.md) |
| Ficha de investigación | Punto 4 | [`docs/skills-mcp/investigacion.md`](docs/skills-mcp/investigacion.md) (2 págs.) |
| Informe de aplicación | Entrega | [`docs/skills-mcp/aplicacion.md`](docs/skills-mcp/aplicacion.md) (2 págs.) |
| Artefactos del change preparado | Punto 7 | `openspec/changes/C-02-tenancy-core-models/` (proposal, design, specs, tasks) |
| Evidencia de invocación y defectos | Punto 8 | [`docs/skills-mcp/evidencias/`](docs/skills-mcp/evidencias/) |

## 4. Reproducir la configuración

Otro integrante debe poder seguir estas pasos y comprobar la disponibilidad de **las dos** herramientas.

### 4.1 La skill

```bash
# La skill está versionada en el repo: no hace falta instalarla para usarla.
# Para instalarla globalmente (fuera del repo), copiar el SKILL.md:
mkdir -p ~/.config/opencode/skills/visual-explore-options
cp .opencode/skills/visual-explore-options/SKILL.md ~/.config/opencode/skills/visual-explore-options/

# Comprobar que el agente la encuentra:
#   - AGENTS.md §Skills disponibles la lista
#   - .atl/skill-registry.md la registra
#   - cargarla en una sesión nueva con:  skill({ id: "visual-explore-options" })
```

### 4.2 El MCP `filesystem`

```bash
npm install -g @modelcontextprotocol/server-filesystem

# En ~/.config/opencode/opencode.json (el cliente lee ESTE archivo, no el .jsonc):
"filesystem": {
  "type": "local",
  "command": [
    "node",
    "<ruta global de npm>/node_modules/@modelcontextprotocol/server-filesystem/dist/index.js",
    "<ruta del repositorio>"
  ]
}

# Comprobar la conexión y ejecutar una herramienta real:
opencode mcp list
node docs/skills-mcp/tools/mcp-fs.js "<ruta del repositorio>" read_text_file
```

> **Problema de instalación resuelto** (documentado en `mcp-configuracion.md`): con `npx` falla en Windows si el path tiene espacios, porque el shim parte el argumento. Invocar `node` con el entry absoluto lo evita.

### 4.3 El MCP `engram` (memoria del proyecto)

```bash
# Ya está atado al repositorio por .engram/config.json; en la config global:
"engram": { "type": "local", "command": ["engram", "mcp"],
            "environment": { "ENGRAM_PROJECT": "odontologia-tpmetodologia" } }

# Comprobar:
engram projects list
engram search "C-01" --project odontologia-tpmetodologia
```

### 4.4 Correr el proyecto

```bash
docker run -d --name odontologia-test-pg \
  -e POSTGRES_USER=odontologia -e POSTGRES_PASSWORD=odontologia \
  -e POSTGRES_DB=odontologia_test -p 55432:5432 postgres:16

cd backend && pip install -r requirements.txt && python -m pytest     # 75 tests
cd frontend && npm install && npm test && npm run typecheck && npm run build   # 10 tests
```

## 5. Empaquetado

El `.zip` se genera con el script del repo (los apellidos se pasan por parámetro):

```bash
powershell -ExecutionPolicy Bypass -File docs/skills-mcp/tools/entrega.ps1 -Apellidos "Apellido1-Apellido2-Apellido3"
```

Genera `TP-Skills-MCP-<Apellidos>.zip` en la raíz, con la ficha, el informe, los PDFs, `ENTREGA.md` y las evidencias.

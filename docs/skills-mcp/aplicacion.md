# Informe de Aplicación — Skills y MCP (hasta punto 6 del TP)

## Proyecto
SaaS multi-tenant de gestión para consultorios odontológicos (Argentina)

## Fecha
2026-10-19

## Alcance cumplido (Puntos 1 al 6 del TP)

### Punto 1 — Identificar una necesidad real

**Necesidad**: Estandarizar la fase `explore` de Spec-Driven Development (SDD) para que el agente presente opciones técnicas con por-qué, cómo y esquema visual, y se detenga en pausa obligatoria antes de generar `design.md`.

**Evidencia**: Skill `visual-explore-options` creada con plantilla exacta y pausa obligatoria. Se usó en el change `C-01 foundation-setup-decisiones` (ver `discovery/explore-c01-foundation-setup-decisiones.md`).

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
- `C:\Users\Cara Palida\Documents\projects\odontologia-tpMetodologia\.opencode\skills\visual-explore-options\SKILL.md`
- `...\.devin\skills\visual-explore-options\SKILL.md`
- `...\.claude\skills\visual-explore-options\SKILL.md`
- `...\skills\visual-explore-options.md`
- Global: `C:\Users\Cara Palida\.config\opencode\skills\visual-explore-options\SKILL.md`

**AGENTS.md actualizado**: Tabla de skills disponibles + sección dedicada a `visual-explore-options` + sección de integración MCP.

**Evidencia de uso**: Se generaron 6 pruebas (3 with_skill + 3 baseline) con skill-creator. Resultado: with_skill 15/15 (100%) vs baseline 6/15 (40%) en assertions de plantilla, ASCII, pausa obligatoria y recomendación.

**Cambio real donde se aplicó**: `C-01 foundation-setup-decisiones` (archivado como `openspec/changes/archive/2026-10-19-C-01-foundation-setup-decisiones/`). El artefacto de explore se generó con la skill: `discovery/explore-c01-foundation-setup-decisiones.md`.

**Decisiones tomadas con la skill (Eje 1 → A, Eje 2 → A, Eje 3 → A, Eje 4 → A, M1 → Postgres 16 real en dev y CI):**
- ADR-001: WhatsApp v1 = `official` (Cloud API de Meta)
- ADR-002: "Facturación" v1 = caja manual, sin comprobante
- ADR-003: Contrato formal de migrabilidad FDI
- Esquema: respetar `0001_cancelacion_turno`, C-02 = `002`, C-07 = ALTER de `turno`
- SQLAlchemy sincrónico + psycopg 3
- Settings con `pydantic-settings`, 14 variables, fail-fast
- Health checks `/health` y `/health/ready`
- Sobre de error `AppError` + handler único
- CI con dos jobs en paralelo + Postgres 16 y Redis 7
- Compose `api` + `worker` + `db` + `redis`
- Frontend: router v6 + api client con `code` RN-XX

### Punto 6 — Configurar e integrar el MCP

**Servidor**: `@modelcontextprotocol/server-filesystem` (oficial de Anthropic)

**Estado**: CONFIGURADO Y OPERATIVO

**Instalación**:
```bash
npm install -g @modelcontextprotocol/server-filesystem
```
Resultado: 12 paquetes añadidos correctamente.

**Configuración del cliente** (`~/.config/opencode\opencode.jsonc`):
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "filesystem": {
        "command": "npx",
        "args": [
          "@modelcontextprotocol/server-filesystem",
          "C:\\Users\\Cara Palida\\Documents\\projects\\odontologia-tpMetodologia"
        ]
      }
    }
  }
}
```

**Comprobación de conexión**: `opencode mcp list` muestra 3 servidores conectados (`context7`, `engram`, `filesystem`). Verificado el 2026-10-19.

**Causa raíz de un fallo previo (documentada en `revision-critica-punto-8.md`, D1)**: la entrada de `filesystem` estaba en `opencode.jsonc` —archivo que el cliente **no lee**— y además usaba `npx`, cuyo shim en Windows parte el path del workspace al contener un espacio (`Error: None of the specified directories are accessible`). El server ahora se invoca con `node` + el entry point absoluto, en el `opencode.json` activo.

**Evidencia**: `docs/skills-mcp/mcp-configuracion.md` actualizado con el estado real, y `docs/skills-mcp/tools/mcp-fs.js` como cliente stdio reutilizable con la raíz del proyecto.

**Evidencia**: `docs/skills-mcp/mcp-configuracion.md` actualizado con estado operativo.

## Archivos modificados y motivo

| Archivo | Motivo |
|---------|--------|
| `AGENTS.md` | Agregar `visual-explore-options` a skills disponibles y sección de integración MCP |
| `docs/skills-mcp/investigacion.md` | Crear ficha de investigación (TP punto 4) |
| `docs/skills-mcp/aplicacion.md` | Crear informe de aplicación (TP punto 5-6, este archivo) |
| `docs/skills-mcp/mcp-configuracion.md` | Crear configuración del MCP (TP punto 6) |
| `.opencode/skills/visual-explore-options/SKILL.md` | Instalar skill en proyecto |
| `.devin/skills/visual-explore-options/SKILL.md` | Replicar skill para Devin |
| `.claude/skills/visual-explore-options/SKILL.md` | Replicar skill para Claude |
| `skills/visual-explore-options.md` | Copia plana en skills/ del proyecto |
| `openspec/changes/archive/2026-10-19-C-01-foundation-setup-decisiones/` | Change C-01 aplicado y archivado (proposal.md, design.md, tasks.md, specs/) |
| `openspec/changes/C-02-tenancy-core-models/` | Punto 7 del TP: artefactos SDD de C-02 (explore + proposal + design + specs + tasks), **preparado para implementar** (no implementado, no verificado, no archivado) |
| `discovery/explore-c02-tenancy-core-models.md` | Punto 7 del TP: artefacto del explore de C-02 generado con la skill `visual-explore-options` |
| `docs/skills-mcp/revision-critica-punto-8.md` | Punto 8 del TP: revisión crítica con evidencia de invocación de skill y de herramienta MCP, y 5 defectos detectados (D1-D5) |
| `docs/skills-mcp/tools/mcp-fs.js` | Punto 8 del TP: cliente MCP stdio reutilizable, con la raíz del proyecto (evita el shim `npx.cmd` con paths con espacios) |
| `docs/skills-mcp/mcp-configuracion.md` | Punto 8 del TP: estado real del servidor, causa raíz del fallo de conexión y su corrección (D1) |

## Revisión crítica

**Omisión detectada**: La skill `visual-explore-options` no aparece como entrada de tabla en `.atl/skill-registry.md` porque ese archivo es gestionado por el orquestador (no versionado). Se documentó como pendiente.

**Corrección aplicada**: Se agregó la skill manualmente a la tabla de "Skills Disponibles" en `AGENTS.md` y se documentó la ubicación en todas las rutas de descubrimiento.

**Limitaciones**:
- La instancia que abre el cliente de OpenCode queda rooteada en el **workspace de la sesión**, que no es el repositorio del proyecto: para consultar el repo con el MCP se usa el cliente stdio de `docs/skills-mcp/tools/mcp-fs.js`, con la raíz del proyecto.
- El registro en `.atl/skill-registry.md` es gestionado por el orquestador y no se versiona.
- El change del punto 7 se declaró en la ficha de investigación (`C-01`) y se **reevaluó a `C-02`** cuando C-01 quedó implementado y archivado; el motivo está documentado en `discovery/explore-c02-tenancy-core-models.md` §0.

## Conclusión

Se completaron los puntos 1 al 6 del TP: necesidad identificada, change candidato declarado (`C-01 foundation-setup-decisiones` para el punto 7), skill `visual-explore-options` creada e integrada en el proyecto, servidor MCP seleccionado e instalado localmente, ficha de investigación elaborada, y configuración del MCP documentada. La skill está disponible para cualquier agente que trabaje en el proyecto mediante `@visual-explore-options`.

## Evidencia de uso de la skill en el change C-01

El artefacto de explore se encuentra en `discovery/explore-c01-foundation-setup-decisiones.md` y fue generado invocando `@visual-explore-options`. El usuario eligió la combinación A + A + A + A con Postgres 16 real en dev y CI. El `design.md` resultante refleja esas decisiones.

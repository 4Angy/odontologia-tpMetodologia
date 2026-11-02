# Informe de Aplicación — Skills y MCP (puntos 5 a 6)

**Proyecto:** SaaS multi-tenant de gestión para consultorios odontológicos (Argentina) · **Fecha:** 2026-10-19
**Detalle ampliado:** `preparacion.md` (punto 7) · `revision-critica.md` (punto 8) · `revision-critica-punto-8*.md` (evidencia) · `mcp-configuracion.md` (config del MCP) · `evidencias/` (registros)

## 1. Resultados por consigna

| Punto | Qué se hizo | Evidencia |
|---|---|---|
| 1 · Necesidad real | Skill para estandarizar el `explore` (comparar opciones y **detenerse** a esperar al usuario) + MCP para consultar la KB sin salir del chat; ambos aplicados al mismo change | `investigacion.md` §1-§2 |
| 2 · Skill creadora | `skill-creator` (OpenCode) instalada y usada; 6 pruebas (3 con skill + 3 baseline) → **con skill 15/15 (100 %) vs. baseline 6/15 (40 %)** | `investigacion.md` §3, §7 |
| 3 · MCP | Filesystem Server vs GitHub Server en 7 dimensiones y elección justificada; configuración y **herramienta real ejecutada** | `investigacion.md` §4, `mcp-configuracion.md` |
| 4 · Ficha | `investigacion.md` (≤2 páginas) con los 7 elementos exigidos y fuentes con URL y fecha | este repo |
| 5 · Skill propia | `visual-explore-options` creada, adaptada e instalada en 4 rutas del repo + global; registrada en `.atl/skill-registry.md`; `AGENTS.md` actualizado | `AGENTS.md`, `.atl/skill-registry.md` |
| 6 · MCP | Servidor **conectado y operativo** (`opencode mcp list` → 3 servidores) + cliente stdio para leer el repo + sonda de handshake (`INIT secure-filesystem-server 2.0.0`, 14 tools) | `mcp-configuracion.md`, `tools/mcp-fs.js`, `tools/mcp-handshake.js` |
| 7 · Change | `C-02 tenancy-core-models` preparado (explore + proposal + design + spec de 13 escenarios + 46 tareas), **sin implementar** | `preparacion.md` |
| 8 · Revisión | Evidencia de invocación de skill y MCP + **8 defectos** con antes/después | `revision-critica.md` |

## 2. Archivos modificados y motivo

| Archivo | Motivo |
|---|---|
| `AGENTS.md` | Skills (cuándo usarla, qué necesita, cómo revisar) e integración MCP (propósito, capacidades, momento de uso, límites) |
| `.atl/skill-registry.md` | **Registro de la skill**: nombre, propósito, ubicación, situaciones de uso |
| `.opencode/`, `.claude/`, `.devin/`, `skills/` | Copias de la skill por agente; el repo queda versionado |
| `docs/skills-mcp/` | Ficha, este informe, config del MCP, informes de los puntos 7-8, **informe de cumplimiento**, herramientas y evidencias |
| `ENTREGA.md` + `tools/entrega.ps1` | Entrega (integrantes, repo, commit) y empaquetado en un `.zip` único |
| `openspec/changes/C-02-tenancy-core-models/` + `discovery/explore-c02-*.md` | Artefactos SDD del change preparado y el artefacto del explore generado con la skill propia |
| `CHANGES.md` | Referencia del change en el roadmap, con la convención y **sin** marcarlo implementado |
| `.engram/config.json` | Ata la memoria del proyecto (MCP engram) a este repositorio |
| `ENTREGA.md` | Entrega del equipo: integrantes, repo, commit y reproducción |

## 3. Revisión crítica

**Ocho defectos detectados y corregidos**, con antes/después en `revision-critica.md`. Los de mayor gravedad:

1. **El MCP filesystem declaraba "OPERATIVO" sin estar conectado.** Causa raíz doble: la entry estaba en `opencode.jsonc` (que el cliente **no lee**) y usaba `npx`, cuyo shim en Windows parte el path con espacios. Corregido con `node` + entry absoluto en el config activo; verificado con `opencode mcp list` y un handshake JSON-RPC.
2. **El spec de C-02 contradecía el contrato de error** ya archivado en `foundation/runtime` (`{code, message, action?}`): pedía "identificar la columna causante", un campo que el envelope no tiene. Verificado que **ninguno de los 24 RN** de la KB cubre ese caso → corresponde el código genérico.
3. **La migración `002` dejaba `slug` nullable** y no contemplaba el seed del slice archivado. Verificado sobre Postgres 16 real que un índice único admite **múltiples NULL**: la unicidad global quedaba sin garantía.
4. **El agente introdujo dos CVE moderados** al agregar `react-router-dom` 6.x; actualizados a 7.18.4 y vitest 5.0.5 → `npm audit` en 0.

Además, una **prueba de borde** sobre los límites del validador: con el defecto 2 presente, `openspec validate --strict` reportaba el change como válido. Por eso la verificación cruzada quedó escrita como tarea del change y no como confianza en la herramienta.

## 4. Limitaciones

- La instancia del MCP filesystem que abre el cliente de OpenCode queda rooteada en el workspace de la sesión, no en el repo: por eso se incluye `tools/mcp-fs.js`, un cliente stdio con la raíz correcta que **sólo imprime el resultado de la herramienta**. Para ver el `INIT` del server y la lista de herramientas está `tools/mcp-handshake.js`, que hace el mismo camino y sí las imprime. `engram` resuelve el proyecto por `.engram/config.json` y por `ENGRAM_PROJECT` en la config del cliente.
- La skill se probó con 6 casos de `skill-creator`; no hay evaluación con usuarios reales de la clínica.
- El change `C-02` está **preparado, no implementado**: su verificación (13 escenarios) queda como tareas con su comando.
## 5. Entrega

`.zip` único `TP-Skills-MCP-Herrera-Zalazar.zip` (por `tools/entrega.ps1`) con la ficha, el informe, los PDFs, `ENTREGA.md` y las evidencias. El video no se graba (decisión del equipo): la evidencia en texto de las invocaciones reales lo reemplaza.

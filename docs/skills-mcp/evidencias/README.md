# Evidencias — TP Skills y MCP

Registros de las **invocaciones reales** de la skill y del MCP, de las verificaciones y de las correcciones. Los archivos .txt son salidas reales de comandos; los skill-creator-*.md son copias literales de la sesión de OpenCode; los demás .md son informes que citan esa evidencia.

| Archivo | Qué demuestra |
|---|---|
| `mcp-filesystem-verificacion.txt` | El servidor MCP `filesystem` está **conectado y operativo**: `opencode mcp list` lo lista como `connected` y un handshake JSON-RPC por el protocolo devuelve el contenido real de `CHANGES.md` y el listado de `knowledge-base/`. |
| `mcp-engram-verificacion.txt` | El MCP `engram` resuelve el proyecto del repositorio (y no otro) y expone las observaciones del trabajo, incluida la resolución por `config` de `.engram/config.json`. |
| `verificacion-openspec.txt` | Estado del flujo SDD: changes activos, specs, `validate --all --strict` y `validate --archived` en verde, y los 4 artefactos de C-02 completos con **0 tareas hechas**. |
| `verificacion-tests.txt` | 75 tests backend contra Postgres 16 real, 10 tests frontend, typecheck sin errores y `npm audit` en 0 vulnerabilidades. |
| `experimento-postgres-null-en-unique.txt` | Experimento que demuestra el defecto D7: un índice `UNIQUE` de PostgreSQL admite **múltiples valores NULL**, así que `slug` nullable dejaba la unicidad global sin garantía. |
| `skill-invocacion.md` | Solicitud, resultado y aportación de la skill `visual-explore-options` en las dos PREPARACIONES (C-01 y C-02), con la pausa obligatoria. |
| `skill-creator-uso.md` | Cómo se usó `skill-creator` para generar `visual-explore-options`: solicitud, qué produjo, qué se hizo a mano y qué no existe. Acredita el punto 5. |
| `skill-creator-pruebas.md` | Las 6 pruebas (3 con skill y 3 baseline), con prompts, salidas y los 30 criterios evaluados; respalda 15/15 vs 6/15. Acredita el punto 5. |
| `defectos-antes-despues.md` | Los 8 defectos detectados en los resultados del agente, con la fuente o regla que permitió corregirlos y el antes/después. |

## Cómo reproducir

```bash
# MCP filesystem
opencode mcp list
node docs/skills-mcp/tools/mcp-handshake.js "<raiz del repo>"
node docs/skills-mcp/tools/mcp-fs.js "<raiz del repo>" read_text_file

# MCP engram
engram projects list
engram search "C-01" --project odontologia-tpmetodologia

# Flujo SDD
openspec validate --all --strict
openspec list --specs

# Tests
cd backend && python -m pytest
cd frontend && npm test && npm run typecheck && npm audit
```

## Capturas

| Grupo | Archivos |
|---|---|
| MCP filesystem — preparación de C-02 | `Captura de pantalla 2026-10-27 203300.png` (20:33:00), `Captura de pantalla 2026-10-27 203344.png` (20:33:44), `Captura de pantalla 2026-10-27 203426.png` (20:34:26), `Captura de pantalla 2026-10-27 203510.png` (20:35:10), `Captura de pantalla 2026-10-27 203531.png` (20:35:31) |
| Exploración de C-02 — opciones y pausa | `Captura de pantalla 2026-10-27 204527.png` (20:45:27) |
| `visual-explore-options` — exploración de C-02 | `Captura de pantalla 2026-10-27 215652.png` (21:56:52), `Captura de pantalla 2026-10-27 215744.png` (21:57:44), `Captura de pantalla 2026-10-27 215803.png` (21:58:03), `Captura de pantalla 2026-10-27 215918.png` (21:59:18), `Captura de pantalla 2026-10-27 215942.png` (21:59:42), `Captura de pantalla 2026-10-27 220222.png` (22:02:22) |

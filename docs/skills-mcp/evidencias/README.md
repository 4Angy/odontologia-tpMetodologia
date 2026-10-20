# Evidencias — TP Skills y MCP

Registros de las **invocaciones reales** de la skill y del MCP, de las verificaciones y de las correcciones. Nada de esto es una transcripción: cada archivo es la salida real de un comando.

| Archivo | Qué demuestra |
|---|---|
| `mcp-filesystem-verificacion.txt` | El servidor MCP `filesystem` está **conectado y operativo**: `opencode mcp list` lo lista como `connected` y un handshake JSON-RPC por el protocolo devuelve el contenido real de `CHANGES.md` y el listado de `knowledge-base/`. |
| `mcp-engram-verificacion.txt` | El MCP `engram` resuelve el proyecto del repositorio (y no otro) y expone las 13 observaciones del trabajo, incluida la resolución por `config` de `.engram/config.json`. |
| `verificacion-openspec.txt` | Estado del flujo SDD: changes activos, specs, `validate --all --strict` y `validate --archived` en verde, y los 4 artefactos de C-02 completos con **0 tareas hechas**. |
| `verificacion-tests.txt` | 75 tests backend contra Postgres 16 real, 10 tests frontend, typecheck sin errores y `npm audit` en 0 vulnerabilidades. |
| `experimento-postgres-null-en-unique.txt` | Experimento que demuestra el defecto D2: un índice `UNIQUE` de PostgreSQL admite **múltiples valores NULL**, así que `slug` nullable dejaba la unicidad global sin garantía. |
| `skill-invocacion.md` | Solicitud, resultado y aportación de la skill `visual-explore-options` en las dos PREPARACIONES (C-01 y C-02), con la pausa obligatoria. |
| `defectos-antes-despues.md` | Los 8 defectos detectados en los resultados del agente, con la fuente o regla que permitió corregirlos y el antes/después. |

## Cómo reproducir

```bash
# MCP filesystem
opencode mcp list
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

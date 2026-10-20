# Consultorio Odontológico SaaS

SaaS multi-tenant para consultorios odontológicos chicos: agenda con recordatorios por WhatsApp,
caja manual con seña por Mercado Pago y ficha de pacientes. Stack: FastAPI + PostgreSQL + Redis + Docker,
React + TypeScript + Vite.

Documentación del dominio: [`knowledge-base/`](knowledge-base/) · Plan de implementación: [`CHANGES.md`](CHANGES.md) ·
Reglas para agentes: [`AGENTS.md`](AGENTS.md) · Entrega del TP: [`ENTREGA.md`](ENTREGA.md)

## Requisitos

- Python 3.12+ · Node.js 20+ y npm
- **PostgreSQL 16** y **Redis 7** (con Docker: `docker compose up -d db redis`)

Los tests del backend corren contra **Postgres 16 real** — cada test usa su propio esquema — porque SQLite
no valida claves foráneas y deja pasar datos inválidos (fue exactamente lo que detectó la revisión del punto 8).
Para el atajo en SQLite: `TEST_DATABASE_URL=sqlite:///:memory: python -m pytest`.

## Clonar y correr los tests

```bash
git clone https://github.com/4Angy/odontologia-tpMetodologia.git
cd odontologia-tpMetodologia
```

### Base de datos de test

```bash
docker run -d --name odontologia-test-pg \
  -e POSTGRES_USER=odontologia -e POSTGRES_PASSWORD=odontologia \
  -e POSTGRES_DB=odontologia_test -p 55432:5432 postgres:16
```

### Backend (75 tests)

```bash
cd backend
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
python -m pytest
```

Se espera: `75 passed`. Los tests deben correrse desde `backend/` (el paquete `app` solo es importable desde ahí).

### Frontend (10 tests + typecheck + build)

```bash
cd frontend
npm install
npx vitest run
npx tsc --noEmit
npm run build
```

Se espera: `10 passed`, typecheck sin errores y build de producción OK.

## Skills y MCP (TP de Metodología I)

| Qué | Dónde | Cómo se usa |
|---|---|---|
| **Skill propia** `visual-explore-options` | [`.opencode/skills/`](.opencode/skills/) (+ réplicas en `.claude/`, `.devin/`, `skills/`) | Estandariza la fase `explore`: ≥2 alternativas comparables, esquema ASCII y **pausa obligatoria** antes de `design.md`. Registro: [`.atl/skill-registry.md`](.atl/skill-registry.md) |
| **Servidor MCP** `filesystem` (oficial Anthropic) | Config global del cliente: `~/.config/opencode/opencode.json` | Permite leer `knowledge-base/`, `CHANGES.md` y `openspec/` sin salir del chat. Cliente stdio reutilizable: [`docs/skills-mcp/tools/mcp-fs.js`](docs/skills-mcp/tools/mcp-fs.js) |
| **Memoria del proyecto** (MCP `engram`) | [`.engram/config.json`](.engram/config.json) + `ENGRAM_PROJECT` en la config del cliente | Persiste decisiones y hallazgos entre sesiones, atado a este repo |

Documentación completa: [`docs/skills-mcp/`](docs/skills-mcp/) —

- [`TP-informe-cumplimiento.pdf`](docs/skills-mcp/TP-informe-cumplimiento.pdf) — **informe para exponer**: mapa de cumplimiento consigna por consigna, las dos incorporaciones, el change preparado, los 8 defectos y la reproducción
- [`investigacion.md`](docs/skills-mcp/investigacion.md) · [PDF](docs/skills-mcp/TP-investigacion-puntos-1-a-4.pdf) — ficha de investigación (puntos 1-4)
- [`aplicacion.md`](docs/skills-mcp/aplicacion.md) · [PDF](docs/skills-mcp/TP-aplicacion-puntos-5-a-6.pdf) — informe de aplicación (puntos 5-6)
- [`preparacion.md`](docs/skills-mcp/preparacion.md) · [PDF](docs/skills-mcp/TP-preparacion-puntos-7.pdf) — change preparado (punto 7)
- [`revision-critica.md`](docs/skills-mcp/revision-critica.md) · [PDF](docs/skills-mcp/TP-revision-critica-puntos-8.pdf) — revisión crítica (punto 8)
- [`mcp-configuracion.md`](docs/skills-mcp/mcp-configuracion.md) — requisitos, instalación, comprobación y solución de problemas
- [`evidencias/`](docs/skills-mcp/evidencias/) — registros de las invocaciones reales

### Comprobar el MCP

```bash
opencode mcp list          # debe mostrar filesystem, engram y context7 como connected
node docs/skills-mcp/tools/mcp-fs.js "<raiz del repo>" list_directory
```

## Estructura

```
backend/    FastAPI + SQLAlchemy (módulos por dominio, Alembic, tests)
frontend/   React + TS + Vite (features, tests)
knowledge-base/  Fuente de verdad del dominio (10 archivos)
discovery/  Investigación de mercado (15 competidores, análisis, informe PDF)
openspec/   Specs y changes (metodología OpenSpec)
docs/skills-mcp/  Ficha, informes, configuración del MCP, herramientas y evidencias
CHANGES.md  Roadmap de 13 changes con dependencias y camino crítico
AGENTS.md   Instrucciones y reglas duras para agentes
.atl/       Registro de skills del proyecto
```

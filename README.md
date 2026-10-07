# Consultorio Odontológico SaaS

SaaS multi-tenant para consultorios odontológicos chicos: agenda con recordatorios por WhatsApp,
caja manual con seña por Mercado Pago y ficha de pacientes. Stack: FastAPI + PostgreSQL + Redis + Docker,
React + TypeScript + Vite.

Documentación del dominio: [`knowledge-base/`](knowledge-base/) · Plan de implementación: [`CHANGES.md`](CHANGES.md) ·
Reglas para agentes: [`AGENTS.md`](AGENTS.md)

## Requisitos

- Python 3.12+
- Node.js 20+ y npm

Los tests usan SQLite en memoria/archivo temporal: **no hace falta PostgreSQL ni Docker** para correrlos.

## Clonar y correr los tests

```bash
git clone https://github.com/4Angy/odontologia-tpMetodologia.git
cd odontologia-tpMetodologia
```

### Backend (34 tests)

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

Se espera: `34 passed`. Los tests deben correrse desde `backend/` (el paquete `app` solo es importable desde ahí).

### Frontend (2 tests + typecheck)

```bash
cd frontend
npm install
npx vitest run
npx tsc --noEmit
```

Se espera: `2 passed` y typecheck sin errores.

## Estructura

```
backend/    FastAPI + SQLAlchemy (módulos por dominio, Alembic, tests)
frontend/   React + TS + Vite (features, tests)
knowledge-base/  Fuente de verdad del dominio (10 archivos)
discovery/  Investigación de mercado (15 competidores, análisis, informe PDF)
openspec/   Specs y changes (metodología OpenSpec)
CHANGES.md  Roadmap de 13 changes con dependencias y camino crítico
AGENTS.md   Instrucciones y reglas duras para agentes
```

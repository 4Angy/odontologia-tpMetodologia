# Backend — Consultorio Odontológico

API FastAPI del monolito modular (DD-03). Un solo deploy: `api` + `worker` + Postgres 16 + Redis 7 (Docker Compose).

## Requisitos

- Python 3.12+ (probado en 3.12 y 3.14)
- Postgres 16 (o Docker) y Redis 7

## Instalación

```bash
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements.txt   # Windows
.venv/bin/pip install -r backend/requirements.txt       # Linux/macOS
```

## Configuración

La configuración se lee **sólo de variables de entorno** y se valida al arrancar: si algo falta o es inválido, la app **no arranca** (fail-fast) con un mensaje que nombra la variable.

Copiá el ejemplo y completalo:

```bash
cp backend/.env.example backend/.env
```

### Variables

14 variables canónicas de dominio (KB `knowledge-base/08_arquitectura_propuesta.md`) + 2 operativas.

| Variable | Descripción | Ejemplo | Sensible |
|---|---|---|---|
| `APP_ENV` | `dev` \| `test` \| `prod`. En `prod` `JWT_SECRET` es obligatoria. | `dev` | N |
| `LOG_LEVEL` | Nivel de logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`). | `INFO` | N |
| `DATABASE_URL` | Conexión Postgres (driver `psycopg` 3). | `postgresql+psycopg://odontologia:odontologia@localhost:5432/odontologia` | Y |
| `REDIS_URL` | Conexión Redis (cola y caché). | `redis://localhost:6379/0` | Y |
| `JWT_SECRET` | Firma de tokens. **Obligatoria fuera de `dev`/`test`.** Mínimo 32 caracteres en `prod`. | (64 hex) | Y |
| `JWT_ACCESS_MIN` | Vigencia del access token, en minutos. | `15` | N |
| `JWT_REFRESH_DAYS` | Vigencia del refresh token, en días. | `7` | N |
| `TENANT_DEFAULT_TZ` | Zona horaria por defecto del tenant. | `America/Argentina/Buenos_Aires` | N |
| `WHATSAPP_PROVIDER` | `official` \| `gateway`. Ver [ADR-001](../../docs/adr/ADR-001-whatsapp-provider.md). | `official` | N |
| `WHATSAPP_API_TOKEN` | Token de la WABA (Cloud API). | (token) | Y |
| `WHATSAPP_PHONE_ID` | ID del número emisor. | `5411...` | N |
| `MP_ACCESS_TOKEN` | Credencial de Mercado Pago (C-12). | `APP_USR-...` | Y |
| `MP_WEBHOOK_SECRET` | Firma de webhooks MP (C-12). | (secreto) | Y |
| `SMTP_URL` | SMTP para el fallback de email (C-09). | `smtp://usuario:clave@smtp:587` | Y |
| `PUBLIC_BASE_URL` | Base de los links públicos y de WhatsApp. | `https://app.ejemplo.com` | N |
| `SEED_DEMO` | Crea el tenant demo. | `false` | N |

### Generar `JWT_SECRET`

```bash
openssl rand -hex 32
```

En `dev`/`test`, si falta, la app arranca con un secreto **efímero por proceso** y avisa por log. En `prod` la app **no arranca**: es una condición de despliegue, no un default.

## Verificación

```bash
cd backend
python -m pytest          # suite completa
python -m pytest -k health  # un subconjunto
```

Los tests corren contra **Postgres 16 real**, no SQLite: cada test usa su propio esquema (fixture compartida en `backend/conftest.py`). La URL sale de `TEST_DATABASE_URL`.

Levantá una base de test (una sola vez):

```bash
docker run -d --name odontologia-test-pg \
  -e POSTGRES_USER=odontologia -e POSTGRES_PASSWORD=odontologia \
  -e POSTGRES_DB=odontologia_test -p 55432:5432 postgres:16
```

```bash
cd backend
python -m pytest          # usa postgresql+psycopg://odontologia:odontologia@localhost:55432/odontologia_test
```

Para usar otra URL: `TEST_DATABASE_URL=postgresql+psycopg://... python -m pytest`. Para el atajo en SQLite: `TEST_DATABASE_URL=sqlite:///:memory:`.

Migraciones (reversibles, R6):

```bash
python -m alembic upgrade head
python -m alembic downgrade -1
python -m alembic upgrade head
```

## Levantar con Docker

Desde la raíz del repo:

```bash
cp .env.example .env    # y completá JWT_SECRET y POSTGRES_PASSWORD
docker compose up -d --build
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

- `GET /health` — liveness. No toca la base ni Redis.
- `GET /health/ready` — readiness. Verifica Postgres y Redis e identifica el componente que falla.

Sólo el servicio `api` aplica migraciones; el `worker` no (si los dos lo hicieran, se pisan).

## Estructura

```
backend/app/
├── main.py          # app, health checks, handlers de error
├── deps.py          # sesión DB, reloj, sondas de readiness
├── core/
│   ├── config.py    # Settings por variables de entorno (fail-fast)
│   ├── db.py        # Base SQLAlchemy compartida
│   ├── errors.py    # sobre {code, message, action?}
│   ├── logging.py   # logging estructurado sin secretos
│   └── security.py  # JWT (auth completa: C-03)
├── modules/
│   ├── agenda/      # turnos (C-06/C-07)
│   ├── pacientes/   # (C-04)
│   ├── cobros/      # (C-11)
│   ├── notificaciones/  # (C-09)
│   └── tenancy/     # (C-02)
├── worker/          # esqueleto sin jobs (C-09)
├── alembic/         # migraciones
└── tests/           # tests del runtime
```

## Reglas duras (AGENTS.md)

`tenant_id` siempre del JWT (R1/R2), DTOs Pydantic v2 con `extra='forbid'` (R3/R4), montos en centavos enteros (R5), migraciones con `downgrade` (R6), datetimes UTC con timezone (R7), idempotencia en webhooks (R8), errores con `code` RN-XX (R9), TDD estricto (R11), datos sintéticos (R14).

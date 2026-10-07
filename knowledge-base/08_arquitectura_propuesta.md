# Arquitectura Propuesta

Todas las decisiones pasan el filtro de la prioridad de calidad confirmada: **costo operativo bajo**.

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|--------|--------------|---------|
| Monolito modular | Backend FastAPI por dominios (agenda, pacientes, caja, notificaciones) | Un deploy, un equipo chico, costo mínimo; se extrae un servicio solo con dolor probado |
| Row-level multi-tenancy | `tenant_id` en toda tabla de negocio + JWT con tenant | Barato y suficiente para consultorios chicos; RLS Postgres como endurecimiento, no como día 1 |
| Cola + scheduler | Recordatorios, lista de espera, webhooks (Redis) | Desacopla proveedores externos falibles del flujo local (RN-GL-03) |
| Webhook-first con idempotencia | MP + WhatsApp inbound | Los pagos/mensajes llegan dos veces; `mp_payment_id`/`provider_msg_id` como claves |
| Idempotency keys en API | Reserva pública y cobros | Doble-clic y reintentos no duplican turnos ni cobros |
| Auditoría por middleware | Mutaciones (quién/cuándo/qué) | Trazabilidad visible como feature (diferenciador C.4-6 del análisis competitivo) |

Lo que explícitamente NO se hace en v1: microservicios, event-sourcing, CQRS, Kubernetes, multi-región.

## Estructura de directorios

```
proyecto/
├── backend/
│   └── app/
│       ├── main.py               # FastAPI app, routers, middlewares (tenant, audit, errors RN-XX)
│       ├── core/                 # config, security (JWT), deps, errors
│       ├── modules/
│       │   ├── agenda/           # turnos, bloqueos, lista_espera, reserva pública (router+service+schemas)
│       │   ├── pacientes/        # ficha, evoluciones, adjuntos, import/export
│       │   ├── cobros/           # señas MP, cobros, caja, deudas
│       │   ├── notificaciones/   # plantillas, worker WhatsApp/email, consumo
│       │   └── tenancy/          # tenants, usuarios, roles, config
│       ├── worker/               # jobs Redis (scheduler + sender)
│       ├── alembic/              # migraciones
│       └── tests/
├── frontend/
│   └── src/
│       ├── features/             # agenda/, pacientes/, caja/, config/
│       ├── shared/               # api client, auth/tenant context, ui
│       ├── pages/                # agenda, paciente, caja, reserva pública (/r/:slug)
│       └── App.tsx + routes
├── docker-compose.yml            # api + worker + postgres + redis (único deploy v1)
└── knowledge-base/
```

## Seguridad

- Autenticación: JWT access 15 min + refresh rotativo 7 días con detección de reuse (RN-AU-02); reset por email con token 1h.
- Autorización: RBAC por roles acumulables en JWT (`recepcion|odontologo|dueno`); middleware de tenant obligatorio; link público por token con expiración (RN-AU-03).
- Validación de input: schemas Pydantic estrictos en borde + validación de teléfono E.164 + adjuntos (tipo/tamaño) + rate-limit en rutas públicas.
- Secrets management: solo env vars / archivo `.env` fuera del repo en dev; en producción secrets del proveedor de deploy (ningún secreto en imágenes ni en la KB). Rotación manual documentada en runbook v1.
- Datos salud: Postgres con backups diarios + cifrado en reposo del proveedor; ley 25.326/26.529: opt-in WhatsApp, minimización de datos, exportación del paciente. **Suposición:** el detalle de adecuación legal fina lo valida un abogado antes del lanzamiento (ver PA en `10_preguntas_abiertas.md` si aplica).

## Variables de entorno

| Variable | Descripción | Ejemplo | Sensible |
|----------|-------------|---------|----------|
| `DATABASE_URL` | Conexión Postgres | `postgresql+asyncpg://u:p@db:5432/odonto` | Y |
| `REDIS_URL` | Conexión Redis | `redis://redis:6379/0` | Y |
| `JWT_SECRET` | Firma de tokens | (generado, 64 hex) | Y |
| `JWT_ACCESS_MIN` / `JWT_REFRESH_DAYS` | Vigencias | `15` / `7` | N |
| `TENANT_DEFAULT_TZ` | Zona horaria | `America/Argentina/Buenos_Aires` | N |
| `WHATSAPP_PROVIDER` | `official` \| `gateway` | `official` | N |
| `WHATSAPP_API_TOKEN` | Token Cloud API o gateway | (según PA-01) | Y |
| `WHATSAPP_PHONE_ID` | Número remitente | `5411...` | N |
| `MP_ACCESS_TOKEN` | Cobro de señas | `APP_USR-...` | Y |
| `MP_WEBHOOK_SECRET` | Firma webhooks MP | (generado) | Y |
| `SMTP_URL` | Fallback email | `smtp://...` | Y |
| `PUBLIC_BASE_URL` | Links públicos/WhatsApp | `https://app.ejemplo.com` | N |
| `SEED_DEMO` | Crea tenant demo | `false` | N |

# Descripción General

## Stack tecnológico

Decidido y confirmado — no se re-evalúa en esta KB salvo que el costo operativo (prioridad de calidad) lo exija.

| Capa | Tecnologías | Versión mínima |
|------|-------------|----------------|
| Backend | Python + FastAPI + SQLAlchemy | Python 3.12, FastAPI 0.110+ |
| Auth | JWT (access + refresh) | — |
| Base de datos | PostgreSQL | 16 |
| Cache / colas / jobs | Redis (cache + cola de jobs + scheduler de recordatorios) | 7 |
| Frontend | React + TypeScript + Vite | React 18, TS 5 |
| Contenedores | Docker + Docker Compose (dev y deploy inicial) | Docker 24 |
| Mensajería v1 | WhatsApp (proveedor por decidir — ver PA-01 en `10_preguntas_abiertas.md`) | — |
| Cobros v1 | Mercado Pago SDK (solo seña) | API vigente 2026 |

**Suposición:** versiones mínimas no confirmadas por el usuario; se fijan por ser LTS/estables a 2026 y se validan en Sprint 1.

## Arquitectura general

```
                 ┌─────────────┐
                 │   Paciente   │  (link reserva + WhatsApp)
                 └──────┬──────┘
                        │ HTTPS / WhatsApp API
┌──────────┐     ┌──────▼──────────────────────┐     ┌──────────────┐
│ Recepción│────▶│  Frontend SPA (React+TS)     │────▶│  Backend API │
│ Odontol. │     │  (Vite, tenant por subdom.) │◀────│  (FastAPI)   │
│ Dueño    │     └─────────────────────────────┘     └──────┬───────┘
└──────────┘                                              │
                                    ┌─────────────┬───────┴────────┐
                                    │ PostgreSQL  │  Redis         │
                                    │ (multi-     │  (cache+colas+ │
                                    │  tenant RL) │   scheduler)   │
                                    └─────────────┴────────────────┘
```

- Monolito modular FastAPI por dominios (agenda, pacientes, caja, notificaciones), no microservicios: el filtro de decisión es **costo operativo bajo** (un solo deploy, un Postgres, un Redis).
- Multi-tenant: un tenant = un consultorio. Aislamiento por `tenant_id` en cada tabla (row-level) + schemas o DB separada solo si un tenant grande lo exige en v2+. **Suposición:** row-level con `tenant_id` obligatorio alcanza para v1; RLS de Postgres como endurecimiento en Sprint 2.
- Jobs de recordatorios/lista de espera en Redis (cola + scheduler); el worker vive en el mismo deploy (otro contenedor del Compose, no infra nueva).
- El backend es propio en parte porque WhatsApp lo exige (webhooks, plantillas, reintentos) — ver `needs_infra: true`.

## Integraciones externas

| Servicio | Propósito | Tipo |
|----------|-----------|------|
| WhatsApp | Recordatorios, confirmación/cancelación, lista de espera | REST + webhooks (API oficial Cloud API) **o** gateway artesanal — POR DECIDIR (PA-01) |
| Mercado Pago | Cobro de seña al reservar; arrastre ante reprogramación | SDK REST + webhooks (solo seña en v1, no cobro online completo) |
| Email (SMTP transaccional) | Fallback de recordatorios + recupero de cuenta | SMTP/API REST |
| (v2+, no v1) AFIP/ARCA | Facturación electrónica | — fuera de v1 |
| (v2+, no v1) Obras sociales/prepagas | Convenios, autorizaciones, liquidaciones | — fuera de v1 |

## API REST

Agrupada por recurso; detalle de contratos en construcción (OpenAPI autogenerado por FastAPI).

| Recurso | Endpoints principales |
|---------|----------------------|
| Auth | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/password-reset` |
| Tenants/usuarios | `GET/PUT /me`, `GET /users`, `POST /users/invite` (roles: recepción/odontólogo/dueño) |
| Pacientes | `CRUD /pacientes`, `GET /pacientes/:id/evoluciones`, `POST /pacientes/import-csv` |
| Agenda | `CRUD /turnos`, `POST /turnos/:id/confirmar\|cancelar\|reprogramar`, `GET /agenda/dia\|semana`, `POST /lista-espera`, reserva pública `POST /public/reservar` |
| Cobros/caja | `CRUD /cobros`, `POST /senias` (MP preference + webhook), `GET /caja/cierre-dia`, `GET /deudas` |
| Notificaciones | `POST /notificaciones/test`, `GET /notificaciones/consumo` (panel de costo WhatsApp), webhooks `POST /webhooks/whatsapp`, `POST /webhooks/mercadopago` |
| Exportación | `GET /export/:recurso.csv` (pacientes, turnos, cobros) |

Convenciones: JSON; errores con `code` trazable a RN-XX cuando aplique (ej. cancelación <24h → `RN-AG-01`); paginación cursor/limit; todo endpoint de negocio exige `tenant_id` del JWT.

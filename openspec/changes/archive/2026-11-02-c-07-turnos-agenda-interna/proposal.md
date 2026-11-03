# Proposal

## Why

El consultorio necesita gestionar turnos internos sin dobles reservas y operar la agenda diaria desde una vista única. C-04 y C-06 ya proporcionan pacientes, profesionales, prestaciones y disponibilidad; C-07 completa el flujo interno antes de habilitar la reserva pública.

## What Changes

- Incorporar creación y gestión tenant-scoped de turnos con acciones explícitas de confirmar, cancelar, reprogramar, marcar presente y marcar ausente.
- Ofrecer vistas internas de agenda por día y semana, con filtros multi-profesional y acciones de gestión diaria.
- Rechazar colisiones concurrentes por profesional, ofrecer hasta tres horarios alternativos y permitir sobreturnos solo con permiso, motivo y auditoría.
- Hacer operativa la reprogramación desde el flujo de cancelación, conservando el manejo de señas para C-12.
- Añadir idempotencia a la creación, controles RBAC y una migración Alembic aditiva y reversible.

## Capabilities

### New Capabilities

- `agenda/turnos-internos`: creación y operación segura de turnos, transiciones de estado y agenda interna.

### Modified Capabilities

- `agenda/cancelacion-turno`: completar la acción de reprogramación ofrecida por el flujo de cancelación y preservar sus contratos de error, auditoría e idempotencia.

## Impact

- Backend FastAPI/SQLAlchemy: dominio, persistencia tenant-scoped, endpoints y migración Alembic.
- Frontend React: agenda día/semana, alta de turnos y acciones diarias.
- Pruebas unitarias, API, integración y concurrencia; sin nuevas dependencias externas.

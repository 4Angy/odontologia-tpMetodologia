# Proposal

## Why

El backend ya contiene profesionales, prestaciones, bloqueos, configuración y la migración `006_catalogo_agenda_base`, pero el frontend aún presenta configuración como placeholder y el slice tiene cobertura acotada para validaciones y tenancy cruzada entre relaciones. Completar C-06 significa cerrar esos gaps y validar la base reutilizable por agenda y reserva, no volver a implementar su CRUD.

## What Changes

- Auditar y probar los endpoints/modelos actuales de profesionales, prestaciones, bloqueos y configuración; completar solo validaciones faltantes, como coherencia tenant/profesional y datetimes aware.
- Añadir pantallas React de profesionales, prestaciones, bloqueos y configuración del consultorio, respetando RBAC y DTOs estrictos.
- Aplicar cancelación global por tenant sin override por prestación; el valor por defecto es 24 horas. Configurar horarios semanales por profesional en la zona horaria del tenant, con bloqueos como excepciones; calcular candidatos cada 30 minutos y exigir la duración completa de la prestación.
- Aplicar antelación mínima global de reserva de 2 horas por tenant, configurable por el dueño; persistir instantes en UTC.
- Completar el seed sintético e idempotente del catálogo que el roadmap promete y validar defaults de configuración.
- No editar la migración existente `006_catalogo_agenda_base`; cualquier cambio de esquema necesario para horarios será una migración forward, aditiva y reversible, sin reutilizar identificadores Alembic.
- Preservar la independencia funcional de C-06 respecto de C-04/C-05. La cadena Alembic actual puede exigir 005 antes de 006 al desplegar, pero no crea una dependencia funcional ni bloquea el trabajo en paralelo.

## Capabilities

### New Capabilities

- `agenda/catalogo-base`: catálogo tenant-scoped de profesionales, prestaciones, bloqueos y configuración base reutilizable por la agenda.

### Modified Capabilities

Ninguna.

## Impact

- Backend existente: `backend/app/modules/agenda/`, `backend/alembic/versions/006_catalogo_agenda_base.py` y seed demo.
- Frontend React: configuración placeholder actual en `frontend/src/pages/index.tsx`; nuevas vistas en `frontend/src/features/agenda/`.
- Pruebas backend/frontend, RBAC, aislamiento multi-tenant, validación temporal y migraciones.
- Dependencia funcional: C-03. C-06 es independiente de C-04/C-05 y puede avanzar en paralelo según CHANGES.md; C-07 la consume.
- La relación secuencial de Alembic con la migración 005 existente es una cuestión técnica pendiente, no una dependencia funcional que esta propuesta resuelva por su cuenta.

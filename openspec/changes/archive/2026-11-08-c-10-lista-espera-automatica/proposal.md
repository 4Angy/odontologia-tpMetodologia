# Proposal

## Why

Hoy un hueco liberado por cancelación queda visible en la agenda, pero no se recupera automáticamente: depende de que recepción recuerde la lista de espera y llame manualmente. Eso pierde facturación recuperable y deja sin trazabilidad el ofrecimiento. C-10 cierra el Flujo 2 del dominio (US-005) reutilizando el motor durable de C-09.

## What Changes

- Nueva capacidad `agenda/lista-espera`: alta y consulta de cola por tenant, máquina de estados `activa|ofrecida|convertida|vencida`, oferta automática al primer elegible con TTL (default 2h), aceptación/declinación por token público, avance al siguiente y auditoría de transiciones.
- Al cancelar un turno en término (interno), el sistema dispara la oferta sincrónica a la primera entrada activa compatible y encola el WhatsApp con plantilla `lista_espera` (Opción A acordada en explore).
- Migración `013_lista_espera`: tabla `lista_espera` + índice `(tenant_id, estado, prioridad)`.
- Frontend: vista de cola auditable para recepción y botón de oferta manual.
- Tests: oferta al primero elegible, TTL vencido pasa al siguiente, aceptar asigna turno y sale de la lista, sin opt-in se salta con motivo registrado.

## Capabilities

### New Capabilities
- `agenda/lista-espera`: gestión de lista de espera y oferta automática de huecos liberados por WhatsApp con TTL.

### Modified Capabilities
- `agenda/cancelacion-turno`: la cancelación en término dispara la oferta automática de lista de espera cuando existe una entrada activa compatible para el hueco liberado.

## Impact

- Backend: nuevo módulo `app/modules/lista_espera` (modelos, repositorio, servicio, router), cambios en `agenda` (cancelación y pago timeout) para disparar la oferta, worker con job de vencimiento.
- Base de datos: migración `013_lista_espera` (Alembic, reversible).
- Notificaciones: reúso de `notificacion_envio` y plantilla `lista_espera` (C-09), sin cambios de contrato.
- Frontend: nueva vista de cola y acciones de aceptar/declinar por token.
- Tokens públicos: nuevos propósitos `waitlist_accept` / `waitlist_decline` (reúso del mecanismo C-08).

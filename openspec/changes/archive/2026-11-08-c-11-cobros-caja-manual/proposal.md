# Proposal

## Why

El consultorio necesita registrar cobros manuales (efectivo, transferencia, MP, otro), ver saldos y deudas por paciente y cerrar la caja del día con totales por medio, sin emitir comprobantes fiscales en v1 (ADR-002). Hoy el módulo `cobros/` está vacío y `CajaPage` es un placeholder, por lo que no hay forma de saber cuánta plata entró ni cuánta falta cobrar. C-11 materializa la épica de cobros y caja manual (US-006 + US-008) y habilita el futuro arrastre de señas de C-12.

## What Changes

- **New models**: `Cobro` (paciente, turno nullable, monto en centavos, medio, concepto, usuario que cobró, fecha) y `CierreCaja` (fecha, totales por medio, observaciones, usuario; inmutable).
- **Saldo derivado**: `saldo_derivado(paciente)` se redefine como `cargos (presupuestos aprobados/aceptados) − pagos (cobros manuales; señas se integran en C-12)`. Nunca se acepta saldo del cliente.
- **Endpoints nuevos**: `CRUD /cobros`, `GET /deudas`, `POST /caja/cierre-dia`, `POST /caja/ajuste` (nota auditada), `GET /caja/cierre-dia`.
- **Inmutabilidad del cierre**: un cierre por `(tenant, fecha)`; no se edita ni borra; los ajustes solo escriben auditoría (y opcionalmente un `Cobro` de concepto `"ajuste"`).
- **Migración 014**: tablas `cobro`, `cierre_caja` con índices `(tenant_id, fecha)` y `(tenant_id, paciente_id)`; constraint de unicidad `(tenant_id, fecha)` para el cierre.
- **Frontend**: pantalla de caja (cobro rápido, deudas ordenadas, cierre del día con totales por medio) reemplazando el placeholder, declarando honestamente que v1 es caja manual sin comprobantes fiscales (RN-CO-01).
- **RBAC**: alta de cobro `recepcion`/`dueno`; cierre y ajuste solo `dueno`.

## Capabilities

### New Capabilities
- `cobros/caja`: registro de cobros manuales, saldo/deuda derivados por paciente, listado de deudas ordenado y cierre de caja diario inmutable con ajustes auditados.

### Modified Capabilities
<!-- No se modifican requirements de specs existentes; el saldo del paciente ya estaba definido como derivado en gestion-pacientes. -->

## Impact

- **Código**: nuevo módulo `app/modules/cobros/` (models, schemas, repository, service, router), registro en `app/main.py`, migración Alembic 014, actualización de `PacienteService.saldo_derivado()` para restar cobros.
- **APIs**: nuevos endpoints bajo `/cobros`, `/deudas`, `/caja/*`; ningún endpoint acepta `saldo` del cliente.
- **Datos**: dos tablas nuevas; no se alteran tablas existentes.
- **Dependencias**: depende de C-04 (pacientes) y C-07 (turnos, por `turno_id` nullable en `cobro`); habilita C-12 (señas MP).
- **Frontend**: nuevo feature `caja` consumiendo los endpoints; reemplazo de `CajaPage` placeholder.
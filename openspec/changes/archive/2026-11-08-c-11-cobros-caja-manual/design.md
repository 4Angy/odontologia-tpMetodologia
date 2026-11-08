# Design

## Context

Ver `proposal.md` para motivación y alcance. El módulo `cobros/` está vacío y la última migración es `012_notificaciones`. Se reutilizan `TenantMixin`, `AuditMixin`, `AwareDateTime`, `registrar_auditoria` y el patrón de módulos (models/schemas/repository/service/router). El saldo de paciente ya se deriva en `PacienteService.saldo_derivado()` sumando presupuestos aprobados/aceptados; C-11 debe restar cobros y dejar hook para señas (C-12).

## Goals / Non-Goals

**Goals:**
- Registrar cobros manuales con auditoría y derivar saldos/deudas por paciente.
- Cerrar la caja del día por medio de pago de forma inmutable.
- Exponer deudas ordenadas por antigüedad o monto.
- Integrar con el frontend reemplazando el placeholder de caja.

**Non-Goals:**
- Comprobantes fiscales / AFIP-ARCA (v2).
- Checkout general o pasarela (solo caja manual).
- Reapertura de cierres o edición de totales.
- Señas MP (C-12), solo se deja el hook en `saldo_derivado`.

## Decisions

### D1 · Saldo con signo positivo = deuda
- **Decisión**: `saldo_derivado = cargos (presupuestos aprobados/aceptados) − pagos (cobros manuales)`. Señas se restan cuando C-12 exista.
- **Rationale**: consistente con `saldo_derivado` actual (suma presupuestos); positivo = "lo que falta cobrar" es la lectura natural para el dueño.
- **Alternativa descartada**: saldo positivo = crédito a favor (invertiría la semántica existente).

### D2 · Cierre inmutable + ajuste solo auditoría
- **Decisión**: `POST /caja/cierre-dia` crea una fila por `(tenant, fecha)` (constraint único). No hay PUT/DELETE. `POST /caja/ajuste` escribe `audit_event` vinculado al `cierre_id`; si trae monto, crea un `Cobro` de concepto `"ajuste"` que afecta el próximo cierre, no el cerrado.
- **Rationale**: cumple RN-CO-04 y permite correcciones trazables sin mutar historia.
- **Alternativa descartada**: reabrir cierre con flag `reabierto_at` (complejidad innecesaria en v1).

### D3 · Ajuste con nota obligatoria y monto opcional
- **Decisión**: body `{ cierre_id, nota (obligatoria), monto_cents? }`.
- **Rationale**: la nota es el requisito de RN-CO-04/RN-GL-02; el monto opcional corrige saldos sin tocar el cierre.

### D4 · Deudas ordenadas
- **Decisión**: `GET /deudas` devuelve `{ paciente_id, nombre, apellido, saldo_cents }` filtrando `saldo > 0`, orden default por antigüedad (deuda más vieja primero), con `?orden=monto|antiguedad`.
- **Rationale**: la antigüedad prioriza cobranza; el parámetro cubre el caso "mayor monto primero".

### D5 · Conciliación por fecha
- **Decisión**: `GET /caja/cierre-dia?fecha=YYYY-MM-DD` (default hoy) devuelve el cierre de esa fecha con totales por medio y la lista de cobros del día; 404 si no existe.
- **Rationale**: permite conciliar un día específico sin paginación.

### D6 · Hook de señas
- **Decisión**: `saldo_derivado` delega los pagos a un método `_pagos_del_paciente(tenant, paciente)` que hoy suma solo `Cobro` y mañana también `Senia` acreditada/aplicada.
- **Rationale**: evita reescribir el cálculo cuando llegue C-12.

### D7 · Persistencia del saldo
- **Decisión**: no persistir `paciente.saldo`; siempre calcular. La columna queda para compatibilidad pero no se escribe.
- **Rationale**: evita drift entre columna y derivado (RN-CO-05).

## Risks / Trade-offs

- [Cobro con fecha de un día ya cerrado] → se permite; el cobro no altera el cierre cerrado y queda para el próximo cierre. Documentar en UI.
- [Borrado de cobro tras cierre] → permitido con auditoría; el cierre histórico no se recalcula. Riesgo de inconsistencia percibida; mitigación: la UI muestra "cobros del día" al conciliar.
- [Señas no integradas hasta C-12] → el saldo puede sobreestimar la deuda si hubo seña; documentado y el hook lo resuelve.
- [RBAC mal asignado] → alta de cobro solo `recepcion`/`dueno`; cierre/ajuste solo `dueno`; tests de RBAC.

## Migration Plan

1. Crear migración `014_cobros_caja` (down_revision `012_notificaciones`) con tablas `cobro` y `cierre_caja`, índices y constraints.
2. Implementar módulo `app/modules/cobros/` (models, schemas, repository, service, router) y registrar en `app/main.py`.
3. Actualizar `PacienteService.saldo_derivado()` para restar cobros.
4. Implementar frontend `caja` y reemplazar `CajaPage`.
5. Tests (API + servicio + migración + RBAC).
6. Rollback: `alembic downgrade -1` elimina las tablas; el módulo deja de registrarse sin afectar otros.

## Open Questions

Ninguna bloqueante. El hook de señas se resuelve en C-12 sin cambiar este diseño.
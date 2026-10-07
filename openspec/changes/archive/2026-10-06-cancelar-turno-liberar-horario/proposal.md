# Proposal — cancelar-turno-liberar-horario

## Why

Recepción necesita cancelar un turno existente y que el horario quede inmediatamente reservable, sin llamadas ni huecos fantasma. Hoy ese flujo no existe como slice implementable: la cancelación vive solo como alcance futuro dentro de `C-07 turnos-agenda-interna` (CHANGES.md). Este primer change entrega ese slice vertical mínimo con regla de antelación y trazabilidad.

Slice huérfano declarado (F1): no existen `Turno`/`Config`/auth (C-02/C-03/C-06/C-07 pendientes). Este change crea el `turno` mínimo + `config` mínima como seed de C-06/C-07, con nota de extensión sin re-migración (C-06/C-07 agregan columnas/tablas sin tocar lo creado aquí).

## What Changes

- `POST /turnos/:id/cancelar` (autenticado, roles con permiso de agenda): cancela un turno en estado `confirmado` o `pendiente_confirmacion`.
  - Valida antelación mínima configurable por tenant (`config.antelacion_cancel_hs`, defecto 24h; RN-AG-01/02). Nombre de columna preciso fijado aquí: `antelacion_cancel_hs` (C-02 dice `antelacion_hs`; vale el nombre de este change). Si `inicio - ahora < antelación` → `409` con `code: RN-AG-01`, mensaje español-AR (RN-GL-01) y `action: {type: "reprogramar", hint: "..."}` documentado como placeholder (reprogramar es C-07; frontend lo muestra deshabilitado/informativo).
  - Orden de validación explícito e inmutable: tenant → existe → permiso → ¿ya cancelado? (`200` idempotente) → terminales (`409`) → antelación (`409`) → motivo (`422`). Segundo POST con motivo distinto se ignora y conserva la primera auditoría.
  - Transición de estado → `cancelado`; "slot libre" = observable: la query de turnos activos por (tenant, profesional, rango) ya no devuelve el turno. El scenario de disponibilidad se mueve a C-07 como dependencia. Hueco dentro de bloqueo sigue no-reservable; colisión por carga manual sin anti-solape = riesgo declarado (RN-AG-03 es C-07).
  - Requiere `motivo` (texto libre corto, obligatorio, 1–500); registra auditoría mínima quién/cuándo/qué (RN-GL-02): `cancelled_by`, `cancelled_at` (UTC), `motivo`.
  - Idempotente ante doble-clic/reintento: cancelar un turno ya `cancelado` devuelve el recurso `200` sin error ni efecto secundario. Concurrencia: `SELECT FOR UPDATE` o update condicional por estado.
  - Rechazos: turno en estado terminal no cancelable (`presente`, `ausente`; `reprogramado` es el turno viejo ya migrado —no un estado cancelable— y se aclara en spec) + turno ya pasado (`inicio < now`) → `409` con `code` trazable; sin/inválido JWT → `403`; turno inexistente o de otro tenant (JWT válido) → `404` indistinguible (RN-AU-01, sin fuga por enumeración).
  - RBAC por unión multi-rol (RN-AU-04): `recepcion` CRUD agenda, `odontologo` R sus turnos, `dueno` todo; usuario con `recepcion+odontologo` cancela cualquiera vía `recepcion`. `profesional.usuario_id` null → `403` con `code` (fallback definido). Disparador paciente por token público = non-goal explícito (llega en C-08).
- Config de antelación: `GET/PUT /config` expone `antelacion_cancel_hs` (entero ≥ 0, solo `dueno` modifica; rige para turnos futuros, no retroactivo — RN-AG-02). UNA antelación global (PA-04): servicio `resolver_antelacion(tenant, prestacion?)` que hoy ignora `prestacion` y es extensible sin cambio de contrato. Config ausente → fallback 24h + log. `antelacion_cancel_hs=0` = cancelable hasta minuto cero.
- Seña no-touch (F4): columna `turno.senia_pendiente_definicion BOOLEAN DEFAULT FALSE`, seteada `TRUE` solo si había seña asociada. Desviación temporal explícita de RN-CO-03 con Owner C-12 (C-12 lee el flag y aplica la política; PA-05 no se resuelve aquí).
- Frontend (slice mínimo): botón Cancelar en el detalle del turno con modal de motivo + confirmación; muestra el error `RN-AG-01` en español-AR con acción "Reprogramar" deshabilitada/informativa (placeholder).
- Non-goals (explícitamente fuera): resto de C-07 (alta de turnos, anti-solape RN-AG-03, sobreturnos RN-AG-04, vistas día/semana, disponibilidad como capability), reserva pública y tokens (C-08), notificaciones WhatsApp (C-09 — este slice no encola ni cancela envíos; recordatorios ya encolados del turno cancelado = deuda registrada para C-09), lista de espera automática (C-10), señas/devoluciones MP (C-12, RN-CO-03/RN-AG-05).

## Capabilities

### New Capabilities

- `agenda/cancelacion-turno`: cancelar un turno con validación de antelación configurable, liberación del slot (observable), estado `cancelado` con trazabilidad y errores con `code` RN-XX en español-AR.

### Modified Capabilities

(none — no hay specs previas; `openspec list --specs` returns empty. Este es el primer change en `openspec/changes/`.)

## Impact

- **Backend**: nuevo endpoint + servicio de cancelación en `backend/app/modules/agenda/` (`AgendaCancelService` + `resolver_antelacion`); migración Alembic con `downgrade` para `turno` mínimo (`cancelled_by`, `cancelled_at`, `motivo`, `senia_pendiente_definicion`) y `config` mínima (`antelacion_cancel_hs DEFAULT 24`) como seed; DTOs Pydantic v2 con `extra='forbid'`.
- **Frontend**: `features/agenda` — botón/modal de cancelación; sin cambios al shell ni a otras vistas.
- **APIs/contratos**: un endpoint nuevo + shape de error `{code: RN-AG-01, message, action: {type, hint}}`; sin breaking changes (no hay API previa).
- **Dependencias/sistemas**: ninguna integración externa (sin WhatsApp, sin MP); dependencias declaradas: C-07 (disponibilidad/alta/anti-solape), C-08 (token público), C-09 (deuda: envíos encolados), C-12 (owner política de seña).

## Open questions (carried, not resolved)

- **PA-04** (knowledge-base/10_preguntas_abiertas.md): resuelta como UNA antelación global + `resolver_antelacion(tenant, prestacion?)` extensible. Ventanas por prestación quedan para C-06/C-07 sin cambio de contrato.
- **PA-05 / RN-CO-03**: no resuelta aquí por diseño (ver F4); Owner C-12.
- **Deuda C-09**: recordatorios ya encolados del turno cancelado no se tocan en este slice; C-09 debe encolar-cancelar o ignorar envíos de turnos `cancelado`.

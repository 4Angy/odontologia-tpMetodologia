# Design — cancelar-turno-liberar-horario

## Context

Primer change del repo (`openspec list` vacío; sin specs previas ni código backend/frontend existente — el repo contiene solo KB, CHANGES.md, discovery y scaffolding OpenSpec). Ver `proposal.md — Why` para la motivación. Restricciones que modelan el diseño: multi-tenancy row-level (R1/R2: todo filtrado por `tenant_id` del JWT), DTOs Pydantic v2 sin exponer modelos (R3/R4), datetimes UTC con timezone (R7), errores con `code` RN-XX en español-AR (R9/RN-GL-01), y alcance recortado que NO implementa C-07 completo (sin alta de turnos, sin anti-solape, sin sobreturnos).

Slice huérfano (F1): C-02/C-03/C-06/C-07 pendientes. Este change crea el `turno` mínimo (id, tenant_id, paciente_id, profesional_id, prestacion_id nullable, inicio/fin timestamptz, estado, cancelled_by/cancelled_at/motivo, senia_pendiente_definicion) + `config` mínima (`tenant_id`, `antelacion_cancel_hs`) como seed; C-06/C-07 extienden sin re-migración de lo creado. Nombre preciso fijado aquí: `antelacion_cancel_hs` (prevalece sobre `antelacion_hs` de C-02/KB-ERD).

## Goals / Non-Goals

**Goals:**

- Slice vertical mínimo e integrable: endpoint de cancelación + validación de antelación + liberación observable del slot + trazabilidad, testeable sin dependencias externas.
- Dejar el contrato de error `RN-AG-01`, la auditoría y `resolver_antelacion` en la forma que C-07/C-08/C-10/C-12 reutilizarán sin reescribir.

**Non-Goals:**

- Alta/listado de turnos, vistas día/semana, disponibilidad como capability, anti-solape (RN-AG-03), sobreturnos (RN-AG-04): quedan para C-07 (la disponibilidad es dependencia, no parte de este slice).
- Reserva pública, tokens, acción del paciente por token público: C-08 (non-goal explícito).
- Notificaciones: C-09. Este slice no encola ni cancela envíos (deuda C-09 registrada).
- Lista de espera automática (C-10); señas/devoluciones (C-12). La seña se deja intacta por diseño (ver Decisiones).

## Decisions

1. **Endpoint dedicado `POST /turnos/:id/cancelar` con body `{motivo}`** (en vez de `PATCH /turnos/:id {estado}`).
   - Rationale: transición de estado con validación y efectos (antelación, auditoría, idempotencia) merece operación explícita; evita que un PATCH genérico saltee RN-AG-01. Alternativa descartada: PATCH genérico — más flexible pero permite estados inválidos y complica el permiso por transición.
2. **Servicio `AgendaCancelService.cancel(tenant_id, turno_id, user, motivo, now_utc)` puro en dominio, adaptador HTTP fino + `resolver_antelacion(tenant, prestacion?)`.**
   - Rationale: la regla de antelación y la máquina de estados son testeables sin HTTP/DB; el router solo resuelve tenant del JWT (R2), valida DTO y mapea errores a `{code, message, action}`. `resolver_antelacion` implementa PA-04 (UNA antelación global; hoy ignora `prestacion`, extensible sin cambio de contrato). Alternativa descartada: lógica en el router — imposible de reutilizar en C-08 (cancelación pública por token) y C-10.
3. **Antelación como `config.antelacion_cancel_hs` (int ≥ 0, default 24), comparación en UTC, límite inclusivo; `0` = hasta minuto cero; config ausente → fallback 24h + log.**
   - Rationale: RN-AG-02 exige configurable por tenant y no retroactivo; comparar `inicio - now_utc >= antelacion` en UTC evita bugs de tz (`America/Argentina/Buenos_Aires` sin DST, pero el servidor corre en UTC — R7). Se crea el mínimo de `config` en este slice si C-06 no existe. Alternativa descartada: constante quemada 24h — viola RN-AG-02 y PA-04.
4. **Cancelación = transición a `cancelado` + columnas `cancelled_by/cancelled_at/motivo`, sin borrar la fila ni mover el slot a otra tabla. "Slot libre" = observable (la query de activos por tenant/profesional/rango ya no devuelve el turno).**
   - Rationale: borrar rompería auditoría RN-GL-02 y la futura conciliación de seña. El observable evita prometer una API de disponibilidad que es C-07. Requiere migración Alembic con `downgrade` (R6). Alternativa descartada: tabla `turno_cancelado` separada — complica queries de agenda y auditoría.
5. **Idempotencia por estado, no por key externa + orden de validación inmutable + concurrencia con lock.**
   - Orden: tenant → existe → permiso → ¿ya cancelado? (`200`, conserva primera auditoría, ignora motivo nuevo) → terminales (`409`) → antelación (`409` RN-AG-01) → motivo (`422`). Rationale: el reintento/doble-clic llega al mismo `turno_id`; si ya está `cancelado` se devuelve `200` sin re-validar antelación ni duplicar auditoría. Motivo último implica que un 409 de antelación precede al 422 de motivo (decisión explícita del explore). Concurrencia: transacción con `SELECT … FOR UPDATE` o update condicional por estado; el segundo concurrente cae en idempotencia. Alternativa descartada: header `Idempotency-Key` — sobrediseño para una transición idempotente por naturaleza.
6. **Seña intacta + `turno.senia_pendiente_definicion BOOLEAN DEFAULT FALSE` solo si había seña asociada.**
   - Rationale: mover/devolver seña es RN-CO-03/PA-05 (C-12) con política configurable aún abierta; tocarla aquí anticiparía una decisión de producto. Desviación temporal explícita de RN-CO-03 con Owner C-12 (C-12 lee el flag y aplica `no_devuelve|devuelve_50|devuelve_100` / saldo a favor). Sin seña asociada el flag queda `FALSE`.
7. **Error 409 lleva `action: {type: "reprogramar", hint: "..."}` como placeholder documentado.**
   - Rationale: reprogramar es C-07; el shape deja el contrato estable sin prometer la capability. Frontend lo renderiza deshabilitado/informativo. Alternativa descartada: omitir `action` — rompería el contrato que C-07 espera reutilizar.
8. **RBAC por unión (RN-AU-04) + fallback null + códigos HTTP precisos.**
   - `recepcion` CRUD agenda; `odontologo` R sus turnos (`turno.profesional.usuario_id == user.id`); `dueno` todo. Unión: `recepcion+odontologo` cancela cualquiera vía `recepcion`. `profesional.usuario_id` null → `odontologo` no matchea → `403` con `code` (fallback definido, sin 500). HTTP: sin/inválido JWT → `403` (RN-AU-01: sin tenant no hay respuesta útil); turno inexistente o de otro tenant con JWT válido → `404` indistinguible (no fuga por enumeración). Turno pasado (`inicio < now`) → `409` terminal. `reprogramado` no es cancelable porque es el turno viejo ya migrado (aclaración contra la lista confusa).

## Risks / Trade-offs

- [Riesgo] Condición de carrera: dos cancelaciones concurrentes del mismo turno → Mitigación: transacción con `SELECT … FOR UPDATE` o update condicional por estado; el segundo concurrente cae en idempotencia + test de concurrencia en tasks.
- [Riesgo] Reloj/Timezone: comparar naive vs aware rompe el límite 24h → Mitigación: todo UTC aware (R7); `inicio` timestamptz; tests en bordes (exactamente 24h, 23h59m, `antelacion=0`, turno pasado).
- [Riesgo] Alcance creep hacia C-07 (tentación de agregar alta/listado/disponibilidad "para probar") → Mitigación: los tests usan fixtures/seed directos de `Turno`; lo "libre" se verifica por query de estados activos, no por API de disponibilidad (que es dependencia C-07).
- [Riesgo] Hueco en bloqueo sigue no-reservable; carga manual puede colisionar sin anti-solape → Declarado: RN-AG-03 es C-07; este slice no lo impide.
- [Riesgo] Recordatorios ya encolados del turno cancelado siguen vivos → Deuda C-09 aceptada; este slice no toca envíos.
- [Trade-off] `config` + `turno` mínimos duplicados con futuro C-06/C-07 → se documentan como seed/extensión (C-06/C-07 agregan el resto sin re-migrar lo ya creado).
- [Trade-off] Sin notificaciones en este slice: el paciente no se entera automáticamente → aceptado; C-09 lo cubre y la respuesta incluye el estado para aviso manual.
- [Trade-off] Desviación temporal RN-CO-03 (seña no-touch) → aceptada con Owner C-12 y flag observable.

## Migration Plan

1. Alembic `xxx_cancelacion_turno`: `ADD COLUMN turno.cancelled_by / cancelled_at / motivo / senia_pendiente_definicion BOOLEAN DEFAULT FALSE` + `CREATE TABLE config (tenant_id FK, antelacion_cancel_hs INT DEFAULT 24 CHECK >= 0)` solo si no existe (+ `CREATE TABLE turno` mínimo solo si no existe, como seed); `downgrade` revierte ambas (R6).
2. Deploy sin downtime: solo agrega columnas/tabla, ningún ALTER destructivo; rollback = `downgrade` + deploy previo (el código nuevo no es leído por el viejo).
3. Seed demo: 1 tenant + 1 turno futuro cancelable y 1 dentro de ventana (datos sintéticos, R14).

## Open Questions

- PA-04 (ventanas por prestación): resuelta como UNA global + `resolver_antelacion(tenant, prestacion?)` extensible. C-06/C-07 pueden refinar por prestación sin cambiar contrato ni specs actuales.
- PA-05 / RN-CO-03 (política de seña): diferida a C-12 por diseño (F4); no altera specs ni tasks actuales salvo leer el flag.
- Deuda C-09 (envíos encolados de turnos cancelados): registrada; C-09 decide cancelar/ignorar.
- RBAC odontólogo (¿solo sus turnos?): resuelto — propios, salvo unión con `recepcion`/`dueno`; `usuario_id` null → `403`.

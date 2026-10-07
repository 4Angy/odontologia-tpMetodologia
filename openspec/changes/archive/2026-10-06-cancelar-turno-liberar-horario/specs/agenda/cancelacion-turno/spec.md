# Spec Delta

## Purpose

Permite a recepción cancelar un turno existente validando la antelación mínima configurable, liberando el horario de forma observable y dejando trazabilidad auditable del motivo.

## ADDED Requirements

### Requirement: Cancelación en término libera el horario (observable)

El sistema SHALL permitir cancelar un turno en estado `confirmado` o `pendiente_confirmacion` cuando la antelación restante (`inicio - ahora`) sea mayor o igual a la configurada por el tenant (`config.antelacion_cancel_hs`), transicionando el turno a `cancelado` y haciendo que la query de turnos activos por (tenant, profesional, rango) ya no lo devuelva.

#### Scenario: Cancelación exitosa en término

- **GIVEN** existe un turno en estado `confirmado` o `pendiente_confirmacion` de un tenant con `antelacion_cancel_hs` configurada, con `inicio - now > antelacion`, y un usuario autenticado con permiso de agenda
- **WHEN** un usuario con permiso de agenda envía `POST /turnos/:id/cancelar` con `motivo` válido y el turno inicia en más horas que `antelacion_cancel_hs`
- **THEN** el sistema responde `200` con el turno en estado `cancelado` y la query de activos por (tenant, profesional, rango) ya no incluye ese turno

#### Scenario: Slot liberado es observable, disponibilidad es C-07

- **GIVEN** un turno en estado `confirmado` o `pendiente_confirmacion` fue cancelado en término a `cancelado` y existe una query de activos por (tenant, profesional, rango) que lo incluía antes
- **WHEN** un turno fue cancelado en término
- **THEN** la query de activos ya no lo devuelve (hueco observable); la API de disponibilidad que reutiliza ese hueco es dependencia de C-07, no de este slice. Un hueco dentro de un bloqueo sigue no-reservable.

### Requirement: Validación de antelación mínima con error trazable y placeholder

El sistema SHALL rechazar la cancelación fuera de término (`inicio - ahora < antelacion_cancel_hs`) con `409`, cuerpo `{code: "RN-AG-01", message, action: {type: "reprogramar", hint}}` en español-AR mostrable, donde `action` es un placeholder documentado (reprogramar es C-07; frontend lo muestra deshabilitado/informativo), sin mutar el turno.

#### Scenario: Cancelación fuera de término

- **GIVEN** existe un turno en estado `confirmado` o `pendiente_confirmacion` con `inicio - now < antelacion_cancel_hs` y un usuario autenticado con permiso de agenda
- **WHEN** se intenta cancelar un turno que inicia dentro de la ventana de antelación (p. ej. 2h antes con config 24h)
- **THEN** el sistema responde `409` con `code: "RN-AG-01"`, mensaje en español-AR y `action.type: "reprogramar"` con `hint`, y el turno conserva su estado previo

#### Scenario: Límite exacto de antelación

- **GIVEN** existe un turno en estado `confirmado` o `pendiente_confirmacion` con `inicio - now == antelacion_cancel_hs` y un usuario autenticado con permiso de agenda
- **WHEN** la antelación restante es exactamente igual a `antelacion_cancel_hs`
- **THEN** la cancelación es aceptada (límite inclusivo)

#### Scenario: Antelación cero permite cancelar hasta minuto cero

- **GIVEN** el tenant tiene `antelacion_cancel_hs=0`, existe un turno en estado `confirmado` o `pendiente_confirmacion` con `inicio >= now`, y un usuario autenticado con permiso de agenda
- **WHEN** `antelacion_cancel_hs=0` y el turno aún no inició (`inicio >= now`)
- **THEN** la cancelación en término es aceptada

#### Scenario: Config ausente usa fallback con log

- **GIVEN** el tenant no tiene fila en `config`, existe un turno futuro en estado `confirmado` o `pendiente_confirmacion`, y un usuario autenticado con permiso de agenda
- **WHEN** el tenant no tiene fila en `config`
- **THEN** el sistema usa fallback 24h, emite log y valida contra ese valor

### Requirement: Antelación configurable por tenant (una global, extensible)

El sistema SHALL exponer `antelacion_cancel_hs` (entero ≥ 0, defecto 24) por tenant mediante `resolver_antelacion(tenant, prestacion?)` que hoy ignora `prestacion` (UNA antelación global, PA-04; extensible por prestación sin cambio de contrato); solo el rol `dueno` puede modificarlo y el cambio rige únicamente para cancelaciones futuras, nunca retroactivas.

#### Scenario: Dueño modifica la antelación

- **GIVEN** existe un tenant con `config.antelacion_cancel_hs` y un usuario autenticado con rol `dueno`
- **WHEN** un usuario con rol `dueno` actualiza `antelacion_cancel_hs` a un valor válido
- **THEN** las cancelaciones posteriores se validan contra el nuevo valor y las ya efectuadas no cambian

#### Scenario: Rol sin permiso intenta configurar

- **GIVEN** existe un tenant con `config.antelacion_cancel_hs` y un usuario autenticado sin rol `dueno`
- **WHEN** un usuario sin rol `dueno` intenta modificar `antelacion_cancel_hs`
- **THEN** el sistema responde `403` sin aplicar cambios

### Requirement: Trazabilidad de la cancelación

El sistema SHALL registrar en cada cancelación `cancelled_by` (usuario), `cancelled_at` (UTC con timezone) y `motivo` (texto obligatorio, 1–500 caracteres), consultable por el dueño como auditoría mínima (RN-GL-02).

#### Scenario: Cancelación registra auditoría

- **GIVEN** existe un turno cancelable en término en estado `confirmado` o `pendiente_confirmacion` y un usuario autenticado con permiso de agenda que envía `motivo` válido
- **WHEN** una cancelación en término se completa
- **THEN** el turno conserva `cancelled_by`, `cancelled_at` en UTC y el `motivo` informado, visibles en el detalle/auditoría

#### Scenario: Motivo faltante o vacío

- **GIVEN** existe un turno en estado `confirmado` o `pendiente_confirmacion` que ya superó las validaciones de tenant, existencia, permiso, no-ya-cancelado, terminales y antelación, y un usuario autenticado con permiso de agenda
- **WHEN** la solicitud de cancelación omite `motivo` o lo envía vacío (tras pasar tenant/existe/permiso/no-ya-cancelado/terminales/antelación)
- **THEN** el sistema responde `422` con mensaje en español-AR y no muta el turno

### Requirement: Idempotencia de cancelación y orden de validación

El sistema SHALL tratar la cancelación repetida del mismo turno como éxito sin efectos secundarios: si el turno ya está `cancelado`, responde `200` con el recurso actual, conserva la primera auditoría e ignora un motivo distinto. El sistema SHALL aplicar el orden inmutable: tenant → existe → permiso → ¿ya cancelado? (`200`) → terminales (`409`) → antelación (`409`) → motivo (`422`), bajo `SELECT FOR UPDATE` o update condicional por estado ante concurrencia.

#### Scenario: Doble clic en cancelar

- **GIVEN** existe un turno activo en estado `confirmado` o `pendiente_confirmacion` cancelable en término y un usuario autenticado con permiso de agenda
- **WHEN** se envía dos veces `POST /turnos/:id/cancelar` para el mismo turno (reintento o doble-clic)
- **THEN** ambas respuestas son `200` con estado `cancelado` y solo queda un registro de auditoría de la primera cancelación

#### Scenario: Segundo POST con motivo distinto conserva la primera auditoría

- **GIVEN** existe un turno en estado `cancelado` con motivo "A" y auditoría original (`cancelled_by/cancelled_at`) registrada
- **WHEN** un turno ya `cancelado` con motivo "A" recibe otro POST con motivo "B"
- **THEN** la respuesta es `200`, el turno conserva motivo "A" y `cancelled_by/cancelled_at` originales

#### Scenario: Cancelaciones concurrentes no duplican efectos

- **GIVEN** existe un turno activo en estado `confirmado` o `pendiente_confirmacion` cancelable en término y dos solicitudes autenticadas con permiso de agenda
- **WHEN** dos `POST /turnos/:id/cancelar` concurrentes llegan para el mismo turno activo
- **THEN** una transiciona a `cancelado` y la otra cae en idempotencia (`200`) sin duplicar auditoría ni efectos

### Requirement: Estados no cancelables, RBAC por unión y aislamiento sin fuga

El sistema SHALL rechazar con `409` y `code` trazable la cancelación de turnos en estados terminales (`presente`, `ausente`) y de turnos ya pasados (`inicio < now`); `reprogramado` no es un estado cancelable: es el turno viejo ya migrado por una reprogramación (C-07) y se trata como terminal/no-reintentable. El sistema SHALL aislar por tenant y SHALL autorizar por unión de roles (RN-AU-04): `recepcion` CRUD agenda, `odontologo` R solo sus turnos (`profesional.usuario_id == user.id`; si `profesional.usuario_id` es null → `403` con `code`), `dueno` todo. Sin/inválido JWT → `403`; turno inexistente o de otro tenant con JWT válido → `404` indistinguible (RN-AU-01, sin fuga por enumeración). El disparador paciente por token público es non-goal explícito (C-08).

#### Scenario: Turno ya atendido no se cancela

- **GIVEN** existe un turno en estado `presente` o `ausente` y un usuario autenticado con permiso de agenda
- **WHEN** se intenta cancelar un turno en estado `presente` o `ausente`
- **THEN** el sistema responde `409` con `code` trazable y el turno no cambia

#### Scenario: Turno ya pasado no se cancela

- **GIVEN** existe un turno en estado `confirmado` o `pendiente_confirmacion` con `inicio < now` y un usuario autenticado con permiso de agenda
- **WHEN** se intenta cancelar un turno con `inicio < now`
- **THEN** el sistema responde `409` terminal con `code` trazable y el turno no cambia

#### Scenario: Turno inexistente o de otro tenant es indistinguible

- **GIVEN** existe un usuario autenticado con JWT válido de un tenant y un `turno_id` inexistente o perteneciente a otro tenant
- **WHEN** con JWT válido se intenta cancelar un turno inexistente o de otro tenant
- **THEN** el sistema responde `404` idéntico en ambos casos, sin exponer datos del otro tenant

#### Scenario: Sin JWT o JWT inválido

- **GIVEN** existe un turno en cualquier estado y una solicitud sin JWT o con JWT inválido
- **WHEN** la solicitud llega sin JWT o con JWT inválido
- **THEN** el sistema responde `403` sin revelar existencia del turno

#### Scenario: Rol sin permiso de agenda

- **GIVEN** existe un turno activo en estado `confirmado` o `pendiente_confirmacion` y un usuario autenticado sin permiso de agenda
- **WHEN** un usuario sin permiso de agenda intenta cancelar
- **THEN** el sistema responde `403` y el turno no cambia

#### Scenario: Unión multi-rol cancela vía recepcion

- **GIVEN** existe un usuario autenticado con roles `recepcion+odontologo` y un turno cancelable en término de un profesional distinto al del usuario
- **WHEN** un usuario con roles `recepcion+odontologo` cancela un turno que no es de su profesional
- **THEN** el sistema lo autoriza (`200` si está en término) por la unión vía `recepcion`

#### Scenario: Profesional sin usuario vinculado niega a odontólogo

- **GIVEN** existe un turno cuyo `profesional.usuario_id` es null y un usuario autenticado con rol `odontologo`
- **WHEN** un `odontologo` intenta cancelar un turno cuyo `profesional.usuario_id` es null
- **THEN** el sistema responde `403` con `code` (fallback definido, sin error 500)

### Requirement: Seña intacta en este slice (desviación temporal RN-CO-03)

El sistema SHALL NOT modificar ni mover ninguna seña asociada al turno cancelado en este slice (desviación temporal explícita de RN-CO-03, Owner C-12); la seña conserva su estado y el turno cancelado setea `turno.senia_pendiente_definicion BOOLEAN DEFAULT FALSE` a `TRUE` solo si había seña asociada. C-12 lee el flag y aplica la política.

#### Scenario: Turno con seña acreditada se cancela

- **GIVEN** existe un turno cancelable en término en estado `confirmado` o `pendiente_confirmacion` con seña asociada en estado `acreditada` y un usuario autenticado con permiso de agenda
- **WHEN** se cancela en término un turno con seña `acreditada`
- **THEN** la seña sigue `acreditada` sin moverse y la respuesta incluye `senia_pendiente_definicion: true`

#### Scenario: Turno sin seña no marca el flag

- **GIVEN** existe un turno cancelable en término en estado `confirmado` o `pendiente_confirmacion` sin seña asociada y un usuario autenticado con permiso de agenda
- **WHEN** se cancela en término un turno sin seña asociada
- **THEN** la respuesta incluye `senia_pendiente_definicion: false` y ninguna seña cambia

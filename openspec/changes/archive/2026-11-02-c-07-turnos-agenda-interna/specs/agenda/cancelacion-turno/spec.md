# Spec Delta

## MODIFIED Requirements

### Requirement: Validación de antelación mínima con error trazable y reprogramación
El sistema SHALL rechazar la cancelación fuera de término (`inicio - ahora < antelacion_cancel_hs`) con `409`, cuerpo `{code: "RN-AG-01", message, action: {type: "reprogramar", hint}}` en español-AR mostrable, sin mutar el turno. La acción `reprogramar` SHALL permitir iniciar el flujo interno de reprogramación.

#### Scenario: Cancelación fuera de término
- **GIVEN** existe un turno en estado `confirmado` o `pendiente_confirmacion` con `inicio - now < antelacion_cancel_hs` y un usuario autenticado con permiso de agenda
- **WHEN** se intenta cancelar un turno que inicia dentro de la ventana de antelación (p. ej. 2h antes con config 24h)
- **THEN** el sistema responde `409` con `code: "RN-AG-01"`, mensaje en español-AR y `action.type: "reprogramar"` con `hint`, y el turno conserva su estado previo

#### Scenario: Iniciar reprogramación desde la acción ofrecida
- **GIVEN** el usuario recibe el error de cancelación fuera de término con `action.type: "reprogramar"`
- **WHEN** recepción o dueño selecciona la acción en la agenda interna y elige un horario sugerido o lo ingresa manualmente
- **THEN** el turno anterior pasa a `reprogramado` solo cuando la operación de reprogramación se completa

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

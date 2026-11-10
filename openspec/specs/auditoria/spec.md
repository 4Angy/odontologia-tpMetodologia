# auditoria Specification

## Purpose
Ofrece al dueño del consultorio una traza unificada y consultable de todas las mutaciones del sistema, incluyendo el rol activo del actor en cada acción, para cumplir la trazabilidad exigida por DD-06 y RN-GL-02.

## Requirements

### Requirement: Auditoría consultable por el dueño

El sistema SHALL exponer un endpoint `/auditoria` (solo rol `dueno`) que devuelva las mutaciones registradas del tenant ordenadas por fecha descendente, con actor, acción, recurso, recurso_id, rol activo y timestamp UTC.

#### Scenario: Dueño consulta la auditoría

- **WHEN** el dueño solicita `/auditoria` con un límite válido
- **THEN** el sistema devuelve la lista de eventos del tenant ordenada por `ocurrido_at` descendente, incluyendo `rol_activo` cuando esté disponible

#### Scenario: Usuario no dueño consulta la auditoría

- **WHEN** un usuario sin rol `dueno` solicita `/auditoria`
- **THEN** el sistema rechaza la operación con `403` y código `RN-AU-04`

### Requirement: Registro de rol activo en cada mutación

El sistema SHALL registrar el rol activo del actor en cada evento de auditoría de mutación, de modo que la unión de roles de DD-06 no borre la trazabilidad de qué rol se usó en cada acción.

#### Scenario: Mutación realizada por usuario multi-rol

- **WHEN** un usuario con varios roles ejecuta una mutación
- **THEN** el evento de auditoría queda registrado con el rol activo utilizado en esa acción

#### Scenario: Mutación histórica sin rol activo

- **WHEN** se consulta un evento anterior a la introducción de `rol_activo`
- **THEN** el sistema devuelve `rol_activo` nulo sin error

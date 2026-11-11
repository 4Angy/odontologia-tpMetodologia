# Spec Delta

## ADDED Requirements

### Requirement: Rol activo en la auditoría de mutaciones

El sistema SHALL incluir el rol activo del actor en la traza de auditoría de cada mutación, de forma que la unión de roles acumulables (DD-06) no elimine la trazabilidad de qué rol se usó en cada acción. Los eventos anteriores a la introducción de este campo SHALL conservar un valor nulo sin romper la consulta.

#### Scenario: Mutación por usuario multi-rol registra rol activo

- **GIVEN** un usuario del tenant `A` con roles `recepcion` y `odontologo`
- **WHEN** ejecuta una mutación bajo el rol `recepcion`
- **THEN** el evento de auditoría del tenant `A` registra `rol_activo = recepcion` junto con el actor y el timestamp UTC

#### Scenario: Evento histórico sin rol activo

- **GIVEN** un evento de auditoría creado antes de la introducción de `rol_activo`
- **WHEN** el dueño consulta la auditoría
- **THEN** el evento se devuelve con `rol_activo` nulo y sin error
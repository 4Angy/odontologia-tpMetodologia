# Spec Delta

## MODIFIED Requirements

### Requirement: Consultar agenda interna tenant-scoped

El sistema SHALL ofrecer consultas de agenda por día y semana con filtro opcional por profesional. Las consultas MUST respetar el tenant autenticado, el período válido, la zona horaria del tenant y los permisos de lectura, y MUST ordenar los turnos por inicio. Cada turno MUST exponer `confirmado_paciente_at` como dato de solo lectura cuando exista, sin que ninguna acción de agenda pueda escribirlo.

#### Scenario: Recepción o dueño consulta agenda

- **WHEN** recepción o dueño solicita la agenda de un período válido
- **THEN** recibe los turnos de su tenant en ese período, ordenados por inicio

#### Scenario: Odontólogo consulta sus propios turnos

- **WHEN** odontología consulta la agenda
- **THEN** recibe únicamente turnos de profesionales vinculados a su usuario y de su tenant

#### Scenario: Rechazar lectura de agenda ajena

- **WHEN** el cliente solicita datos de otro tenant o turnos de un profesional sin permiso
- **THEN** el sistema deniega o limita la consulta sin revelar datos ajenos

#### Scenario: La agenda distingue el acuse del paciente

- **WHEN** recepción o dueño consulta un período que incluye un turno con `confirmado_paciente_at` registrado
- **THEN** la respuesta indica que el paciente confirmó y el instante UTC del acuse, manteniendo el estado del turno sin cambios

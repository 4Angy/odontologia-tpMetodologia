# agenda/turnos-internos Specification

## Purpose

Define la creación y operación segura de turnos internos, incluidas las transiciones explícitas, el aislamiento por tenant, el manejo de colisiones y las consultas de agenda diaria y semanal.

## Requirements

### Requirement: Crear turnos internos aislados y válidos

El sistema SHALL permitir a recepción y dueño crear turnos para pacientes y profesionales del tenant autenticado. Los instantes MUST incluir zona horaria, el fin MUST ser posterior al inicio y el intervalo MUST coincidir con la duración de la prestación cuando se indique una. Las respuestas API MUST usar DTOs y MUST NOT exponer modelos de persistencia.

#### Scenario: Crear turno interno

- **WHEN** recepción o dueño crea un turno con referencias válidas de su tenant y un intervalo válido
- **THEN** el sistema persiste un turno `confirmado` y devuelve su representación

#### Scenario: Rechazar referencias ajenas o intervalo inválido

- **WHEN** la solicitud usa una entidad de otro tenant, un datetime naive o un intervalo inválido
- **THEN** el sistema rechaza la solicitud sin crear el turno ni revelar datos de otro tenant

### Requirement: La creación de turnos es idempotente por tenant

El sistema SHALL asociar la clave idempotente al tenant autenticado y al turno creado. Un reintento equivalente MUST devolver el turno original; reutilizar la clave con datos diferentes MUST responder conflicto sin crear ni modificar turnos.

#### Scenario: Reintento con la misma clave y contenido

- **WHEN** se repite una creación con la misma clave y el mismo contenido
- **THEN** el sistema devuelve el turno original sin duplicarlo ni duplicar su auditoría

#### Scenario: Reutilización de clave con contenido diferente

- **WHEN** se reutiliza una clave idempotente existente con datos distintos
- **THEN** el sistema responde `409` con un error trazable y no crea ni modifica turnos

### Requirement: Evitar colisiones de turnos por profesional

El sistema SHALL rechazar solapamientos con turnos activos del mismo profesional usando intervalos semiabiertos. Ante reservas ordinarias concurrentes, MUST confirmarse como máximo un turno. Una colisión MUST responder `409` con hasta tres alternativas disponibles, ordenadas por cercanía al horario solicitado y, en empate, priorizando la anterior. Las alternativas MUST respetar disponibilidad, duración de prestación y bloqueos.

#### Scenario: Rechazar colisión y ofrecer alternativas

- **WHEN** un turno ordinario se superpone con otro turno activo del profesional
- **THEN** el sistema lo rechaza con `409` y devuelve hasta tres alternativas disponibles

#### Scenario: Permitir intervalos contiguos

- **WHEN** un turno comienza exactamente al finalizar otro turno del mismo profesional
- **THEN** el sistema permite la creación porque los intervalos semiabiertos no se superponen

#### Scenario: Dos solicitudes concurrentes reservan el mismo horario

- **WHEN** dos solicitudes ordinarias concurrentes intentan crear turnos superpuestos para el mismo profesional
- **THEN** como máximo una crea el turno y la otra recibe un conflicto con alternativas actualizadas

### Requirement: El sobreturno es una excepción explícita y auditable

El sistema SHALL permitir una colisión solo si recepción o dueño solicita explícitamente el sobreturno, informa un motivo no vacío y tiene permiso de escritura de agenda. El sistema MUST registrar el actor autorizante y el motivo.

#### Scenario: Sobreturno autorizado

- **WHEN** recepción o dueño crea un turno solapado con `sobreturno=true` y motivo válido
- **THEN** el sistema permite la excepción y registra actor, motivo e instante UTC

#### Scenario: Sobreturno incompleto o sin permiso

- **WHEN** se intenta un sobreturno sin flag explícito, motivo válido o permiso de agenda
- **THEN** el sistema lo rechaza y no crea el turno

### Requirement: Las acciones de turno respetan transiciones y permisos

El sistema SHALL exponer acciones explícitas para confirmar, cancelar, reprogramar, marcar presente y marcar ausente; MUST NOT permitir cambiar el estado mediante una actualización genérica. Recepción y dueño pueden gestionar turnos. Odontología puede leer los turnos propios y cancelar sus turnos según el contrato de cancelación, pero no puede confirmar, reprogramar, marcar asistencia ni autorizar sobreturnos. La reprogramación MUST dejar el movimiento de la seña a cargo de C-12.

#### Scenario: Confirmar turno pendiente

- **WHEN** recepción o dueño confirma un turno `pendiente_confirmacion`
- **THEN** el turno pasa a `confirmado`

#### Scenario: Registrar asistencia

- **WHEN** recepción o dueño marca presente un turno confirmado, o lo marca ausente al alcanzar su hora de fin
- **THEN** el turno pasa al estado terminal solicitado

#### Scenario: Rechazar una transición no permitida

- **WHEN** la acción no es compatible con el estado actual o un odontólogo intenta una acción restringida
- **THEN** el sistema rechaza la operación con un error trazable y sin efectos parciales

#### Scenario: Reprogramar un turno

- **WHEN** recepción o dueño reprograma un turno activo en un horario elegido manualmente o sugerido por disponibilidad
- **THEN** el turno anterior pasa a `reprogramado`, se crea el nuevo como `confirmado` y la seña no se mueve en este change

### Requirement: Consultar agenda interna tenant-scoped

El sistema SHALL ofrecer consultas de agenda por día y semana con filtro opcional por profesional. Las consultas MUST respetar el tenant autenticado, el período válido, la zona horaria del tenant y los permisos de lectura, y MUST ordenar los turnos por inicio.

#### Scenario: Recepción o dueño consulta agenda

- **WHEN** recepción o dueño solicita la agenda de un período válido
- **THEN** recibe los turnos de su tenant en ese período, ordenados por inicio

#### Scenario: Odontólogo consulta sus propios turnos

- **WHEN** odontología consulta la agenda
- **THEN** recibe únicamente turnos de profesionales vinculados a su usuario y de su tenant

#### Scenario: Rechazar lectura de agenda ajena

- **WHEN** el cliente solicita datos de otro tenant o turnos de un profesional sin permiso
- **THEN** el sistema deniega o limita la consulta sin revelar datos ajenos

### Requirement: La disponibilidad se presenta como sugerencia en la agenda interna

La aplicación SHALL mostrar horarios devueltos por disponibilidad al crear o reprogramar turnos cuando se seleccionen profesional y prestación. La disponibilidad MUST ser una sugerencia: recepción y dueño también pueden ingresar manualmente otro horario, sujeto a las validaciones de intervalo, duración y colisión. Un sobreturno explícito solo exime de la colisión, no de las demás validaciones.

#### Scenario: Elegir una sugerencia de horario

- **WHEN** recepción o dueño selecciona un horario sugerido al crear o reprogramar
- **THEN** la interfaz completa el inicio con ese horario en la zona del tenant

#### Scenario: Ingresar manualmente un horario no sugerido

- **WHEN** recepción o dueño ingresa manualmente un horario válido que no colisiona
- **THEN** el sistema permite la operación aunque el horario no forme parte de los candidatos sugeridos

### Requirement: La interfaz permite operar la agenda interna

La aplicación SHALL ofrecer vistas de día y semana, filtro por profesional, alta y reprogramación de turnos, y acciones de gestión diaria con errores visibles en español-AR. La interfaz MUST reflejar los resultados guardados por el servidor y no aplicar cambios optimistas ante errores.

#### Scenario: Crear y gestionar turno desde la agenda

- **WHEN** recepción o dueño crea, confirma, reprograma o registra asistencia desde la agenda
- **THEN** la interfaz refleja el resultado guardado y mantiene el período seleccionado

#### Scenario: Mostrar conflicto de horario

- **WHEN** el backend rechaza una colisión
- **THEN** la interfaz explica el conflicto y permite elegir una de las alternativas devueltas

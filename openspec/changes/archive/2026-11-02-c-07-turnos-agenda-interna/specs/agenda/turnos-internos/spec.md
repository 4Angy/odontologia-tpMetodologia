# Spec Delta

## Purpose

Permite al equipo del consultorio operar turnos internos de forma segura, con agenda diaria y semanal, reglas de estado explícitas y protección contra dobles reservas.

## ADDED Requirements

### Requirement: Crear turnos internos aislados y válidos
El sistema SHALL permitir a recepción y dueño crear turnos para pacientes y profesionales del tenant autenticado, con instantes timezone-aware, fin posterior al inicio y duración compatible con la prestación seleccionada.

#### Scenario: Crear turno interno
- **WHEN** recepción o dueño crea un turno con referencias válidas de su tenant y un intervalo válido
- **THEN** el sistema persiste un turno confirmado y devuelve su representación sin exponer el modelo de persistencia

#### Scenario: Rechazar referencias ajenas o intervalo inválido
- **WHEN** la solicitud usa una entidad de otro tenant, un datetime naive o un intervalo inválido
- **THEN** el sistema rechaza la solicitud sin crear ni revelar datos de otro tenant

### Requirement: La creación de turnos es idempotente por tenant
El sistema SHALL asociar la clave idempotente al tenant y al turno creado, devolver el resultado original ante un reintento equivalente y rechazar la reutilización de una clave con contenido diferente sin crear otro turno.

#### Scenario: Reintento con la misma clave y contenido
- **WHEN** se repite una creación con la misma clave y el mismo contenido
- **THEN** el sistema devuelve el turno original y no duplica el registro

#### Scenario: Reutilización de clave con contenido diferente
- **WHEN** se reutiliza una clave idempotente existente con datos distintos
- **THEN** el sistema responde con conflicto identificable y no crea ni modifica turnos

### Requirement: Evitar colisiones de turnos por profesional
El sistema SHALL rechazar turnos que se superpongan con otro turno activo del mismo profesional, considerando intervalos semiabiertos, incluso ante solicitudes concurrentes, y ofrecer hasta tres horarios disponibles ordenados por cercanía al horario pedido; en empate, priorizar el horario anterior.

#### Scenario: Rechazar colisión y ofrecer alternativas
- **WHEN** un turno ordinario se superpone con otro turno activo del profesional
- **THEN** el sistema responde `409` con hasta tres horarios que respetan disponibilidad, duración y bloqueos

#### Scenario: Permitir intervalos contiguos
- **WHEN** un turno comienza exactamente al finalizar otro turno del mismo profesional
- **THEN** el sistema permite la creación porque los intervalos no se superponen

#### Scenario: Dos solicitudes concurrentes reservan el mismo horario
- **WHEN** dos solicitudes ordinarias concurrentes intentan crear turnos superpuestos para el mismo profesional
- **THEN** como máximo una crea el turno y la otra recibe el conflicto con alternativas actualizadas

### Requirement: El sobreturno es una excepción explícita y auditable
El sistema SHALL permitir una colisión solo si recepción o dueño solicita explícitamente un sobreturno, informa un motivo no vacío y cuenta con permiso de escritura de agenda; la excepción registra quién la autorizó.

#### Scenario: Sobreturno autorizado
- **WHEN** recepción o dueño crea un turno solapado con `sobreturno=true` y motivo válido
- **THEN** el sistema permite la excepción y registra actor, motivo e instante UTC

#### Scenario: Sobreturno incompleto o sin permiso
- **WHEN** se intenta un sobreturno sin flag, motivo válido o permiso de agenda
- **THEN** el sistema lo rechaza y no crea el turno

### Requirement: Las acciones de turno respetan transiciones y permisos
El sistema SHALL exponer acciones explícitas para confirmar, cancelar, reprogramar, marcar presente y marcar ausente; no permitirá cambiar el estado mediante una actualización genérica. Recepción y dueño pueden ejecutar las acciones internas; odontología conserva lectura de sus propios turnos, además de cancelar sus propios turnos según el contrato existente.

#### Scenario: Confirmar turno pendiente
- **WHEN** recepción o dueño confirma un turno `pendiente_confirmacion`
- **THEN** el turno pasa a `confirmado`

#### Scenario: Registrar asistencia
- **WHEN** recepción o dueño marca presente un turno confirmado, o lo marca ausente al alcanzar su fin programado
- **THEN** el turno pasa al estado solicitado

#### Scenario: Rechazar una transición no permitida
- **WHEN** se solicita una acción incompatible con el estado actual o un odontólogo intenta confirmar, reprogramar o marcar asistencia
- **THEN** el sistema rechaza la operación sin efectos parciales y devuelve un error trazable

#### Scenario: Reprogramar un turno
- **WHEN** recepción o dueño reprograma un turno activo con un horario elegido manualmente o sugerido por disponibilidad
- **THEN** el turno anterior pasa a `reprogramado`, se crea el nuevo turno confirmado y la seña no se mueve en este change

### Requirement: Consultar agenda interna tenant-scoped
El sistema SHALL ofrecer consultas de agenda por día y semana, con filtro opcional por profesional, respetando la zona horaria del tenant y los permisos de lectura.

#### Scenario: Recepción o dueño consulta agenda
- **WHEN** recepción o dueño solicita la agenda de un período válido
- **THEN** recibe los turnos de su tenant dentro del período, ordenados por inicio

#### Scenario: Odontólogo consulta sus propios turnos
- **WHEN** un odontólogo consulta la agenda
- **THEN** recibe únicamente turnos de profesionales vinculados a su usuario y de su tenant

#### Scenario: Rechazar lectura de agenda ajena
- **WHEN** el cliente solicita datos de otro tenant o turnos de otro profesional sin permiso
- **THEN** el sistema deniega o limita la consulta sin revelar datos ajenos

### Requirement: La interfaz permite operar la agenda interna
La aplicación SHALL ofrecer vistas de día y semana, selección de profesional y prestación, creación con disponibilidad, y acciones de gestión diaria con errores visibles en español-AR.

#### Scenario: Crear y gestionar turno desde la agenda
- **WHEN** recepción o dueño crea, confirma, reprograma o registra asistencia desde la agenda
- **THEN** la interfaz refleja el resultado guardado y mantiene la selección de período

#### Scenario: Mostrar conflicto de horario
- **WHEN** el backend rechaza una colisión
- **THEN** la interfaz explica el conflicto y permite elegir uno de los horarios alternativos disponibles

### Requirement: La disponibilidad se presenta como sugerencia en la agenda interna
La aplicación SHALL mostrar horarios devueltos por disponibilidad al crear o reprogramar turnos cuando se seleccionen profesional y prestación. La disponibilidad MUST ser una sugerencia: recepción y dueño también pueden ingresar manualmente otro horario, sujeto a las validaciones de intervalo, duración y colisión. Un sobreturno explícito solo exime de la colisión, no de las demás validaciones.

#### Scenario: Elegir una sugerencia de horario
- **WHEN** recepción o dueño selecciona un horario sugerido al crear o reprogramar
- **THEN** la interfaz completa el inicio con ese horario en la zona del tenant

#### Scenario: Ingresar manualmente un horario no sugerido
- **WHEN** recepción o dueño ingresa manualmente un horario válido que no colisiona
- **THEN** el sistema permite la operación aunque el horario no forme parte de los candidatos sugeridos

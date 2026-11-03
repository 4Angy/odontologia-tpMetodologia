# Catálogo base de agenda Specification

## Purpose

Proporciona el catálogo y la configuración tenant-scoped necesarios para calcular disponibilidad y operar la agenda interna y pública.

## Requirements

### Requirement: Catálogo de profesionales aislado y autorizado
El sistema SHALL permitir a recepción y dueño gestionar profesionales de su tenant y a los roles de consulta autorizados leer solo el catálogo de su tenant.

#### Scenario: Crear profesional sin usuario asociado
- **WHEN** recepción o dueño crea un profesional sin login
- **THEN** el profesional queda asociado exclusivamente al tenant autenticado

#### Scenario: Identificador de profesional de otro tenant
- **WHEN** una operación del catálogo referencia un profesional ajeno
- **THEN** el sistema rechaza la referencia y no revela datos del otro tenant

### Requirement: Catálogo de prestaciones conserva duración e importes seguros
El sistema SHALL permitir gestionar prestaciones con duración válida e importe de referencia en centavos enteros, nullable cuando no se informa.

#### Scenario: Leer prestación
- **WHEN** un rol de consulta autorizado lista prestaciones
- **THEN** recibe únicamente las de su tenant con duración e importe tipados

#### Scenario: Duración o importe fuera de rango
- **WHEN** se envía una duración o importe inválido
- **THEN** el sistema rechaza la solicitud sin persistir cambios

### Requirement: Bloqueos usan intervalos UTC válidos
El sistema SHALL crear, consultar, actualizar y eliminar bloqueos solo para profesionales del mismo tenant y con intervalos aware cuyo fin sea posterior al inicio.

#### Scenario: Rango inválido o datetime naive
- **WHEN** se presenta un intervalo invertido o sin zona horaria
- **THEN** el sistema responde con error de validación identificable y no crea el bloqueo

#### Scenario: Bloqueo para profesional ajeno
- **WHEN** el cliente referencia un profesional perteneciente a otro tenant
- **THEN** el sistema rechaza la mutación sin revelar su existencia

### Requirement: Configuración de agenda global por tenant y editable por dueño
El sistema SHALL permitir al dueño configurar por tenant la antelación mínima global de cancelación, la antelación mínima global de reserva y las ventanas de recordatorio. La cancelación no admite override por prestación. Los defaults son 24 horas para cancelación y 2 horas para reserva, sin constantes ocultas por tenant.

#### Scenario: Defaults globales de configuración
- **WHEN** el tenant aún no tiene configuración
- **THEN** el sistema aplica a todas las prestaciones 24 horas para cancelación, 2 horas para reserva y recordatorios T-48h/T-24h habilitados, según los nombres reales del esquema

#### Scenario: Sin override de cancelación por prestación
- **WHEN** se consulta o configura la antelación de cancelación
- **THEN** existe un solo valor global del tenant y no se acepta ni aplica un override por prestación

#### Scenario: Rol distinto al dueño modifica configuración
- **WHEN** recepción u odontólogo intenta modificar configuración
- **THEN** el sistema deniega la mutación

#### Scenario: Cambio de configuración de cancelación
- **WHEN** el dueño cambia la antelación
- **THEN** el nuevo valor rige para operaciones futuras y no reescribe decisiones pasadas

### Requirement: Horarios semanales por profesional y zona horaria del tenant
El sistema SHALL permitir configurar horarios semanales para cada profesional interpretados en la zona horaria del tenant; los bloqueos son excepciones a esos horarios. Los instantes de agenda se almacenan en UTC.

#### Scenario: Horario semanal en zona del tenant
- **WHEN** el dueño configura la disponibilidad semanal de un profesional
- **THEN** los intervalos se interpretan en la zona horaria configurada para el tenant y cualquier instante persistido se normaliza a UTC

#### Scenario: Bloqueo como excepción
- **WHEN** un bloqueo se superpone con un horario semanal del profesional
- **THEN** el intervalo bloqueado no se ofrece como disponible

### Requirement: Disponibilidad considera duración y restricciones de agenda
El sistema SHALL calcular candidatos con inicio cada 30 minutos, a partir del horario semanal del profesional, duración completa de la prestación, bloqueos y antelación mínima global de reserva, y excluir turnos ocupados cuando el dominio de turnos esté disponible.

#### Scenario: Duración completa dentro del horario
- **WHEN** una prestación comienza dentro del horario semanal pero su duración completa no cabe antes del cierre o de un bloqueo
- **THEN** el candidato no se ofrece

#### Scenario: Granularidad de inicio
- **WHEN** el sistema enumera candidatos de disponibilidad
- **THEN** cada inicio de candidato está separado por intervalos de 30 minutos

#### Scenario: Candidato atraviesa un bloqueo
- **WHEN** una prestación no cabe íntegramente en el intervalo libre del profesional
- **THEN** ese candidato no se ofrece

#### Scenario: Candidato antes de la antelación mínima global
- **WHEN** el inicio solicitado es anterior al umbral global de reserva de 2 horas o al valor configurado por el dueño
- **THEN** el candidato no se ofrece

#### Scenario: Turno ya ocupa el horario
- **WHEN** un turno activo del profesional se superpone con el candidato
- **THEN** el candidato no se ofrece

### Requirement: Mutaciones de catálogo y configuración son auditables
El sistema SHALL registrar actor, instante UTC y cambio de toda mutación de catálogo o configuración, conforme a RN-GL-02.

#### Scenario: Cambio de configuración
- **WHEN** el dueño actualiza una opción de agenda
- **THEN** el cambio queda asociado al actor autenticado y al tenant

#### Scenario: Auditoría no disponible
- **WHEN** no puede persistirse la auditoría de una mutación
- **THEN** la mutación no queda aplicada parcialmente

### Requirement: Interfaz administra catálogo y configuración
La aplicación SHALL ofrecer vistas para profesionales, prestaciones, bloqueos y configuración, con permisos por rol y errores de validación visibles.

#### Scenario: Usuario autorizado mantiene catálogo
- **WHEN** recepción o dueño crea o actualiza elementos permitidos del catálogo
- **THEN** la vista refleja el resultado guardado para su tenant

#### Scenario: Odontólogo consulta catálogo
- **WHEN** odontólogo abre el catálogo o configuración que puede consultar
- **THEN** solo ve información de agenda de su tenant y no obtiene permiso de escritura no concedido

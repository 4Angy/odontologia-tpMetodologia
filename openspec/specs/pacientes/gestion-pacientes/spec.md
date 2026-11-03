# gestion-pacientes Specification

## Purpose

Permite gestionar los datos identificatorios y preferencias de comunicación de pacientes dentro de un consultorio, con controles de privacidad y portabilidad de datos.

## Requirements

### Requirement: Datos de pacientes aislados por tenant
El sistema SHALL derivar el tenant de la identidad autenticada y limitar cada lectura y mutación de pacientes y opt-ins a ese tenant.

#### Scenario: Consulta de paciente de otro tenant
- **WHEN** un usuario solicita un paciente perteneciente a otro tenant
- **THEN** el sistema responde como si el paciente no existiera y no revela sus datos

#### Scenario: El cliente envía tenant_id
- **WHEN** un cliente incluye un tenant no autorizado en una solicitud
- **THEN** el sistema rechaza el campo no declarado o ignora cualquier fuente de tenant que no sea la identidad validada

### Requirement: Datos personales se exponen mediante contratos estrictos
El sistema SHALL validar los campos de entrada, rechazar propiedades no declaradas y responder con DTOs que no expongan entidades internas.

#### Scenario: Campo de entrada desconocido
- **WHEN** una solicitud de paciente contiene un campo no admitido
- **THEN** el sistema rechaza la solicitud sin persistir cambios

#### Scenario: Teléfono inválido
- **WHEN** se intenta crear o actualizar un teléfono que no cumple E.164
- **THEN** el sistema rechaza la operación con un error de negocio identificable

### Requirement: Paciente puede gestionarse sin sobrescribir su saldo
El sistema SHALL permitir consultar, crear, actualizar y dar de baja lógica a pacientes sin aceptar un saldo arbitrario del cliente.

#### Scenario: Cliente intenta definir saldo
- **WHEN** una solicitud de creación o actualización incluye saldo
- **THEN** el sistema rechaza el campo y conserva el saldo administrado por el dominio

#### Scenario: Baja lógica de paciente sin historia asociada
- **WHEN** un usuario autorizado elimina un paciente sin historia clínica o financiera
- **THEN** el paciente queda dado de baja lógica, no aparece en consultas operativas y sus datos no se borran físicamente

#### Scenario: Borrado destructivo con historia asociada
- **WHEN** se solicita eliminar un paciente con historia clínica o financiera asociada
- **THEN** el sistema bloquea el borrado destructivo, no elimina ni cascada la historia y devuelve un error de negocio identificable; cualquier supresión de esos datos requiere un proceso separado

### Requirement: Opt-in requiere acción explícita y contacto válido
El sistema SHALL mantener preferencias de comunicación separadas por paciente y canal, y activar WhatsApp solo tras una acción explícita con teléfono E.164 válido.

Cada activación SHALL guardar la versión del texto presentado, el actor autenticado y el instante UTC. Esta evidencia técnica no implica una determinación de validez legal. Recepción y dueño pueden administrar opt-ins; odontología solo puede consultarlos.

#### Scenario: Activar WhatsApp con teléfono válido
- **WHEN** un usuario autorizado registra explícitamente opt-in WhatsApp para un paciente con teléfono válido
- **THEN** el sistema guarda el estado del canal, su evidencia de consentimiento y no habilita otros canales

#### Scenario: Activar WhatsApp sin teléfono válido
- **WHEN** se intenta activar WhatsApp sin teléfono o con un teléfono inválido
- **THEN** el sistema rechaza la operación y no activa el opt-in

#### Scenario: Activar WhatsApp sin versión del texto
- **WHEN** se intenta activar WhatsApp sin identificar la versión del texto presentado
- **THEN** el sistema rechaza la operación y no activa el opt-in

#### Scenario: Odontología intenta modificar el opt-in
- **WHEN** un usuario con rol únicamente odontología intenta modificar un opt-in
- **THEN** el sistema deniega la mutación y conserva el estado existente

### Requirement: Cambio de teléfono revoca consentimiento y referencias al número anterior
El sistema SHALL revocar el opt-in WhatsApp al cambiar el teléfono, exigir consentimiento nuevo para el número nuevo e impedir acciones pendientes habilitadas para el número anterior.

#### Scenario: Cambio de teléfono con opt-in activo
- **WHEN** un usuario autorizado cambia el teléfono de un paciente que tiene activo el opt-in WhatsApp
- **THEN** el opt-in queda revocado, el nuevo número no queda consentido y se requiere una acción explícita de consentimiento nuevo para reactivarlo

#### Scenario: Cambio de teléfono con tokens o trabajos pendientes
- **WHEN** el teléfono cambia y existen tokens o trabajos de comunicación asociados al número anterior
- **THEN** C-04 invalida los tokens bajo su control y notifica la invalidación mediante el contrato de integración de C-09 para que los trabajos asociados al número anterior no se ejecuten; C-04 no simula ni implementa el worker de C-09

### Requirement: Mutaciones de pacientes son auditables
El sistema SHALL registrar quién, cuándo y qué cambió en cada mutación de paciente u opt-in, conforme a RN-GL-02.

#### Scenario: Actualización de datos de contacto
- **WHEN** un usuario autorizado actualiza un paciente u opt-in
- **THEN** el cambio y su actor quedan auditados dentro del tenant

#### Scenario: Auditoría no disponible
- **WHEN** no puede persistirse la auditoría de una mutación
- **THEN** la mutación no se confirma parcialmente

### Requirement: Importación CSV informa cada fila
El sistema SHALL importar pacientes desde CSV aislando duplicados y errores por fila y devolver un reporte que identifique filas importadas, duplicadas y fallidas.

El archivo SHALL ser UTF-8 (con o sin BOM), medir como máximo 5 MiB y contener como máximo 5.000 filas de datos. Los encabezados aceptados son `nombre`, `apellido`, `dni`, `telefono` y `email`; `nombre` y `apellido` son obligatorios y no se permiten columnas desconocidas.

#### Scenario: CSV con filas válidas, duplicadas e inválidas
- **WHEN** se importa un CSV que contiene las tres clases de fila
- **THEN** el reporte distingue cada fila y su resultado sin descartar silenciosamente el resto del archivo

#### Scenario: CSV vacío o mal formado
- **WHEN** el archivo no contiene registros utilizables o no puede analizarse
- **THEN** el sistema devuelve un error comprensible y no crea pacientes parciales sin reportarlos

### Requirement: Exportación de pacientes del tenant en CSV
El sistema SHALL permitir exportar pacientes en CSV, incluyendo exclusivamente datos del tenant autenticado. La exportación de turnos y cobros pertenece a C-07/C-11.

#### Scenario: Exportar pacientes
- **WHEN** un usuario autorizado exporta pacientes
- **THEN** recibe un CSV utilizable que contiene exclusivamente pacientes de su tenant

### Requirement: Interfaz permite operar pacientes y preferencias
La aplicación SHALL ofrecer a los roles autorizados una lista/búsqueda, alta, detalle, edición, opt-ins e importación con reporte, mostrando errores de validación.

#### Scenario: Buscar y abrir un paciente
- **WHEN** recepción consulta pacientes por apellido, teléfono o DNI
- **THEN** puede abrir el detalle de un resultado de su tenant

#### Scenario: Revisar resultado de importación
- **WHEN** finaliza una importación CSV
- **THEN** la interfaz presenta resultados de filas importadas, duplicadas y fallidas sin ocultar errores

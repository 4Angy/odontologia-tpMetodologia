# pacientes/ficha-clinica Specification

## Purpose

Permite consultar y registrar la atención clínica mínima de un paciente, sus adjuntos y presupuestos, preservando privacidad, trazabilidad y migrabilidad futura.

## Requirements

### Requirement: Acceso clínico tenant-scoped y por rol
El sistema SHALL limitar cada dato clínico al tenant autenticado y aplicar la matriz RBAC de actores: odontólogo gestiona sus evoluciones, dueño las consulta, recepción no accede a evoluciones.

#### Scenario: Acceso de otro tenant
- **WHEN** un usuario solicita una evolución o adjunto de otro tenant
- **THEN** el sistema no revela ni modifica el recurso

#### Scenario: Recepción intenta consultar evolución
- **WHEN** recepción consulta una evolución clínica
- **THEN** el sistema deniega el acceso sin revelar su contenido

### Requirement: Timeline y evolución respetan exactamente ADR-003
El sistema SHALL conservar y exponer cada evolución con el contrato ADR-003: `profesional_id`, `fecha` almacenada en UTC, `pieza_fdi_slot` y `pieza_fdi_numero` ambos presentes o ambos ausentes, `odontograma_ref` nullable, `firma_simple` y `firmado_at`.

#### Scenario: Consultar timeline
- **WHEN** un usuario con permiso abre la ficha
- **THEN** ve las evoluciones de ese paciente ordenadas de la más reciente a la más antigua

#### Scenario: Registrar evolución con firma simple
- **WHEN** el odontólogo registra una evolución
- **THEN** se conservan `firma_simple` y `firmado_at` según ADR-003, y se declara que la firma simple no es firma digital Ley 25.506

### Requirement: Evolución conserva el contrato de proyección FDI
El sistema SHALL conservar en cada evolución los campos de ADR-003 necesarios para una proyección FDI v2 sin pérdida, sin implementar el odontograma v2.

#### Scenario: Evolución anclada a pieza
- **WHEN** una evolución incluye `pieza_fdi_slot` y `pieza_fdi_numero`
- **THEN** ambos campos se guardan juntos y permanecen recuperables con `odontograma_ref`, contenido y `fecha` UTC

#### Scenario: Evolución sin ancla
- **WHEN** una evolución no identifica pieza
- **THEN** ambos campos FDI quedan ausentes, `odontograma_ref` puede ser null y no se inventa una pieza

#### Scenario: Ancla FDI incompleta
- **WHEN** solo se presenta uno de `pieza_fdi_slot` o `pieza_fdi_numero`
- **THEN** el sistema rechaza la evolución sin persistirla

#### Scenario: Proyección repetida
- **WHEN** se proyecta una evolución dos veces al contrato de migración
- **THEN** el resultado es idempotente y no pierde motivo, detalle, fecha, firma ni ancla

### Requirement: Adjuntos privados se validan y sirven de forma temporal
El sistema SHALL asociar adjuntos al paciente y tenant correctos, almacenarlos cifrados en almacenamiento privado compatible con S3, aceptar solo JPEG, PNG o PDF de hasta 10 MiB tras validar el tipo real, y emitir para descarga URLs firmadas de corta duración sin requerir un proveedor específico.

#### Scenario: Archivo permitido y válido
- **WHEN** se incorpora un JPEG, PNG o PDF cuyo tipo real coincide con el tipo declarado y su tamaño es como máximo 10 MiB
- **THEN** el archivo se guarda cifrado en almacenamiento privado y su descarga requiere una URL firmada de corta duración

#### Scenario: Tipo o tamaño inválido
- **WHEN** se incorpora un archivo cuyo tipo real no es JPEG, PNG o PDF, cuyo tipo real no coincide con el declarado, o que supera 10 MiB
- **THEN** se rechaza con un error comprensible y no queda disponible ni registrado como adjunto válido

#### Scenario: Adjunto de otro tenant
- **WHEN** un usuario intenta leer o asociar un adjunto con paciente de otro tenant
- **THEN** el sistema rechaza la operación sin revelar el recurso

### Requirement: CRUD y estados de presupuestos derivan deuda sin editar saldo
El sistema SHALL permitir crear, consultar, actualizar, cambiar estado y eliminar presupuestos e ítems; representar importes en centavos enteros, calcular el total desde sus ítems y derivar saldo sin aceptar una escritura directa de saldo. Un presupuesto en borrador no afecta la deuda; solo presupuestos aprobados o aceptados la contribuyen, restando cobros y créditos aplicados por C-11.

#### Scenario: Total de presupuesto
- **WHEN** se registra un presupuesto con varios ítems
- **THEN** el total corresponde a la suma de sus montos enteros en centavos

#### Scenario: Presupuesto en borrador
- **WHEN** se crea o actualiza un presupuesto en borrador
- **THEN** se calcula su total desde los ítems, pero no aumenta la deuda ni el saldo

#### Scenario: Presupuesto aprobado o aceptado
- **WHEN** un presupuesto pasa a estado aprobado o aceptado
- **THEN** su importe contribuye a la deuda derivada; cobros y créditos aplicados por C-11 se restan, sin endpoint que escriba el saldo directamente

#### Scenario: Editar, cambiar estado o eliminar presupuesto
- **WHEN** se edita, cambia de estado o elimina un presupuesto
- **THEN** el total y la deuda derivada se recalculan a partir de los presupuestos computables y las aplicaciones de C-11, sin producir saldo desincronizado ni permitir editarlo directamente

### Requirement: Mutaciones clínicas y presupuestarias son auditables
El sistema SHALL conservar para cada mutación clínica o presupuestaria quién la realizó, cuándo ocurrió y qué cambió, de modo consultable por el dueño.

#### Scenario: Consultar auditoría clínica
- **WHEN** el dueño consulta auditoría
- **THEN** puede identificar actor, instante UTC y cambio sin acceder a datos de otros tenants

#### Scenario: Mutación sin auditoría
- **WHEN** falla el registro de auditoría de una mutación
- **THEN** la mutación no se confirma parcialmente

### Requirement: Ficha integrada presenta historia clínica
La aplicación SHALL ofrecer una ficha por paciente con timeline, adjuntos, presupuestos y saldo, respetando los permisos definidos para cada rol.

#### Scenario: Odontólogo registra atención
- **WHEN** el odontólogo autorizado abre una ficha de su tenant
- **THEN** puede consultar la historia y registrar la evolución permitida

#### Scenario: Usuario sin permiso clínico
- **WHEN** recepción abre la ficha
- **THEN** la aplicación no muestra ni permite acceder a evoluciones clínicas

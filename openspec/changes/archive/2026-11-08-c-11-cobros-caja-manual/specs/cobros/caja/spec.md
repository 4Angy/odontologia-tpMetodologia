# Spec Delta

## Purpose

Permite registrar cobros manuales, derivar saldos y deudas por paciente y cerrar la caja del día con totales por medio de pago, sin emitir comprobantes fiscales en v1.

## ADDED Requirements

### Requirement: Cobros aislados por tenant
El sistema SHALL derivar el tenant de la identidad autenticada y limitar cada lectura y mutación de cobros y cierres de caja a ese tenant.

#### Scenario: Consulta de cobro de otro tenant
- **WHEN** un usuario solicita un cobro perteneciente a otro tenant
- **THEN** el sistema responde como si el cobro no existiera y no revela sus datos

#### Scenario: El cliente envía tenant_id
- **WHEN** una solicitud de cobro incluye un tenant no autorizado
- **THEN** el sistema rechaza el campo no declarado o ignora cualquier fuente de tenant que no sea la identidad validada

### Requirement: Saldo y deuda siempre derivados
El sistema SHALL calcular el saldo de un paciente como cargos (presupuestos aprobados o aceptados) menos pagos (cobros manuales; las señas se integran cuando C-12 esté disponible), y SHALL rechazar cualquier intento de definirlo desde el cliente.

#### Scenario: Cliente intenta definir saldo
- **WHEN** una solicitud de cobro o paciente incluye un campo `saldo`
- **THEN** el sistema rechaza el campo no declarado y conserva el saldo administrado por el dominio

#### Scenario: Saldo tras registrar un cobro
- **WHEN** se registra un cobro válido para un paciente con presupuestos aprobados
- **THEN** el saldo derivado del paciente disminuye en el monto del cobro

### Requirement: Alta de cobro rápida y validada
El sistema SHALL permitir crear un cobro con paciente, monto en centavos, medio de pago, concepto y fecha, validando que el monto sea mayor o igual a cero y el medio sea uno de los admitidos.

#### Scenario: Alta exitosa de cobro
- **WHEN** un usuario autorizado registra un cobro válido en menos de 30 segundos de interacción
- **THEN** el sistema persiste el cobro con auditoría y devuelve el recurso creado

#### Scenario: Medio de pago inválido
- **WHEN** se intenta registrar un cobro con un medio no admitido
- **THEN** el sistema rechaza la operación con un error de negocio identificable

#### Scenario: Monto negativo
- **WHEN** se intenta registrar un cobro con monto negativo
- **THEN** el sistema rechaza la operación con un error de negocio identificable

### Requirement: Listado de deudas ordenado
El sistema SHALL exponer las deudas de pacientes con saldo positivo, ordenadas por antigüedad por defecto y permitiendo ordenar por monto.

#### Scenario: Deudas ordenadas por antigüedad
- **WHEN** se consulta el listado de deudas sin parámetro de orden
- **THEN** el sistema devuelve solo pacientes con saldo mayor a cero, ordenados por la deuda más antigua primero

#### Scenario: Deudas ordenadas por monto
- **WHEN** se consulta el listado de deudas con orden por monto
- **THEN** el sistema devuelve los pacientes ordenados por saldo descendente

### Requirement: Cierre de caja diario inmutable
El sistema SHALL permitir crear un cierre de caja por tenant y fecha con totales por medio de pago, y SHALL rechazar su edición o eliminación posterior.

#### Scenario: Creación de cierre del día
- **WHEN** un usuario con rol dueño solicita cerrar la caja de una fecha
- **THEN** el sistema calcula los totales por medio a partir de los cobros de esa fecha y persiste el cierre con auditoría

#### Scenario: Cierre duplicado para la misma fecha
- **WHEN** se intenta cerrar la caja de una fecha que ya tiene cierre
- **THEN** el sistema rechaza la operación con un error de negocio identificable y no modifica el cierre existente

#### Scenario: Edición directa de un cierre
- **WHEN** se intenta modificar un cierre ya persistido mediante PUT o PATCH
- **THEN** el sistema rechaza la operación con un error de negocio identificable

### Requirement: Ajuste de caja solo con auditoría
El sistema SHALL permitir registrar un ajuste vinculado a un cierre existente, exigiendo una nota y dejando evidencia de auditoría sin modificar los totales del cierre original.

#### Scenario: Ajuste con nota
- **WHEN** un usuario con rol dueño registra un ajuste con nota para un cierre existente
- **THEN** el sistema persiste la evidencia de auditoría y, si se incluye monto, registra un cobro adicional de concepto "ajuste"

#### Scenario: Ajuste sin nota
- **WHEN** se intenta registrar un ajuste sin nota
- **THEN** el sistema rechaza la operación con un error de negocio identificable

### Requirement: Declaración honesta de alcance
El sistema SHALL declarar en la interfaz de caja que v1 es caja manual y no emite comprobantes fiscales.

#### Scenario: Pantalla de caja muestra alcance
- **WHEN** un usuario accede a la pantalla de caja
- **THEN** la interfaz muestra un mensaje visible indicando que v1 es caja manual sin comprobantes fiscales
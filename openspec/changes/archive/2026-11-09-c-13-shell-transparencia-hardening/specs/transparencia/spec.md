# Spec Delta

## Purpose

Permite al dueño del consultorio ver de forma transparente el consumo de WhatsApp, la lista honesta de lo que el sistema no hace todavía y el precio del plan en ARS, como diferenciador de confianza frente a competidores que ocultan costos.

## ADDED Requirements

### Requirement: Transparencia de consumo de WhatsApp

El sistema SHALL exponer al dueño el consumo de notificaciones por período (mensajes y costo estimado), reutilizando el panel ya disponible, de modo que el costo operativo sea visible y auditable in-app.

#### Scenario: Dueño consulta el consumo del período

- **WHEN** el dueño solicita el consumo de un rango válido de fechas
- **THEN** el sistema devuelve los totales de mensajes y costo estimado por canal y estado, formateados en ARS

#### Scenario: Usuario no dueño intenta ver el consumo

- **WHEN** un usuario sin rol `dueno` intenta consultar el consumo
- **THEN** el sistema rechaza la operación con `403` y código `RN-AU-04`

### Requirement: Declaración honesta de lo que no hace el sistema

El sistema SHALL mostrar al dueño una sección "qué no hace (aún)" con la lista de funcionalidades fuera de alcance de v1 (odontograma, facturación electrónica AFIP/ARCA, obras sociales, reportes avanzados, cobro online completo, multi-sucursal, API pública), para que la promesa comercial sea verificable in-app.

#### Scenario: Dueño abre la sección de transparencia

- **WHEN** el dueño accede a la página de transparencia
- **THEN** el sistema muestra la lista de funcionalidades fuera de alcance de v1 con su correspondiente backlog (v2+)

### Requirement: Precio del plan visible in-app

El sistema SHALL mostrar el precio del plan en ARS de forma visible dentro de la aplicación, sin requerir contacto comercial, para que el costo sea transparente desde el primer uso.

#### Scenario: Dueño ve el precio del plan

- **WHEN** el dueño accede a la página de transparencia
- **THEN** el sistema muestra el precio del plan en ARS con al menos dos decimales
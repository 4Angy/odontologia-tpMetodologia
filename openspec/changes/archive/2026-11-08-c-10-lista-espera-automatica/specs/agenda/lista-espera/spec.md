# Spec Delta

## Purpose

Gestiona la lista de espera de pacientes por tenant y ofrece automáticamente, por WhatsApp, el primer hueco compatible liberado por una cancelación, con TTL configurable y auditoría de transiciones.

## ADDED Requirements

### Requirement: Alta de entrada en lista de espera

El sistema SHALL permitir a recepción o dueño crear una entrada `activa` en la lista de espera de su tenant asociada a un paciente, con `profesional_id` nullable (cualquiera) y `prestacion_id` nullable, y SHALL asignar `prioridad` y `created_at` en UTC. La entrada MUST quedar en estado `activa` y MUST ser visible en la cola auditable.

#### Scenario: Alta exitosa

- **WHEN** un usuario con permiso de agenda envía `POST /lista-espera` con `paciente_id` válido y `profesional_id`/`prestacion_id` opcionales
- **THEN** el sistema responde `201` con la entrada en estado `activa`, `prioridad` asignada y `created_at` en UTC

#### Scenario: Paciente inexistente o de otro tenant

- **WHEN** se intenta crear una entrada para un `paciente_id` inexistente o de otro tenant
- **THEN** el sistema responde `404` sin crear la entrada (R1)

### Requirement: Consulta auditable de la cola

El sistema SHALL exponer `GET /lista-espera` filtrado por tenant y SHALL permitir filtrar por `estado`, devolviendo las entradas ordenadas por `prioridad` y `created_at`, con los estados `activa|ofrecida|convertida|vencida`.

#### Scenario: Listado por estado

- **WHEN** recepción consulta `GET /lista-espera?estado=activa`
- **THEN** el sistema devuelve solo las entradas `activa` del tenant ordenadas por prioridad y fecha de alta

### Requirement: Oferta automática al liberarse un hueco compatible

El sistema SHALL, al cancelarse un turno en término, buscar la primera entrada `activa` del mismo tenant compatible con el hueco liberado (`profesional_id` de la entrada es null o igual al del turno cancelado, y `prestacion_id` es null o igual) y SHALL transicionarla a `ofrecida`, fijando `expires_at = now + TTL` (default 2h, configurable por tenant) y encolando un envío WhatsApp con plantilla `lista_espera` a través del motor de C-09. Si no existe entrada compatible, el hueco queda libre.

#### Scenario: Primera entrada elegible recibe la oferta

- **WHEN** se cancela en término un turno y existe al menos una entrada `activa` compatible
- **THEN** la primera por prioridad pasa a `ofrecida`, registra `expires_at`, y se crea exactamente un envío `canal="whatsapp"`, `plantilla_codigo="lista_espera"`, `estado="encolada"`

#### Scenario: Sin entradas compatibles

- **WHEN** se cancela en término un turno y no existe entrada `activa` compatible
- **THEN** ningún estado cambia y el hueco queda libre para carga manual

### Requirement: Omisión por falta de opt-in con motivo registrado

El sistema SHALL, al evaluar una entrada `activa` compatible sin opt-in explícito de WhatsApp (o sin teléfono E.164 válido), saltarla, registrar el motivo `RN-PA-01` (sin invocar al proveedor) y continuar con la siguiente entrada elegible. La entrada saltada MUST permanecer `activa` para futuros huecos.

#### Scenario: Entrada sin opt-in se salta

- **WHEN** la primera entrada compatible no tiene opt-in de WhatsApp válido
- **THEN** el sistema registra un envío `estado="omitida"` con `motivo_code="RN-PA-01"`, no invoca al proveedor, y evalúa la siguiente entrada compatible

### Requirement: Vencimiento de la oferta y avance automático

El sistema SHALL, mediante el worker, marcar como `vencida` toda entrada `ofrecida` cuyo `expires_at` ya pasó y SHALL intentar ofrecer el hueco al siguiente `activa` compatible. Una entrada `ofrecida` MUST tener a lo sumo un ofrecimiento vigente por hueco a la vez.

#### Scenario: TTL vencido pasa al siguiente

- **WHEN** el worker detecta una entrada `ofrecida` con `expires_at <= now`
- **THEN** la marca `vencida` y, si existe, ofrece el hueco al siguiente `activa` compatible con nuevo `expires_at`

#### Scenario: Sin siguiente elegible

- **WHEN** vence una oferta y no existe otra entrada `activa` compatible
- **THEN** la entrada queda `vencida` y el hueco queda libre

### Requirement: Aceptación asigna el turno y sale de la lista

El sistema SHALL, al aceptarse una oferta vigente mediante token público, crear un turno para el hueco ofrecido en estado `confirmado` (o `pendiente_confirmacion` si aplica seña), transicionar la entrada a `convertida`, y reutilizar el mecanismo de tokens de C-08. Si el hueco ya no está disponible, el sistema SHALL responder error trazable y la entrada MUST volver a `activa`.

#### Scenario: Aceptación exitosa

- **WHEN** el paciente abre el link de aceptación con token válido y vigente y el hueco sigue libre
- **THEN** se crea el turno asignado, la entrada pasa a `convertida` y el token queda consumido/revocado

#### Scenario: Hueco ya tomado al aceptar

- **WHEN** el paciente acepta pero el hueco fue ocupado por otro turno
- **THEN** el sistema responde error trazable, la entrada vuelve a `activa` y no se crea turno

### Requirement: Declinación vence la oferta y avanza

El sistema SHALL, al declinarse una oferta vigente mediante token público, transicionar la entrada a `vencida` y SHALL intentar ofrecer el hueco al siguiente `activa` compatible. Un token de declinación MUST ser de un solo uso.

#### Scenario: Declinación exitosa

- **WHEN** el paciente abre el link de declinación con token válido y vigente
- **THEN** la entrada pasa a `vencida` y el sistema intenta ofrecer el hueco al siguiente elegible

### Requirement: Arrastre de seña al asignar por lista de espera

El sistema SHALL, al asignar un turno por aceptación de lista de espera, reutilizar la política de arrastre de seña de RN-AG-05 cuando exista seña acreditada asociada al contexto aplicable; en caso contrario, el turno nace sin seña. La política final de seña MUST delegarse a C-12 cuando corresponda.

#### Scenario: Aceptación con seña arrastrada

- **WHEN** la aceptación asigna un turno y existe seña acreditada arrastrable según RN-AG-05
- **THEN** el turno se crea con la seña arrastrada y no se cobra dos veces

### Requirement: Oferta manual desde la cola

El sistema SHALL permitir a recepción o dueño disparar manualmente la oferta para una entrada `activa` compatible con un hueco indicado, reutilizando las mismas reglas de elegibilidad, TTL y envío que la oferta automática.

#### Scenario: Oferta manual exitosa

- **WHEN** recepción selecciona una entrada `activa` y un hueco compatible y dispara la oferta manual
- **THEN** la entrada pasa a `ofrecida` con `expires_at` y se encola el WhatsApp, igual que en la oferta automática

### Requirement: Aislamiento multi-tenant y auditoría de transiciones

El sistema SHALL filtrar toda operación de lista de espera por `tenant_id` del JWT (R1/R2) y SHALL registrar cada transición de estado (`activa→ofrecida`, `ofrecida→convertida`, `ofrecida→vencida`) con actor, instante UTC y motivo cuando aplique. Los datos de prueba MUST ser sintéticos (R14).

#### Scenario: Aislamiento entre tenants

- **WHEN** un usuario de un tenant intenta acceder a entradas de otro tenant
- **THEN** el sistema responde `404` indistinguible sin exponer datos del otro tenant

#### Scenario: Auditoría de transición

- **WHEN** una entrada cambia de estado
- **THEN** queda registrado actor, instante UTC y motivo (si aplica) para auditoría

# notificaciones/motor-envios Specification

## Purpose
Define el motor de notificaciones del consultorio: selección de turnos por ventana,
cola durable de envíos, entrega por WhatsApp con reintentos y fallback a email,
webhook idempotente del proveedor, acuse del paciente sin alterar la máquina de
estados y visibilidad de consumo/costo por tenant.

## Requirements

### Requirement: El scheduler respeta opt-in y ventanas configuradas

El sistema SHALL encolar recordatorios únicamente para turnos activos del tenant
cuyo instante de envío (`turno.inicio - ventana`) cae dentro de la ventana de
planificación vigente, y MUST exigir opt-in explícito del canal. Las ventanas
(`recordatorio_1_hs`, `recordatorio_2_hs`) MUST ser configurables por tenant y sus
instantes MUST calcularse sobre `turno.inicio` en UTC. Cuando no exista canal
habilitado, el sistema MUST registrar el descarte con un `motivo_code` trazable y
MUST NOT invocar al proveedor.

#### Scenario: Turno entra en la ventana T-48h con opt-in

- **WHEN** el scheduler corre y un turno activo del tenant alcanza su instante de envío T-48h y el paciente tiene opt-in de WhatsApp vigente
- **THEN** el sistema crea exactamente un envío `canal="whatsapp"`, `ventana="t-48h"`, `estado="encolada"` con `next_attempt_at` en el instante de envío

#### Scenario: Paciente sin ningún canal habilitado

- **WHEN** el turno alcanza su ventana y el paciente no tiene opt-in de WhatsApp ni email registrado
- **THEN** el sistema registra un envío `estado="omitida"` con `motivo_code="RN-PA-01"` y no realiza ninguna llamada al proveedor

#### Scenario: Ventana ya vencida al crear el turno

- **WHEN** un turno se crea cuando su instante de envío T-24h ya pasó
- **THEN** el sistema no crea un recordatorio para esa ventana y no envía un mensaje tardío

### Requirement: Como máximo un envío por turno, ventana y canal

El sistema SHALL garantizar a nivel de persistencia que exista un único envío por
`tenant_id`, `turno_id`, `ventana` y `canal`, de modo que dos ejecuciones del
scheduler no dupliquen mensajes (RN-PA-03). La garantía MUST sobrevivir a reinicios
y a la ejecución concurrente de más de una instancia del worker.

#### Scenario: Segundo tick dentro de la misma ventana

- **WHEN** el scheduler vuelve a evaluar un turno que ya tiene un envío para la misma ventana y canal
- **THEN** no se crea un segundo envío y no se envía un segundo mensaje

#### Scenario: Dos instancias del scheduler corren a la vez

- **WHEN** dos instancias evaluán la misma ventana del mismo tenant de forma concurrente
- **THEN** solo una toma el turno de planificación y el resultado sigue siendo un único envío por turno y ventana

### Requirement: Los envíos pendientes se cancelan cuando dejan de ser válidos

El sistema SHALL cancelar los envíos `encolada` de un turno cuando el turno se
cancela o reprograma, o cuando el opt-in del paciente se revoca (RN-PA-02). La
cancelación MUST registrar el motivo y MUST evitar cualquier llamada al proveedor.

#### Scenario: Turno cancelado antes del envío

- **WHEN** un turno con recordatorio `encolada` se cancela antes de su `next_attempt_at`
- **THEN** el envío pasa a `estado="cancelada"` con `motivo_code="turno_cancelado"` y el proveedor no recibe el mensaje

#### Scenario: Opt-in revocado por cambio de teléfono

- **WHEN** el paciente revoca su opt-in de WhatsApp después de que el recordatorio quedó encolado
- **THEN** el envío pendiente se cancela y no se envía al número anterior

### Requirement: La entrega es durable, reintentable y con costo registrado

El sistema SHALL tomar envíos `encolada` cuyo `next_attempt_at` ya venció mediante
una reclamación que impida la doble toma entre workers. Cada intento MUST
incrementar `intentos`, y el resultado MUST registrarse como `enviada`,
`entregada`, `fallida` o `cancelada`, conservando `provider_msg_id`, el instante
UTC y el costo estimado en centavos enteros. Un fallo transitorio MUST devolver el
envío a `encolada` con un nuevo `next_attempt_at`; agotados tres intentos, MUST
quedar `fallida` y ser visible para recepción.

#### Scenario: Envío exitoso por WhatsApp

- **WHEN** el worker toma un envío de WhatsApp cuyo proveedor responde con aceptación
- **THEN** el envío pasa a `enviada`, guarda `provider_msg_id`, `enviado_at` en UTC y el `costo_estimado_centavos` vigente al momento del envío

#### Scenario: Fallo transitorio del proveedor

- **WHEN** el proveedor responde con un error transitorio (timeout, `429` o `5xx`)
- **THEN** el envío permanece `encolada`, incrementa `intentos` y recibe un `next_attempt_at` con backoff, sin generar un envío nuevo

#### Scenario: Tercer intento fallido

- **WHEN** el envío acumula tres intentos fallidos
- **THEN** pasa a `fallida` con el último código de error y queda disponible para reintento manual

### Requirement: El fallback a email conserva la intención de envío

El sistema SHALL encolar un envío `canal="email"` cuando el paciente tiene email y
el envío de WhatsApp falla definitivamente, o cuando tiene email pero no tiene
opt-in de WhatsApp (RN-PA-04). El envío de email MUST procesarse por el mismo
worker y MUST NOT realizarse de forma inline al detectar el fallo, para que la
intención sobreviva a un corte del proceso.

#### Scenario: WhatsApp agota los reintentos y hay email

- **WHEN** un envío de WhatsApp pasa a `fallida` y el paciente tiene email registrado
- **THEN** el sistema crea un envío `canal="email"` en estado `encolada` para el mismo turno y ventana, y el worker lo entrega por SMTP

#### Scenario: Sin email disponible

- **WHEN** un envío de WhatsApp pasa a `fallida` y el paciente no tiene email
- **THEN** el envío queda visible como `fallida` para recepción, sin pérdida del registro de la intención

### Requirement: El webhook del proveedor es autenticado, idempotente y monótono

El sistema SHALL verificar la firma del webhook del proveedor antes de procesarlo y
MUST rechazar solicitudes sin firma válida. El procesamiento MUST ser idempotente
por `provider_msg_id` y MUST NOT retroceder el estado de un envío ante eventos
desordenados. El endpoint MUST responder `2xx` ante un duplicado para evitar
reintentos infinitos del proveedor.

#### Scenario: Evento de entrega válido

- **WHEN** llega un webhook firmado con un `provider_msg_id` conocido y estado `delivered`
- **THEN** el envío correspondiente pasa a `entregada` y registra `entregado_at` en UTC

#### Scenario: Webhook duplicado

- **WHEN** el proveedor reenvía el mismo evento con el mismo `provider_msg_id`
- **THEN** el sistema responde `2xx` sin modificar el envío ni duplicar auditoría

#### Scenario: Webhook con firma inválida

- **WHEN** llega una solicitud con firma ausente o incorrecta
- **THEN** el sistema responde `401`/`403` y no modifica ningún envío

#### Scenario: Eventos fuera de orden

- **WHEN** llega un evento `sent` después de uno `delivered` para el mismo envío
- **THEN** el envío permanece en `entregada` y no retrocede de estado

### Requirement: El acuse del paciente se registra sin cambiar el estado del turno

El sistema SHALL registrar el acuse del paciente proveniente del recordatorio en
`turno.confirmado_paciente_at`, sin modificar `turno.estado`, cuando el turno ya
está `confirmado`. Cuando el turno está `pendiente_confirmacion`, MUST conservar la
transición a `confirmado` de C-08. El acuse MUST ser idempotente y MUST exigir un
token público válido y vigente.

#### Scenario: Acuse sobre un turno ya confirmado

- **WHEN** el paciente usa el link del recordatorio sobre un turno `confirmado` con token `confirm` vigente
- **THEN** el sistema guarda `confirmado_paciente_at` en UTC y deja `turno.estado` en `confirmado`

#### Scenario: Acuse repetido

- **WHEN** el paciente vuelve a usar el mismo link de confirmación
- **THEN** el sistema responde exitosamente, conserva el primer `confirmado_paciente_at` y no crea registros duplicados

#### Scenario: Token expirado o revocado

- **WHEN** el acuse se intenta con un token expirado o revocado
- **THEN** el sistema rechaza la operación con un error trazable y no registra el acuse

### Requirement: El consumo y el costo son visibles por tenant

El sistema SHALL exponer el consumo de notificaciones por período, agregando
cantidad de envíos y suma de `costo_estimado_centavos` por canal y estado. La
consulta MUST estar restringida al tenant autenticado, MUST usar permisos de dueño
y MUST presentar los importes en centavos enteros, sin `float`.

#### Scenario: Dueño consulta el consumo del período

- **WHEN** el dueño solicita el consumo de un rango válido
- **THEN** recibe la cantidad de mensajes y el costo total en centavos por canal y estado, solo de su tenant

#### Scenario: Recepción intenta ver el consumo

- **WHEN** un usuario con rol recepción solicita el panel de consumo
- **THEN** el sistema deniega la operación sin revelar datos de costos

#### Scenario: Aislamiento entre tenants

- **WHEN** el dueño de un tenant consulta su consumo
- **THEN** la respuesta no incluye envíos de otro tenant aun cuando compartan el mismo período

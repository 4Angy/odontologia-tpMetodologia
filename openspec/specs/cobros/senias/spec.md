# cobros/senias Specification

## Purpose
Permite exigir y acreditar una seña por Mercado Pago al reservar, arrastrarla ante reprogramaciones, aplicar políticas de devolución parametrizables y liberar reservas sin pago en el plazo configurado.

## Requirements

### Requirement: Seña aislada por tenant
El sistema SHALL derivar el tenant de la identidad autenticada y limitar cada lectura y mutación de señas a ese tenant.

#### Scenario: Consulta de seña de otro tenant
- **WHEN** un usuario solicita una seña perteneciente a otro tenant
- **THEN** el sistema responde como si la seña no existiera y no revela sus datos

### Requirement: Preferencia de pago en reserva pública
El sistema SHALL crear una preferencia de Mercado Pago cuando la seña esté activa y requerida para la prestación seleccionada, y SHALL devolver un `checkout_url` utilizable por el paciente.

#### Scenario: Reserva con seña requerida
- **WHEN** un visitante reserva un turno cuya prestación requiere seña
- **THEN** el sistema crea la preferencia, persiste la seña en estado `pendiente` y devuelve un `checkout_url` no vacío

#### Scenario: Reserva sin seña requerida
- **WHEN** un visitante reserva un turno cuya prestación no requiere seña
- **THEN** el sistema no crea preferencia y devuelve `checkout_url` nulo o vacío

### Requirement: Acreditación idempotente por webhook
El sistema SHALL acreditar una seña al recibir el webhook de Mercado Pago, usando `mp_payment_id` como clave de idempotencia, y SHALL confirmar el turno cuando la seña sea requerida.

#### Scenario: Webhook de pago acreditado
- **WHEN** llega un webhook con un pago acreditado para una seña pendiente
- **THEN** la seña pasa a `acreditada`, el turno pasa a `confirmado` y se registra auditoría

#### Scenario: Webhook duplicado
- **WHEN** llega un webhook con un `mp_payment_id` ya procesado
- **THEN** el sistema responde exitosamente sin duplicar la acreditación ni cambiar el estado

#### Scenario: Webhook con firma inválida
- **WHEN** llega un webhook cuya firma no coincide con el secreto configurado
- **THEN** el sistema rechaza la solicitud con un error identificable

### Requirement: Arrastre de seña ante reprogramación
El sistema SHALL mover la seña acreditada al nuevo turno al reprogramar, y SHALL convertirla en saldo a favor si el nuevo turno no requiere seña.

#### Scenario: Reprogramación a turno que requiere seña
- **WHEN** se reprograma un turno con seña acreditada hacia una prestación que requiere seña
- **THEN** la seña se asocia al nuevo turno sin cobrarse dos veces

#### Scenario: Reprogramación a turno que no requiere seña
- **WHEN** se reprograma un turno con seña acreditada hacia una prestación que no requiere seña
- **THEN** la seña pasa a `aplicada` y se contabiliza como saldo a favor del paciente

### Requirement: Devolución parametrizable
El sistema SHALL aplicar la política de devolución configurada (`no_devuelve`, `devuelve_50`, `devuelve_100`) según la antelación de cancelación, y SHALL usar como default saldo a favor en término y pérdida fuera de término.

#### Scenario: Cancelación en término con default
- **WHEN** un paciente cancela con la antelación configurada
- **THEN** la seña pasa a `aplicada` y queda como saldo a favor

#### Scenario: Cancelación fuera de término con default
- **WHEN** un paciente cancela con menos antelación que la configurada
- **THEN** la seña pasa a `devuelta` sin generar saldo a favor

#### Scenario: Política devuelve 50
- **WHEN** la política configurada es `devuelve_50` y se cancela
- **THEN** la mitad del monto queda como saldo a favor y el resto se pierde

### Requirement: Liberación por timeout
El sistema SHALL cancelar el turno y liberar la seña pendiente si no se acredita el pago dentro del plazo configurado.

#### Scenario: Pago no acreditado en 30 minutos
- **WHEN** una reserva con seña pendiente supera el plazo configurado
- **THEN** el turno se cancela, la seña se marca como `devuelta` y se ofrece el hueco a lista de espera

### Requirement: Saldo incluye señas
El sistema SHALL restar las señas en estado `acreditada` o `aplicada` al calcular el saldo derivado del paciente.

#### Scenario: Saldo con seña acreditada
- **WHEN** un paciente tiene una seña acreditada
- **THEN** el saldo derivado disminuye en el monto de la seña

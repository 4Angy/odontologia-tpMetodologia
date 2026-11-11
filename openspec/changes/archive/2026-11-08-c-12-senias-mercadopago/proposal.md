# Proposal

## Why

La reserva pública hoy deja el turno en `pendiente_confirmacion` y genera un `checkout_url` vacío: no hay compromiso real del paciente (DD-05). C-12 implementa la seña por Mercado Pago (US-007) para que la reserva sea un compromiso real, con arrastre ante reprogramación y política de devolución parametrizable, sin bloquear el flujo local si MP cae (RN-GL-03).

## What Changes

- **New models**: `Senia` (turno, paciente, monto, `mp_preference_id`, `mp_payment_id` nullable, estado `pendiente|acreditada|devuelta|aplicada`).
- **Configuración por prestación**: `PrestacionModel` gana `senia_monto_cents` (nullable) y `senia_requerida` (bool); `ConfigModel` mantiene `senia_requerida` global como default y agrega `politica_devolucion_senia`.
- **Preferencia MP**: reserva pública crea preferencia y devuelve `checkout_url` real (adapter `MPClient` con `httpx`, siguiendo el patrón de `WhatsAppClient`).
- **Webhook MP**: `POST /webhooks/mercadopago` acredita la seña (idempotencia por `mp_payment_id`) y confirma el turno cuando la seña es requerida.
- **Arrastre**: reprogramar (interno y público) mueve la seña al nuevo turno; si el nuevo turno no requiere seña, la seña queda como saldo a favor (`aplicada`).
- **Devolución**: cancelación evalúa antelación (RN-AG-01) y aplica política (`no_devuelve|devuelve_50|devuelve_100`); default: en término → saldo a favor, fuera de término → se pierde.
- **Timeout 30 min**: `release_expired_pending_payments` marca la seña como `devuelta`/`perdida` y libera el turno.
- **Saldo derivado**: `saldo_derivado` resta señas `acreditada`/`aplicada` (además de cobros).
- **Migración 015**: tabla `senia` + `turno.senia_id` + columnas en `prestacion` y `config`.
- **Frontend**: config de seña por prestación, estado de seña en el turno, aviso de arrastre al reprogramar.

## Capabilities

### New Capabilities
- `cobros/senias`: seña por Mercado Pago con preferencia, webhook idempotente, arrastre ante reprogramación y devolución parametrizable.

### Modified Capabilities
- `agenda/reserva-publica`: la reserva genera `checkout_url` real y confirma el turno al acreditarse la seña requerida.
- `agenda/turnos-internos`: reprogramar arrastra la seña acreditada al nuevo turno.
- `agenda/cancelacion-turno`: la cancelación aplica la política de devolución de la seña.

## Impact

- **Código**: nuevo módulo `app/modules/pagos` o extensión de `cobros` (models, schemas, repository, service, router, webhook), adapter `MPClient`, actualización de `public_booking.py`, `turnos_service.py`, `PacienteService.saldo_derivado`/`CobroService`.
- **APIs**: `POST /webhooks/mercadopago`, endpoints de config de seña por prestación, estado de seña en turno.
- **Datos**: tabla `senia`, `turno.senia_id`, columnas en `prestacion` y `config`.
- **Dependencias**: depende de C-08 y C-11; habilita C-13 (credenciales MP por tenant).
- **Frontend**: config de seña, estado en turno, aviso de arrastre.
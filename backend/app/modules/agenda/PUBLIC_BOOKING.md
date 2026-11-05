# Contrato de reserva pública

Este módulo crea reservas en estado `pendiente_confirmacion`. C-08 no llama a
Mercado Pago ni interpreta webhooks de pago.

## Rutas HTTP públicas

Todas las rutas siguientes son sin JWT. El tenant se resuelve por `tenant_slug`
o por el token opaco; nunca se acepta `tenant_id` desde el navegador.

| Método | Ruta | Propósito |
| --- | --- | --- |
| `GET` | `/r/{tenant_slug}` | Catálogo y disponibilidad pública |
| `POST` | `/public/reservar` | Crear reserva; requiere `Idempotency-Key` |
| `POST` | `/public/turnos/{token}/confirmar` | Confirmar con token de propósito `confirm` |
| `POST` | `/public/turnos/{token}/cancelar` | Cancelar con token de propósito `cancel` |
| `POST` | `/public/turnos/{token}/reprogramar` | Reprogramar con token de propósito `reschedule` |

Las respuestas de error usan `{code, message}`. Las rutas públicas devuelven
`429` con `Retry-After` cuando se excede el límite. La respuesta de reserva
puede incluir `checkout_url` cuando se requiere seña, pero C-08 no acredita
pagos.

Los tokens expiran, se revocan individualmente y solo se conserva su hash.
Confirmar, cancelar y reprogramar no comparten el mismo propósito.

## Integración con C-12

- Si `config.senia_requerida` está activa, `POST /public/reservar` devuelve
  `checkout_url` pendiente y mantiene el turno sin confirmar.
- C-12 debe emitir un evento de acreditación idempotente identificado por
  `mp_payment_id`, asociado al turno/seña.
- La acreditación puede pasar el turno a `confirmado`; una reserva pública no
  debe confirmarse por confiar en un dato enviado por el navegador.
- El timeout inicial de una reserva pendiente de pago es de 30 minutos. El job
  de liberación debe cancelar la ocupación, revocar los tokens y dejar
  trazabilidad de la liberación.

Los tokens de acciones se entregan como valores opacos y solo se conserva su
hash. No deben copiarse a logs, eventos de pago ni registros de auditoría.

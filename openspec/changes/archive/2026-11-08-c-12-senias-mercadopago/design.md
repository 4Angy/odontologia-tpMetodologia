# Design

## Context

Ver `proposal.md`. C-12 depende de C-08 (reserva pública) y C-11 (caja/saldo). La reserva pública ya crea turnos `pendiente_confirmacion` con `senia_pendiente_definicion`, `checkout_url` vacío y `release_expired_pending_payments`. El saldo ya se deriva restando cobros; falta sumar señas.

## Goals / Non-Goals

**Goals:**
- Implementar seña por Mercado Pago con preferencia, webhook idempotente y arrastre.
- Integrar devolución parametrizable y timeout de 30 min.
- Extender el saldo derivado para incluir señas.

**Non-Goals:**
- Credenciales MP por tenant (C-13).
- Devolución real vía API de MP (v1 solo saldo a favor / pérdida).
- Checkout general.

## Decisions

### D1 · Adapter MP con httpx (Opción A)
- **Decisión**: `MPClient` con Protocol (`crear_preferencia`, `obtener_pago`) usando `httpx`, siguiendo `WhatsAppClient`. Fake para tests.
- **Rationale**: consistente con el stack; sin dependencia nueva.

### D2 · Config de seña por prestación (Opción A)
- **Decisión**: `PrestacionModel` gana `senia_monto_cents` (nullable) y `senia_requerida` (bool). `ConfigModel` mantiene `senia_requerida` global y agrega `politica_devolucion_senia`.
- **Rationale**: cumple “por prestación” sin romper lo existente.

### D3 · Webhook robusto (Opción A)
- **Decisión**: `POST /webhooks/mercadopago` acepta formatos `payment`/`payment.updated` y query params. Verifica firma HMAC SHA256 con `MP_WEBHOOK_SECRET`. Idempotencia por `mp_payment_id` (unique).
- **Rationale**: tolerante a cambios de MP y seguro.

### D4 · Arrastre al reprogramar (Opción A)
- **Decisión**: `reschedule` (interno y público) reasigna `senia_id` al nuevo turno; si el nuevo no requiere seña, la seña pasa a `aplicada` (saldo a favor).
- **Rationale**: evita cobrar dos veces y respeta RN-AG-05.

### D5 · Devolución parametrizable (Opción A)
- **Decisión**: cancelación evalúa antelación. En término → `aplicada` (saldo a favor). Fuera de término → `devuelta` según política. Política en `ConfigModel.politica_devolucion_senia`.
- **Rationale**: cumple RN-CO-03 y el supuesto default.

### D6 · Confirmación por webhook (Opción A)
- **Decisión**: webhook acredita y, si `senia_requerida`, confirma el turno.
- **Rationale**: cierra el flujo público sin intervención manual.

## Risks / Trade-offs

- [Webhook fuera de orden] → idempotencia por `mp_payment_id` + estado terminal `acreditada`.
- [MP caído] → flujo local se completa; seña queda `pendiente`; reintento exponencial (RN-GL-03).
- [Arrastre en reprogramación interna] → `turnos_service` no propaga `senia_id` hoy; hay que agregar.
- [Saldo] → extender `_pagos_del_paciente` y agregar `_senias_del_paciente`.

## Migration Plan

1. Migración `015_senias_mercadopago`: tabla `senia`, `turno.senia_id`, columnas en `prestacion` y `config`.
2. Implementar adapter `MPClient` + fake.
3. Implementar módulo `cobros/senias` (o extender `cobros`) y webhook.
4. Integrar en `public_booking.py` (preferencia + confirmación).
5. Integrar arrastre en `reschedule` (público e interno).
6. Integrar devolución en cancelación.
7. Extender `saldo_derivado`.
8. Frontend: config de seña, estado en turno, aviso de arrastre.
9. Tests.

## Open Questions

Ninguna bloqueante. Credenciales MP por tenant se resuelven en C-13.
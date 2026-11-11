# Tasks

## 1. Migración y modelos

- [x] 1.1 Crear migración `016_senias_mercadopago` (down_revision `015_merge_lista_espera_cobros`) con tabla `senia`, columnas en `prestacion` y `config`; verificar upgrade/downgrade.
- [x] 1.2 Implementar modelos `SeniaModel` y actualizar `PrestacionModel`/`ConfigModel`; verificar import.

## 2. Backend core

- [x] 2.1 Implementar adapter `MPClient` (Protocol + real con httpx + fake) y tests unitarios.
- [x] 2.2 Implementar módulo de señas (schemas, service): crear preferencia, acreditar, devolver, arrastrar.
- [x] 2.3 Implementar webhook `POST /webhooks/mercadopago` con verificación de firma e idempotencia; tests de webhook duplicado.
- [x] 2.4 Integrar preferencia en `public_booking.create` y confirmación por webhook.
- [x] 2.5 Integrar arrastre en `reschedule` (público e interno) y devolución en cancelación.
- [x] 2.6 Extender `saldo_derivado` (CobroService) para restar señas acreditadas/aplicadas.

## 3. API y config

- [x] 3.1 Agregar campos de seña a `PrestacionCreate/Response` y `ConfigResponse/UpdateRequest`; verificar validación.
- [x] 3.2 Endpoints `GET /senias` y `GET /senias/{id}`; tests de API.

## 4. Frontend

- [x] 4.1 Config de seña por prestación en página de configuración.
- [x] 4.2 Estado de seña en turno y aviso de arrastre al reprogramar (`AgendaPage`) + checkout/arrastre en `PublicBookingPage`.
- [x] 4.3 Tests de frontend para flujos de seña.

## 5. Integración y verificación

- [x] 5.1 Ejecutar suite completa backend (267 passed, 1 skipped) y frontend (64 passed); verificar sin regresiones.
- [x] 5.2 Validar change con `openspec validate`.

# Tasks

## 1. MigraciÃ³n y configuraciÃ³n

- [x] 1.1 Crear migraciÃ³n Alembic `013_lista_espera` (tabla `lista_espera`, Ã­ndices `(tenant_id, estado, prioridad)` y `(tenant_id, estado, expires_at)`, columna `config.lista_espera_ttl_hs` default 2 con check >= 0) con `downgrade` probado `upgrade head â†’ downgrade 012 â†’ upgrade head` contra PostgreSQL 16.
- [x] 1.2 Exponer `lista_espera_ttl_hs` en `ConfigModel` y `ConfigRepository.upsert` (default 2) y verificar con tests de config existentes que el default y el check se aplican.

## 2. Modelo y repositorio (backend)

- [x] 2.1 Crear `app/modules/lista_espera/models.py` con `ListaEsperaModel` (TenantMixin + AuditMixin) y estados `activa|ofrecida|convertida|vencida`, campos de hueco ofrecido (`hueco_profesional_id`, `hueco_inicio`, `hueco_fin`, `hueco_prestacion_id`), `ofrecido_at`, `expires_at`, `motivo_omision`, y verificar import + migraciÃ³n.
- [x] 2.2 Crear `ListaEsperaRepository` tenant-scoped (`list`, `get_by_id`, `create`, `update`, `list_activas_compatibles`, `list_ofrecidas_vencidas`) y verificar tests de aislamiento R1 (cross-tenant â†’ 404/None).
- [x] 2.3 Registrar el modelo en `alembic`/`Base` y verificar que `Base.metadata` incluye `lista_espera`.

## 3. Servicio de dominio

- [x] 3.1 Implementar `ListaEsperaService.ofrecer_por_hueco(tenant_id, hueco, now)` que selecciona la primera `activa` compatible, la marca `ofrecida`, fija `expires_at`, persiste el hueco y encola `notificacion_envio` (plantilla `lista_espera`) reutilizando `NotificacionEnvioRepository`, incluyendo omisiÃ³n por falta de opt-in con `motivo_code="RN-PA-01"` y avance al siguiente; verificar tests de oferta, skip por opt-in y ausencia de compatibles.
- [x] 3.2 Implementar `ListaEsperaService.vencer_y_avanzar(now)` para el worker: marca `vencida` las `ofrecida` con `expires_at <= now` y ofrece al siguiente compatible; verificar tests de TTL vencido y sin siguiente.
- [x] 3.3 Implementar `ListaEsperaService.aceptar(token, tenant_slug, now)` transaccional (validar token `waitlist_accept`, lock profesional, verificar hueco libre, crear turno `confirmado`/`pendiente_confirmacion`, transicionar a `convertida`, revocar token; revertir a `activa` si el hueco fue tomado); verificar tests de Ã©xito, hueco tomado y token invÃ¡lido/expirado.
- [x] 3.4 Implementar `ListaEsperaService.declinar(token, tenant_slug, now)` que vence la oferta y ofrece al siguiente; verificar tests de Ã©xito y token de un solo uso.

## 4. API interna

- [x] 4.1 Agregar `POST /lista-espera` y `GET /lista-espera` (filtros por `estado`) con DTOs Pydantic v2 `extra='forbid'` y RBAC recepciÃ³n/dueno; verificar tests de alta, listado y validaciÃ³n 422.
- [x] 4.2 Agregar `POST /lista-espera/{id}/ofrecer` (oferta manual con hueco en body) reutilizando el servicio; verificar tests de oferta manual exitosa y sin compatibles.

## 5. IntegraciÃ³n con cancelaciÃ³n y pagos

- [x] 5.1 Modificar `cancelar_turno` (interno) para llamar a `ListaEsperaService.ofrecer_por_hueco` con el hueco del turno cancelado dentro de la misma transacciÃ³n; verificar test de cancelaciÃ³n que dispara oferta.
- [x] 5.2 Modificar cancelaciÃ³n pÃºblica (`public_cancel`) para disparar la misma oferta; verificar test end-to-end por token.
- [x] 5.3 Modificar liberaciÃ³n por timeout de pago (`public_booking`) para disparar la oferta al liberar el hueco; verificar test.

## 6. Tokens pÃºblicos y endpoints de aceptaciÃ³n/declinaciÃ³n

- [x] 6.1 Extender `PURPOSES`/validaciÃ³n de C-08 para `waitlist_accept` y `waitlist_decline` y generar tokens al ofertar; verificar tests de validez/expiraciÃ³n/revocaciÃ³n.
- [x] 6.2 Agregar `POST /public/lista-espera/{token}/aceptar` y `POST /public/lista-espera/{token}/declinar` con rate limit; verificar tests de aceptaciÃ³n/declinaciÃ³n por token.

## 7. Worker

- [x] 7.1 Agregar job `lista_espera.expiry` a `JOBS` y ejecutar `ListaEsperaService.vencer_y_avanzar` en cada tick; verificar test de tick que vence y avanza.

## 8. Frontend

- [x] 8.1 Crear vista de cola `ListaEsperaPage` (estados auditables, filtros por estado) y formulario de alta; verificar render y llamadas a API con tests de componente.
- [x] 8.2 Agregar botÃ³n de oferta manual en la cola que llama a `POST /lista-espera/{id}/ofrecer`; verificar test de interacciÃ³n.

## 9. IntegraciÃ³n y migraciÃ³n

- [x] 9.1 Ejecutar suite de backend (`pytest`) y verificar que los tests de C-07/C-08/C-09 siguen verdes tras los cambios.
- [x] 9.2 Verificar migraciÃ³n `013` con ciclo `upgrade head â†’ downgrade 012 â†’ upgrade head` en PostgreSQL 16 y documentar evidencia.



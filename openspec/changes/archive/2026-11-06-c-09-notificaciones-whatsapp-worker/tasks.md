# Tasks

> Change **preparado para implementar**. Ninguna tarea está ejecutada: todas quedan
> `[ ]` y cada una declara cómo se verifica. El apply no puede marcar el change como
> implementado, verificado ni archivado sin ejecutar la verificación indicada.

## 1. Contrato y persistencia

- [x] 1.1 Escribir pruebas de contrato para los DTO de `POST /notificaciones/test`, `GET /notificaciones/consumo`, `GET /notificaciones/envios`, `POST /notificaciones/envios/{id}/reintentar` y el payload del webhook; verificar que campos extra fallen (`extra='forbid'`), que los importes viajen en centavos enteros y que todo datetime sea UTC aware.
- [x] 1.2 Crear `012_notificaciones` reversible (posterior a `011_reserva_publica_tokens`) con `plantilla`, `notificacion_envio`, `config.recordatorio_1_hs`, `config.recordatorio_2_hs`, `config.whatsapp_costo_centavos` y `turno.confirmado_paciente_at`; verificar `alembic upgrade head → downgrade 011 → upgrade head` contra PostgreSQL 16 y que el `downgrade` elimine en orden inverso sin romper FKs.
- [x] 1.3 Escribir pruebas de persistencia para las dos unicidades (`tenant_id, turno_id, ventana, canal` y `tenant_id, provider_msg_id` parcial), los checks de costo e intentos y el índice de reclamación; implementar modelos y repositorios tenant-scoped y verificar que ninguna consulta devuelva filas de otro tenant ni exponga ORM en la API.
- [x] 1.4 Sembrar las cinco plantillas `es-AR` del tenant demo con `activa=false` y placeholders `{{paciente}}`, `{{fecha}}`, `{{link}}`; verificar idempotencia del seed (dos ejecuciones, mismo resultado) y que ninguna plantilla quede activa por defecto.

## 2. Scheduler de recordatorios

- [x] 2.1 Escribir pruebas de cálculo de ventanas para `recordatorio_1_hs`/`recordatorio_2_hs` configurables, valores por defecto 48/24, límites del tick y turnos creados en `America/Argentina/Buenos_Aires`; implementar el cálculo en UTC y verificar que no exista corrimiento por zona horaria ni por cambio de offset.
- [x] 2.2 Escribir pruebas de opt-in: con opt-in de WhatsApp se crea un envío `encolada`; sin WhatsApp pero con email se crea un envío de email; sin ningún canal se crea `omitida` con `motivo_code="RN-PA-01"`; implementar la selección y verificar que el proveedor no se invoque en los casos de omisión.
- [x] 2.3 Escribir pruebas de anti-spam: segundo tick sobre la misma ventana no crea fila, dos instancias concurrentes producen un solo envío y dos ventanas distintas producen dos envíos; implementar con `ON CONFLICT DO NOTHING` y verificar contra PostgreSQL real (no SQLite) que la restricción es la que evita el duplicado.
- [x] 2.4 Escribir pruebas de invalidación: turno cancelado, turno reprogramado y opt-in revocado pasan los envíos `encolada` a `cancelada` con el `motivo_code` correspondiente; implementar la actualización y verificar que el sender no envíe una fila cancelada aunque haya sido reclamada en el mismo instante.

## 3. Sender y adapter de proveedor

- [x] 3.1 Definir `WhatsAppClient` (Protocol) con `CloudApiClient` y `FakeClient`; escribir pruebas del adapter real con `httpx.MockTransport` para `200`, `429` y `500`, verificando el mapeo a error transitorio o permanente y que el token no aparezca en logs.
- [x] 3.2 Escribir pruebas de reclamación concurrente con `FOR UPDATE SKIP LOCKED` sobre dos workers; implementar el claim y verificar que un envío reclamado por uno no sea tomado por el otro y que un proceso caído libere la fila al cerrar la transacción.
- [x] 3.3 Escribir pruebas de reintento con backoff 1/5/15 minutos, incremento de `intentos`, actualización de `next_attempt_at` y transición a `fallida` en el tercer fallo; implementar y verificar que un fallo transitorio no cree un envío nuevo ni pierda el `provider_msg_id` de un intento previo exitoso.
- [x] 3.4 Escribir pruebas de costo: `costo_estimado_centavos` se copia de `config` al enviar, un cambio posterior de tarifa no altera el histórico y el email queda en `0`; implementar el snapshot y verificar que no exista ningún `float` en el camino del dinero.
- [x] 3.5 Escribir pruebas del canal email contra SMTP de prueba (Mailhog/`aiosmtpd`); implementar el envío y verificar que un fallo de SMTP deje la fila `encolada` o `fallida` según el intento, nunca en `enviada`.

## 4. Webhook del proveedor

- [x] 4.1 Escribir pruebas del `GET /webhooks/whatsapp` con `hub.verify_token` correcto e incorrecto; implementar el challenge y verificar que un token inválido no devuelva el challenge ni revele configuración.
- [x] 4.2 Escribir pruebas de firma `X-Hub-Signature-256` con cuerpo válido, firma alterada, firma ausente y cuerpo modificado después de firmar; implementar la verificación HMAC-SHA256 sobre el cuerpo crudo y verificar que ningún rechazo mute estado.
- [x] 4.3 Escribir pruebas de idempotencia y orden: evento duplicado responde `2xx` sin cambios, `sent` después de `delivered` no retrocede, `failed` después de `delivered` no degrada; implementar el ranking monotónico y verificar que el duplicado no duplique auditoría.

## 5. Acuse del paciente

- [x] 5.1 Escribir pruebas de `turno.confirmado_paciente_at`: se registra una sola vez, es idempotente ante repetición del mismo token y no cambia `turno.estado`; implementar la escritura y verificar que ninguna acción interna de agenda pueda modificarlo.
- [x] 5.2 Extender `POST /public/turnos/{token}/confirmar` de C-08 para aceptar un turno ya `confirmado` y registrar el acuse, conservando la transición a `confirmado` para `pendiente_confirmacion`; verificar con token expirado, revocado y de otro tenant que el acuse no se registra.
- [x] 5.3 Exponer `confirmado_paciente_at` en la representación del turno y en la agenda diaria/semanal; escribir pruebas de que el cliente lo recibe como dato de solo lectura y que el filtro "confirmó / sin respuesta" no altera el estado.

## 6. API de gestión y panel de consumo

- [x] 6.1 Escribir pruebas de `GET /notificaciones/consumo` para rangos válidos, rango invertido, período vacío y agregación por canal/estado; implementar con `COUNT` y `SUM` sobre el índice `(tenant_id, created_at)` y verificar que recepción reciba `403` y que no se filtren envíos de otro tenant.
- [x] 6.2 Escribir pruebas de `GET /notificaciones/envios` con filtros por estado y turno, y de `POST /notificaciones/envios/{id}/reintentar` solo desde `fallida`; implementar y verificar que reintentar un envío `encolada`, `enviada` o `entregada` responda error trazable sin efectos.
- [x] 6.3 Escribir pruebas de `POST /notificaciones/test` con rol permitido, rol denegado y límite de frecuencia; implementar el envío auditado a un paciente sintético y verificar que respete opt-in y que no permita elegir `tenant_id` desde el body.

## 7. Frontend mínimo

- [x] 7.1 Escribir pruebas del cliente y de la vista de consumo para el dueño (mensajes, costo en centavos formateado a ARS, rango de fechas); implementar la vista y verificar que no aplique cambios optimistas ni muestre datos de otro tenant.
- [x] 7.2 Escribir pruebas de la página pública `/r/:slug/confirmar?token=...` que hace el `POST` al cargar y muestra éxito, token vencido, token revocado y error de red; implementar y verificar que un `GET` sin ejecución de JS no confirme ningún turno.

## 8. Integración del worker y validación del change

- [x] 8.1 Registrar `notificaciones.scheduler` y `notificaciones.sender` en `JOBS` de `backend/app/worker/main.py`, con `NOTIFICACIONES_ENABLED=false` por defecto; verificar arranque con el interruptor apagado (no encola), encendido (encola) y con Redis caído (el scheduler sigue por advisory lock).
- [x] 8.2 Escribir pruebas del lock `tick:notificaciones:{tenant}` con TTL 840 s y del fallback `pg_try_advisory_lock`; verificar con el MCP `redis` (`redis_key_info`, `redis_scan`) que la clave existe con TTL válido durante el intervalo y desaparece al vencer, y que no hay colisión con otros prefijos del proyecto.
- [x] 8.3 Ejecutar `openspec validate c-09-notificaciones-whatsapp-worker --strict`, la suite focalizada de backend, las pruebas de migración up/down, el build de TypeScript y `git diff --check`; verificar que los tres escenarios obligatorios de la matriz estén en verde y que no se hayan modificado capacidades fuera del alcance.

## Matriz de escenarios obligatorios

Los tres escenarios que exige la consigna están en `specs/notificaciones/motor-envios/spec.md` y se verifican así:

| Tipo | Escenario | Tarea | Cómo se verifica |
|---|---|---|---|
| **Funcionamiento esperado** | Turno entra en la ventana T-48h con opt-in → un envío `encolada` → `enviada` con `provider_msg_id` y costo en centavos | 2.1, 2.2, 3.1, 3.4 | Test de integración con `FakeClient`: se crea el turno a 48 h, corre el scheduler, corre el sender y se afirma una fila por ventana con estado `enviada`, `costo_estimado_centavos > 0` y `enviado_at` en UTC |
| **Error de negocio** | Paciente sin opt-in de WhatsApp ni email → no se envía y queda `omitida` con `RN-PA-01` | 2.2, 3.5 | Test de servicio con paciente sin `optin` ni email: cero llamadas al `FakeClient`, una fila `omitida`, `motivo_code="RN-PA-01"`, y el turno intacto |
| **Borde** | Dos instancias del scheduler evalúan la misma ventana a la vez → un solo envío (anti-spam RN-PA-03) | 2.3, 8.2 | Test de concurrencia contra PostgreSQL real: dos sesiones compiten por el lock y por el `INSERT`; se afirma exactamente una fila por `(tenant, turno, ventana, canal)` y un solo lock `tick:*` visible con el MCP `redis` |

Escenarios adicionales de borde cubiertos por las tareas: turno cancelado entre
encolado y envío (2.4), webhook duplicado y fuera de orden (4.3), token expirado o
revocado (5.2) y Redis caído con degradación a advisory lock (8.1).

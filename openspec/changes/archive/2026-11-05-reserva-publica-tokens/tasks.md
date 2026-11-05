# Tasks

## 1. Contrato y persistencia de reserva pública

- [x] 1.1 Escribir pruebas de contrato para los DTOs públicos estrictos, tenant slug, datos mínimos del paciente, E.164, consentimiento y claves de idempotencia; verificar que campos extra, datetimes inválidos y consentimientos incompletos fallen antes de mutar datos.
- [x] 1.2 Resolver el identificador Alembic posterior a `010_c05_contrato_clinico`, documentar la decisión en el change y crear una migración reversible para tokens públicos, expiración/revocación, propósito, índices tenant-scoped, timeout de pendientes e idempotencia; verificar upgrade/downgrade contra PostgreSQL.
- [x] 1.3 Escribir pruebas de repositorio para hash no reversible, búsqueda por tenant/turno/propósito, expiración, revocación y aislamiento; implementar los modelos y repositorios sin exponer ORM y verificar que ningún query devuelva tokens de otro tenant.
- [x] 1.4 Escribir pruebas de creación/reutilización de pacientes y opt-in durante una reserva pública, incluido el caso de cambio de teléfono que revoca tokens pendientes; implementar la integración con C-04 y verificar que no se almacenen datos clínicos innecesarios.

## 2. Servicios de disponibilidad, reserva y tokens

- [x] 2.1 Escribir pruebas de disponibilidad pública para duración, horarios, bloqueos, antelación, turnos activos y tenant inexistente; implementar el servicio público reutilizando el cálculo de C-06 y verificar resultados cronológicos sin fuga de existencia.
- [x] 2.2 Escribir pruebas de creación pública en estado `pendiente_confirmacion`, origen correcto, idempotencia equivalente/conflictiva y colisión concurrente; implementar el servicio transaccional con lock del profesional y verificar que como máximo una reserva ocupe el slot.
- [x] 2.3 Escribir pruebas de emisión y validación de tokens por propósito, token expirado, revocado, cruzado entre tenants y acción incompatible; implementar tokens opacos con hash, expiración y revocación y verificar que el valor crudo no aparezca en persistencia ni logs.
- [x] 2.4 Escribir pruebas de confirmar, cancelar y reprogramar desde token, incluyendo `RN-AG-01`, alternativas actualizadas y ausencia de efectos parciales; implementar las acciones delegando la máquina de estados de C-07 y verificar que no exista actualización genérica de estado.
- [x] 2.5 Escribir pruebas del contrato de seña pendiente, checkout handoff, timeout de 30 minutos, liberación del slot y revocación de tokens; implementar el adaptador de pago pendiente sin acreditar pagos y verificar compatibilidad con el evento idempotente que consumirá C-12.
- [x] 2.6 Documentar en el módulo el contrato de integración que C-12 debe consumir (checkout URL, estado pendiente, evento de acreditación y timeout) y verificar que la documentación no prometa procesamiento de pagos en C-08.

## 3. API pública y protección anti-abuso

- [x] 3.1 Escribir pruebas API para la vista pública por slug, disponibilidad, reserva, errores genéricos y respuestas DTO; implementar las rutas sin JWT con validación estricta, mensajes español-AR y ausencia de `tenant_id` confiado desde el cliente.
- [x] 3.2 Escribir pruebas API para headers de idempotencia, acciones por token, expiración, revocación, conflicto y rate limit; implementar límites separados para disponibilidad, reservas y acciones, incluyendo `429` y `Retry-After`, y verificar que los rechazos no creen turnos.
- [x] 3.3 Escribir pruebas de auditoría para éxitos, rechazos, expiraciones y bloqueos sin token crudo; implementar auditoría tenant-scoped con categorías trazables y verificar que el dueño pueda distinguir resultados sin acceder a secretos.
- [x] 3.4 Escribir pruebas de integración del timeout pendiente y concurrencia contra PostgreSQL/Redis o los dobles aprobados por el repositorio; implementar el job de liberación y verificar que el slot vuelva a estar disponible y los tokens queden revocados.

## 4. Frontend de reserva pública

- [x] 4.1 Escribir pruebas de cliente y tipos para tenant, disponibilidad, reserva, checkout pendiente y acciones por enlace; implementar el cliente público sin reutilizar el shell autenticado y verificar serialización UTC/offset y errores visibles.
- [x] 4.2 Escribir pruebas de componentes para selección de prestación, profesional, horario, datos de contacto y opt-in; implementar `/r/:slug` con accesibilidad básica y verificar que no muestre slots inválidos ni permita enviar sin datos requeridos.
- [x] 4.3 Escribir pruebas de interfaz para confirmación, cancelación, reprogramación, token expirado/revocado, conflicto y rate limit; implementar estados no optimistas y mensajes español-AR verificando que la vista refleje únicamente respuestas guardadas por el servidor.

## 5. Integración y validación del change

- [x] 5.1 Actualizar la documentación de rutas públicas y contratos de reserva para reflejar tokens separados, expiración, revocación, rate limits, timeout de pago y límites de C-08; verificar que las referencias a C-07 y C-12 sean consistentes.
- [x] 5.2 Ejecutar validación de OpenSpec, suite focalizada backend/frontend, pruebas de migración, build TypeScript y `git diff --check`; verificar aislamiento tenant, TDD de los escenarios críticos y que no se hayan modificado capacidades fuera del alcance.

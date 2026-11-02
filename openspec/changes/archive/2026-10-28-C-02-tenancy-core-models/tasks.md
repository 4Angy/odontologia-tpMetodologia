# Tasks — C-02 `tenancy-core-models`

> TDD estricto (R11): cada grupo escribe el test en rojo ANTES del código; mínimo 2 casos por comportamiento. Datos sintéticos/demo únicamente (R14).
> Contrato de comportamiento: `specs/tenancy/identidad/spec.md` (5 requirements, 12 escenarios). Decisiones: `design.md`. Exploración: `discovery/explore-c02-tenancy-core-models.md`.
> Cada tarea indica **cómo se verifica**. La columna "Escenario" referencia el escenario del spec que la tarea cubre.

## 1. Modelos base y migración `002`

- [x] 1.1 Escribir tests en rojo del modelo `TenantModel` (slug único global, `tz` default `America/Argentina/Buenos_Aires`, `created_at` con timezone) y del modelo `UsuarioModel` (`roles` como array enum, `activo`, `email` único por tenant), y verificar en rojo con `pytest backend/tests -k "models" -x`
- [x] 1.2 Implementar `backend/app/core/tenancy/models.py` con `TenantModel` y `UsuarioModel` (usando la `Base` compartida de `app/core/db.py` y el `TypeDecorator` para `ARRAY(enum)` de Postgres) y verificar que los tests de 1.1 pasan
- [x] 1.3 Escribir tests en rojo de la unicidad compuesta `(tenant_id, email)` en `usuario` y de la unicidad global de `tenant.slug`, y verificar en rojo que el error de integridad identifica la columna correcta
- [x] 1.4 Implementar los índices `ux_usuario_tenant_email` y `ux_tenant_slug` en la definición de los modelos y verificar que los tests de 1.3 pasan contra Postgres 16 real
- [x] 1.5 Escribir tests en rojo de `ConfigModel.senia_requerida` (bool, default false) conservando `antelacion_cancel_hs` (default 24) sin renombrarlo, y verificar en rojo
- [x] 1.6 Implementar la extensión de `config` con `senia_requerida` y verificar que los tests de 1.5 pasan
- [x] 1.7 Escribir la migración `002_tenancy_core_models` con `upgrade` (ALTER de `tenant` y `config`, CREATE de `usuario`, backfill de `slug`, índices) y `downgrade` que revierte **sólo** lo que `002` añadió, y verificar en rojo que `alembic downgrade -1` sobre el esquema de `0001` no toca `0001`
- [x] 1.8 Ejecutar `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` contra Postgres 16 real y verificar que el esquema final coincide con el de `0001` más lo de `002` (R6)
- [x] 1.9 Registrar en `CHANGES.md` y en `knowledge-base/04_modelo_de_datos.md` la desviación de `tenant.id` (String(64) en vez de uuid) y el nombre real de la columna `antelacion_cancel_hs`, con owner (C-06/C-07) y criterio de re-evaluación
- [x] 1.10 Escribir test en rojo del **escenario 3.3 (borde)**: tras aplicar la migración, ningún tenant queda con `slug` nulo (la columna es NOT NULL) y el seed del slice archivado (`backend/app/modules/agenda/seed_demo.py`) sigue funcionando con el `slug` del tenant demo, y verificar en rojo que hoy el seed insertaría un tenant sin `slug`
- [x] 1.11 Actualizar `backend/app/modules/agenda/seed_demo.py` para fijar el `slug` del tenant demo (o diferirlo a C-07 con owner declarado en `CHANGES.md`), y hacer que la migración termine con `ALTER TABLE tenant ALTER COLUMN slug SET NOT NULL` tras el backfill, y verificar que los tests de 1.10 pasan
- [x] 1.12 Escribir test en rojo del backfill: si dos tenants existentes derivan el mismo `slug`, la migración **falla con un mensaje explícito** que nombre a los tenants en conflicto (en vez de dejar un índice a medias), y verificar en rojo

## 2. Mixins, repositorio base y `UnitOfWork` (aislamiento por construcción)

- [x] 2.1 Escribir tests en rojo del `TenantMixin` (`tenant_id` NOT NULL + FK a `tenant`) y del `AuditMixin` (`created_at`, `updated_at`, `deleted_at`), y verificar en rojo con `pytest backend/tests -k "mixins"`
- [x] 2.2 Implementar `TenantMixin` y `AuditMixin` en `app/core/tenancy/models.py` y verificar que los tests de 2.1 pasan
- [x] 2.3 Escribir tests en rojo del `BaseRepository[T]`: `get_by_id` filtra siempre por `tenant_id`; `list` excluye `deleted_at` no nulo y pagina con `cursor`/`limit`; `add` y `flush` delegan en la sesión, y verificar en rojo
- [x] 2.4 Implementar `BaseRepository[T]` con el filtro por `tenant_id` como parámetro **interno** (no expuesto en los métodos) y la paginación por cursor opaco sobre `(created_at, id)`, `limit` por defecto 50 y máximo 200, y verificar que los tests de 2.3 pasan
- [x] 2.5 Escribir test en rojo del **escenario 1.1 (funcionamiento esperado)**: con dos tenants, el repositorio del tenant `A` no devuelve el usuario `u-1` del tenant `B`, y la query registrada incluye el filtro por `tenant_id`, y verificar en rojo
- [x] 2.6 Escribir test en rojo del **escenario 1.2 (borde)**: el mismo correo puede existir en dos tenants (unicidad por tenant, no global), y leerlo desde el tenant equivocado no devuelve filas, y verificar en rojo
- [x] 2.7 Implementar `UnitOfWork(tenant_id, session)` que expone repositorios ya scoped (la API no acepta `tenant_id`) y un único repositorio global explícito para `tenant` (el registro de tenants), y verificar que los tests de 2.5 y 2.6 pasan
- [x] 2.8 Escribir test en rojo de que **todo** acceso a datos de negocio pasa por un repositorio scoped: no existe forma pública de construir un repositorio de negocio sin `tenant_id`, y verificar en rojo
- [x] 2.9 Implementar la garantía estructural (el `UnitOfWork` es la única fábrica de repositorios y no expone un constructor público) y verificar que el test de 2.8 pasa

## 3. Middleware de tenant y error trazable

- [x] 3.1 Escribir tests en rojo del **escenario 2.1 (error de negocio)**: un token sin `tenant_id` recibe `403` con `code: RN-AU-01` y mensaje en español-AR, y **no** se ejecuta ninguna consulta de datos, y verificar en rojo con `pytest backend/tests -k "tenant_middleware"`
- [x] 3.2 Escribir test en rojo del **escenario 2.2 (borde)**: el `tenant_id` del cuerpo o de un header se ignora y la operación se resuelve con el del token, y verificar en rojo
- [x] 3.3 Implementar el middleware de tenant (403 con `RN-AU-01` vía el sobre de error de `app/core/errors.py`) y la dependencia que construye el `UnitOfWork` desde el `tenant_id` del JWT, y verificar que los tests de 3.1 y 3.2 pasan
- [x] 3.4 Verificar que el endpoint existente `POST /turnos/:id/cancelar` sigue respondiendo `403` con `RN-AU-01` ante un token inválido (compatibilidad con el spec `agenda/cancelacion-turno`) y que `openspec validate --specs` sigue en verde

## 4. Slug: unicidad global, normalización y formato

- [x] 4.1 Escribir test en rojo del **escenario 3.1 (error de negocio)**: crear un segundo tenant con un `slug` ya existente falla por la restricción de unicidad y el error identifica la columna `slug`, y verificar en rojo
- [x] 4.2 Escribir test en rojo del **escenario 3.2 (borde)**: un `slug` con espacios, mayúsculas o caracteres no kebab-case se normaliza a minúsculas y guiones simples, o se rechaza con mensaje en español-AR que indique el formato esperado, sin crear el tenant, y verificar en rojo
- [x] 4.3 Implementar la normalización y validación del `slug` (kebab-case) y verificar que los tests de 4.1 y 4.2 pasan
- [x] 4.4 Verificar que el error de slug duplicado responde `409` con el cuerpo `{code, message}` del contrato de `foundation/runtime` (código genérico documentado, porque la KB no define un RN para este caso) y con el mensaje en español-AR, y que el detalle técnico de la restricción queda **sólo en el log**, y verificarlo con un test que afirme la forma exacta del cuerpo

## 5. Roles acumulables y permiso por unión

- [x] 5.1 Escribir test en rojo del **escenario 4.1 (funcionamiento esperado)**: un usuario con `recepcion` + `odontologo` puede leer la agenda y registrar su propia atención, sin roles extra ni un segundo usuario, y verificar en rojo con `pytest backend/tests -k "roles"`
- [x] 5.2 Escribir test en rojo del **escenario 4.2 (borde)**: un usuario sin roles no tiene permiso efectivo, y un usuario `dueno` con `activo = false` tampoco, y verificar en rojo
- [x] 5.3 Implementar el cómputo de permiso por unión de roles (DD-06 / RN-AU-04) como función pura testeable y verificar que los tests de 5.1 y 5.2 pasan
- [x] 5.4 Verificar que el enum de Postgres de `roles` contiene exactamente `recepcion`, `odontologo` y `dueno` (test que consulta `pg_enum`), y que su valor por defecto en el enum coincide con §03

## 6. Auditoría mínima y borrado lógico

- [x] 6.1 Escribir test en rojo del **escenario 5.1 (funcionamiento esperado)**: tras crear y luego modificar un registro, `created_at` se conserva, `updated_at` es posterior y `deleted_at` queda vacío, y verificar en rojo con `pytest backend/tests -k "auditoria"`
- [x] 6.2 Escribir test en rojo del **escenario 5.2 (borde)**: tras el borrado lógico la fila sigue existiendo con `deleted_at` informado, desaparece de los listados por defecto y el registro que la referencia no queda inconsistente, y verificar en rojo
- [x] 6.3 Implementar el borrado lógico (el `list` por defecto excluye `deleted_at IS NOT NULL`) y la actualización de `updated_at` en el flush del repositorio, y verificar que los tests de 6.1 y 6.2 pasan

## 7. Seed de demostración idempotente

- [x] 7.1 Escribir test en rojo del **escenario 6.1 (funcionamiento esperado)**: ejecutar el seed dos veces deja el mismo número de tenants y de usuarios, sin duplicados, y verificar en rojo con `pytest backend/tests -k "seed"`
- [x] 7.2 Escribir test en rojo del **escenario 6.2 (borde)**: con el tenant `demo` ya existente y un correo de usuario modificado, el seed no recrea el tenant, no duplica usuarios y no sobrescribe el correo, y verificar en rojo
- [x] 7.3 Implementar `python -m app.seed` con `INSERT ... ON CONFLICT DO NOTHING` sobre `tenant.slug` y `(tenant_id, email)`, creando 1 tenant `demo` + 3 usuarios (uno por rol + uno con los 3 roles), y verificar que los tests de 7.1 y 7.2 pasan
- [x] 7.4 Verificar que el seed **no** se ejecuta al arrancar la aplicación: un test que levanta la app sin `SEED_DEMO` y comprueba que no se crea ningún tenant, y documentar en `backend/README.md` el comando y su idempotencia

## 8. Verificación integrada del change

- [x] 8.1 Ejecutar la suite completa del backend contra Postgres 16 real y verificar que todo queda en verde, incluyendo los 12 escenarios de `specs/tenancy/identidad/spec.md`
- [x] 8.2 Ejecutar `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` en CI y verificar que la reversibilidad se sostiene con el esquema ampliado (R6)
- [x] 8.3 Verificar el ciclo completo de seed sobre el compose: `docker compose exec api python -m app.seed` dos veces, y comprobar que el conteo de tenants y usuarios no cambia entre corridas
- [x] 8.4 Ejecutar `openspec validate C-02-tenancy-core-models --strict` y verificar que el change y sus specs validan
- [x] 8.5 Revisar contra `knowledge-base/` que no quedó ninguna decisión de dominio sin justificación: `tenant`, `usuario`, `config`, roles, seed y nombre de la columna de anticipación están respaldados por §03, §04, §05, §08 y §09, y actualizar la KB con las desviaciones acordadas (`tenant.id`, `antelacion_cancel_hs`)
- [x] 8.6 Verificar de forma cruzada que el spec nuevo no contradice los specs existentes: revisar `openspec/specs/foundation/runtime/spec.md` (sobre de error `{code, message, action?}`) y `openspec/specs/agenda/cancelacion-turno/spec.md` (códigos RN y aislamiento) contra cada escenario de `tenancy/identidad`, y dejar constancia de la revisión en el design

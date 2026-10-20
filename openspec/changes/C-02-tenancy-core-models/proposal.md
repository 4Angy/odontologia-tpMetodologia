# Proposal — C-02 `tenancy-core-models`

> Change GATE 1. Dependencia: `C-01 foundation-setup-decisiones` (archivado ✓). Governance **CRITICO**: todo el dominio referencia estos modelos y un error de filtro expone datos cruzados entre consultorios (DD-04).
> Decisiones tomadas en `discovery/explore-c02-tenancy-core-models.md` (skill `visual-explore-options`; contexto leído con el MCP `filesystem`).

## Why

C-01 dejó el runtime (settings, health, errores, compose, CI) pero **no dejó los modelos de dominio**: hoy el único esquema del repo es la migración `0001_cancelacion_turno`, que creó `tenant` y `config` en forma mínima y ningún `usuario`. Sin `tenant`, `usuario` y `config` completos no existe el aislamiento multi-tenant, y sin aislamiento el resto del producto (agenda, pacientes, caja) no se puede construir sobre una base sana: C-03, C-04, C-06, C-07 y todos los demás dependen de este change.

Es además el change donde la **regla dura R1** (ninguna query de negocio sin `tenant_id` del JWT) se convierte en estructura y no en disciplina: el riesgo #1 de la arquitectura del proyecto es que un consultorio vea datos de otro, y ese riesgo se paga una sola vez, acá.

## What Changes

**Modelos base multi-tenant (completan los que `0001` ya creó):**

- `tenant`: se le agregan `slug` (texto, **único global**, kebab-case), `email_contacto`, `tz` (default `America/Argentina/Buenos_Aires`) y `created_at`. `id` permanece `String(64)` — desviación documentada respecto de §04 (`uuid`), porque `turno.tenant_id` (FK creado en `0001`) es `String(64)` y cambiar la PK obligaría a re-migrar el slice archivado.
- `usuario` (tabla nueva): `id`, `tenant_id` NOT NULL + FK, `nombre`, `email` (**único por tenant**), `password_hash`, `roles` como **array enum** `recepcion|odontologo|dueno`, `activo` (bool), `created_at`. Índice `(tenant_id, email)`.
- `config` (completa la de `0001`): `antelacion_cancel_hs` (ya existe, default 24) + `senia_requerida` (bool, default false).

**Capa de acceso a datos con aislamiento por construcción:**

- `TenantMixin` (`tenant_id` NOT NULL + FK a `tenant`) y `AuditMixin` (`created_at`, `updated_at`, `deleted_at`) como mixins reutilizables por los módulos siguientes.
- `BaseRepository[T]` genérico con `get_by_id`, `list(cursor, limit)`, `add`, `flush`.
- `UnitOfWork`: se construye con el `tenant_id` del JWT y expone repositorios **ya scoped** — la API del repositorio **no acepta `tenant_id`**, porque el filtro lo aplica el `UnitOfWork`. Única excepción, con nombre explícito: el repositorio de `tenant`, que es global por naturaleza (es el registro de tenants).
- Paginación `cursor`/`limit` base: cursor opaco sobre `(created_at, id)`, límite por defecto 50 y máximo 200.

**Identidad y errores:**

- Middleware de tenant obligatorio: sin `tenant_id` en el JWT → **403 con `code: RN-AU-01`** (no 404 con fuga de información), conforme a RN-AU-01 y R9.

**Migración y seed:**

- Migración `002`: **altera** `tenant` y `config` y **crea** `usuario`, con `downgrade` reversible (R6). La numeración 003-012 del plan no cambia.
- Seed demo **por comando explícito** `python -m app.seed`, idempotente: 1 tenant (`slug: demo`) + 3 usuarios demo (uno por rol + uno con los 3 roles, para probar el caso "todo en una persona" de DD-06). Nunca se ejecuta solo al arrancar.

**No breaking changes**: no se altera ningún requisito de los specs existentes (`agenda/cancelacion-turno`, `foundation/runtime`).

## Capabilities

### New Capabilities

- `tenancy/identidad`: aislamiento por tenant en la capa de datos y en el borde HTTP (unicidad compuesta, slug global, roles acumulables, auditoría mínima y seed idempotente). Es el dominio "Tenancy/identidad" de `knowledge-base/04_modelo_de_datos.md`.

### Modified Capabilities

- (ninguna — `agenda/cancelacion-turno` y `foundation/runtime` conservan sus requisitos sin cambios)

## Impact

**Código afectado**

- `backend/app/core/db.py`: `Base` compartida ya existe (C-01); ahora recibe los mixins y los modelos nuevos.
- `backend/app/core/tenancy/`: nuevo módulo con `models.py` (`TenantModel`, `UsuarioModel`, `ConfigModel`), `repository.py` (`BaseRepository[T]`, `TenantsRepository` global, `UsuariosRepository` scoped), `unit_of_work.py` y `deps.py` (middleware de tenant, `UnitOfWork` como dependencia).
- `backend/app/modules/agenda/models.py`: pasa a usar `TenantMixin`/`AuditMixin`; su `Base` y su tabla `turno` no cambian de forma.
- `backend/app/seed.py`: comando de seed demo idempotente.
- `backend/alembic/versions/0002_tenancy_core_models.py`: nueva migración con `upgrade`/`downgrade`.

**Infraestructura y datos**

- `backend/app/core/db.py` y `alembic/env.py`: `import_models()` ya recorre `app/modules/*`; C-02 agrega el módulo `tenancy` a ese recorrido.
- `openspec/specs/tenancy/identidad/spec.md`: spec nuevo (5 requirements, 12 escenarios).
- Sin cambios en `docker-compose.yml`, `.env.example` ni en el CI: C-02 no introduce variables ni servicios nuevos.

**APIs**: no agrega endpoints públicos. El middleware de tenant protege los endpoints de negocio que ya existen y los que vendrán; su comportamiento observable (403 con `code: RN-AU-01`) queda especificado en `tenancy/identidad`.

**Downstream**: C-03 (auth y RBAC sobre `usuario`), C-04/C-05/C-06/C-07 (modelos de negocio con `TenantMixin` + `AuditMixin` y repositorios scoped), C-11 (`config.senia_requerida`), C-13 (RLS futuro y auditoría).

**Riesgos y gobernanza**: R1/R2 (aislamiento), R3/R4 (DTOs, `extra='forbid'`), R5 (centavos), R6 (migración reversible), R9 (`code` RN-XX), R11 (TDD), R14 (datos sintéticos). Governance CRITICO: un error de filtro expone datos de un consultorio a otro.

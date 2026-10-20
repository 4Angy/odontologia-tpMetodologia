# Design — C-02 `tenancy-core-models`

> Decisiones tomadas en `discovery/explore-c02-tenancy-core-models.md` (skill `visual-explore-options`; contexto de KB leído con el MCP `filesystem`). Selección del usuario: eje 1 → A, eje 2 → A, eje 3 → A, eje 4 → A.
> Ver `proposal.md` para la motivación. Este documento explica **cómo** se implementa.

## Context

Estado real del repo al 2026-10-19 (verificado, no supuesto):

- La migración `0001_cancelacion_turno` —creada por el change archivado `2026-10-06-cancelar-turno-liberar-horario`— ya creó `tenant` (`id` String(64) PK, `nombre`), `config` (`tenant_id` PK+FK, `antelacion_cancel_hs` default 24) y `turno` (`tenant_id` String(64) NOT NULL + FK a `tenant.id`).
- **No existe** la tabla `usuario`. No existe `BaseRepository`, `UnitOfWork`, `TenantMixin` ni `AuditMixin`. No hay middleware de tenant.
- C-01 dejó la infraestructura: `app/core/db.py` con la `Base` compartida e `import_models()`, settings por env con fail-fast, sobre de error `{code, message, action?}`, health checks, compose y CI.
- La KB §04 fija el contrato de dominio: `tenant` (`id` uuid PK, `slug` unique global kebab-case, `nombre`, `email_contacto`, `tz`, `created_at`), `usuario` (`email` unique por tenant, `roles` array enum, `activo`, `password_hash`), `config` (`antelacion_hs`, `senia_monto`, `plantillas`), la regla *"toda tabla de negocio lleva `tenant_id` NOT NULL + FK; unicidades y búsquedas siempre compuestas con `tenant_id`"*, y el seed (1 tenant demo + 3 usuarios demo, uno con los 3 roles).

Restricciones que modelan el diseño: **R1/R2** (aislamiento por `tenant_id` del JWT; nunca del frontend), **RN-AU-01** (sin tenant → 403, no 404 con fuga), **RN-GL-02** (auditoría en toda mutación), **R3/R4** (DTOs Pydantic v2 con `extra='forbid'`), **R5** (centavos enteros), **R6** (migraciones reversibles), **R7** (timestamptz UTC), **R9** (`code` RN-XX), **R11** (TDD estricto), **R14** (datos sintéticos), **DD-04** (row-level; RLS diferido) y **DD-06** (roles acumulables, permiso = unión).

## Goals / Non-Goals

**Goals:**

- Dejar `tenant`, `usuario` y `config` completos y fiel a la KB, **sin tocar** la migración `0001` ni el slice archivado.
- Convertir R1 de "regla que hay que recordar" en "regla que la estructura impide violar".
- Dejar el patrón (`TenantMixin`, `AuditMixin`, `BaseRepository[T]`, `UnitOfWork`, cursor/limit) que C-04..C-07 van a replicar sin volver a decidirlo.
- Dejar el seed demo **idempotente y explícito**, con el caso "todo en una persona" (DD-06) ya sembrado.

**Non-Goals:**

- **No** implementa autenticación: `password_hash` y `activo` quedan como columnas; el login, el refresh rotativo y la revocación de familia son de C-03 (RN-AU-02).
- **No** implementa RLS de Postgres: DD-04 la marca como endurecimiento posterior (C-13).
- **No** agrega endpoints de negocio. El middleware de tenant es la única pieza de borde; los routers de C-03..C-07 los consumirán.
- **No** define el catálogo de roles: §04 los define embebidos en v1.
- **No** toca `config.plantillas` ni las ventanas de recordatorio: C-06 y C-09 son sus dueños.
- **No** implementa la tabla `lista_espera`, `paciente` ni ninguna otra: son de C-04, C-05 y C-10.

## Decisions

1. **La migración `002` altera `tenant` y `config` y crea `usuario`; no reconstruye nada.**
   - Rationale: `0001` es el seed documentado del slice archivado y sus 4 archivos de test siguen siendo válidos. Reconstruir `tenant`/`config` obligaría a re-integrar el slice y a tirar código ya validado, a cambio de limpieza de schema que se puede lograr igual con `ALTER`.
   - Alternativa descartada — **drop & recreate**: schema exacto según §04 desde el día 1, pero descarta filas (el seed demo en dev), rompe el slice archivado y vuelve frágil el `downgrade` de R6.

2. **`tenant.id` permanece `String(64)`; se documenta la desviación respecto de §04 (`uuid`).**
   - Rationale: `turno.tenant_id` —creado en `0001`— es `String(64)` con FK a `tenant.id`. Cambiar el tipo de la PK obliga a migrar también esa FK y a re-migrar el slice archivado. El identificador es opaco: su formato no lo usa ninguna regla de negocio. La desviación queda anotada en `CHANGES.md` y en la KB como deuda para C-06/C-07.
   - Alternativa descartada — migrar a `uuid` en `002`: más fiel a §04, pero disruptivo y sin ganancia funcional en v1.
   - **Consecuencia a vigilar**: si en el futuro el id pasa a uuid, la migración debe alterar `tenant.id` y `turno.tenant_id` en el mismo paso.

3. **`usuario.roles` es un `ARRAY` de un enum de Postgres (`recepcion|odontologo|dueno`), con un `TypeDecorator` de SQLAlchemy.**
   - Rationale: es lo que dice la KB (§04: *"roles (array enum: recepcion/odontologo/dueno)"*, *"embebido como array en v1"*). Una fila por usuario, sin tabla puente. La unión de permisos (DD-06/RN-AU-04) es `set(roles) ⊇ {rol}` en memoria, sin query.
   - Alternativa descartada — **tabla puente `usuario_rol` + catálogo `rol`**: normalizado y extensible (metadatos por rol), pero **contradice la KB** y suma dos tablas a un change CRITICO. Si alguna vez hacen falta metadatos por rol, entra como change propio con su ADR.
   - **Consecuencia a documentar**: agregar un rol es una migración (`ALTER TYPE ... ADD VALUE`), no un cambio de dominio. El enum vive en Postgres, no en Python.

4. **El `UnitOfWork` se construye con el `tenant_id` y expone repositorios ya scoped: la API del repositorio no acepta `tenant_id`.**
   - Rationale: R1 es la regla dura #1 del proyecto y el riesgo #1 de la arquitectura (DD-04). Con el filtro aplicado por el `UnitOfWork`, olvidar `tenant_id` deja de ser una posibilidad sintáctica: no es que haya que acordarse, es que no hay dónde ponerlo. Los tests de aislamiento pasan a ser triviales y el middleware de tenant queda como segunda barrera, no como la única.
   - Alternativa descartada — **`tenant_id` explícito en cada llamada** (`repo.get_by_id(tenant_id, id)`, el patrón del slice archivado): explícito y sin refactor, pero convierte R1 en un exercise de memoria en cada método nuevo.
   - **Única excepción, con nombre explícito**: el repositorio de `tenant` es global por naturaleza (es el registro de tenants; se busca por `slug` para los links públicos). Se expone como `uo.tenants` y se documenta como la excepción, para que la excepción sea visible y no una puerta oculta.

5. **`BaseRepository[T]` genérico con `get_by_id`, `list`, `add`, `flush`; el filtro por `tenant_id` es un parámetro interno del repositorio, no de sus métodos.**
   - Rationale: un solo lugar donde se escribe el filtro (`WHERE tenant_id = :tenant_id`), reutilizado por todos los módulos. `T` es el tipo del modelo, y el repositorio genérico cubre `get_by_id`/`add`/`flush`; los métodos específicos (búsquedas por apellido, por teléfono) viven en el repositorio del módulo, siempre heredando el filtro.
   - Alternativa descartada — un repositorio concreto por módulo sin base común: se repite el filtro en cada uno y cada repetición es una oportunidad de olvido.

6. **Paginación `cursor`/`limit`: cursor opaco sobre `(created_at, id)`, orden ascendente, `limit` por defecto 50 y máximo 200.**
   - Rationale: el cursor **compuesto** evita el salto de filas cuando dos filas comparten `created_at` (muy probable en un seed o en una importación). Es opaco (base64) para que el cliente no dependa del formato. El máximo de 200 evita que un `limit` enorme dispare una extracción de datos de salud (R13).
   - Alternativa descartada — cursor por `id` solamente: `id` no es monotónico en el tiempo, así que "después del último visto" no es estable.
   - Alternativa descartada — paginación por `offset`: se degrada con tablas grandes y salta filas si hay inserciones concurrentes.

7. **`AuditMixin` con `created_at`, `updated_at` y `deleted_at`; el borrado es lógico.**
   - Rationale: RN-GL-02 exige que toda mutación deje rastro de quién/cuándo/qué. `deleted_at` permite el borrado lógico sin perder la fila que un turno o un cobro referencian. `updated_at` lo actualiza el repositorio en cada flush, no cada endpoint: el sello de tiempo no depende de que el endpoint se acuerde.
   - Alternativa descartada — timestamps sólo en `created_at`: no permite saber cuándo cambió un registro, que es la mitad de "qué cambió" (RN-GL-02).

8. **El middleware de tenant responde 403 con `code: RN-AU-01` cuando el JWT no trae `tenant_id`.**
   - Rationale: RN-AU-01 lo dice literal ("Sin tenant no hay respuesta (403, no 404 con fuga)"). El 404 con fuga sería indistinguishable de "no existe" y confirmaría la existencia de recursos de otro tenant. El `code` trazable (R9) permite al frontend distinguir "no tenés tenant" de "no encontraste el recurso".
   - Alternativa descartada — 404: fuga de información. Alternativa descartada — 401: el token es válido; el problema es que no habilita tenant.

9. **El seed demo es un comando explícito e idempotente (`python -m app.seed`), nunca automático al arrancar.**
   - Rationale: si `SEED_DEMO=true` quedara en un entorno real, un seed automático sembraría datos demo en producción. Con el comando explícito, esa configuración no tiene poder de daño. La idempotencia se garantiza en la base con `INSERT ... ON CONFLICT DO NOTHING` sobre `slug` y `(tenant_id, email)`.
   - Alternativa descartada — seed automático en el lifespan: fricción cero en dev, a cambio de un accidente esperando una variable mal puesta.

10. **`config` crece sólo con `senia_requerida` (bool, default false).**
    - Rationale: RN-CO-02 dice que la seña es *opcional por tenant*, y la KB §04 (seed) fija `senia_requerida = false`. La KB también menciona `plantillas` en `config` y ventanas de recordatorio; **esas no entran acá**: C-06 extiende `config` con las ventanas de anticipación y C-09 es dueño de la tabla `plantilla`. Añadir campos sin dueño violate la consigna de no incorporar decisiones de dominio sin justificar.
    - Alternativa descartada — meter `plantillas` y ventanas ahora: duplicaría el trabajo de C-06/C-09 y crearía dos fuentes de verdad para las plantillas.

11. **El nombre de la columna de anticipación es `antelacion_cancel_hs` (no `antelacion_hs`).**
    - Rationale: decisión ya fijada en el change archivado (`design.md`: *"Nombre preciso fijado aquí: `antelacion_cancel_hs` (prevalece sobre `antelacion_hs` de C-02/KB-ERD)"*) y ya materializada en `0001`. C-02 no la renombra: renombrar sería una migración sin ganancia y rompería el slice.
    - Consecuencia: la KB §04 y el ERD quedan con un nombre desalineado; se actualizan en C-02 para que la KB sea la fuente de verdad.

12. **RLS de Postgres no se implementa en este change.**
    - Rationale: DD-04 la ubica como endurecimiento posterior, no día 1, y RLS exige `FORCE ROW LEVEL SECURITY` y políticas por tabla que sólo tienen sentido cuando el modelo esté completo. C-13 es su dueño, y este change deja la base para aplicarla: toda tabla de negocio con `tenant_id` y FK a `tenant`.
    - Alternativa descartada — RLS ahora: sumaría políticas, roles de DB y testing de dos capas de aislamiento en el change que ya es CRITICO, para un beneficio que C-13 recoge igual.

13. **`tenant.slug` termina `NOT NULL` después del backfill, y el seed del slice archivado se actualiza en este change.**
    - Rationale: **Postgres admite múltiples valores NULL en un índice único** (verificado en la revisión crítica: `CREATE UNIQUE INDEX` sobre una columna nullable acepta N filas con NULL). Un `slug` NULL no dispararía la restricción, así que dos tenants sin slug pasarían el índice y el contrato de "slug único global" quedaría **sin garantía** — y el link público `/r/:slug` no podría resolverlos. Por eso la migración termina con `slug NOT NULL`.
      Además, `backend/app/modules/agenda/seed_demo.py` —del slice archivado— inserta el tenant demo **sin `slug`** (línea 21: `TenantModel(id=TENANT_DEMO, nombre="Consultorio Demo")`). Con la columna nullable dejaría un tenant sin slug; con la columna NOT NULL el seed archivado rompería con `IntegrityError`. C-02 actualiza ese seed para fijar el `slug` del tenant demo, o difiere el cambio a C-07 con owner explícito. **No puede quedar sin dueño.**
    - Alternativa descartada — dejar `slug` nullable y confiar en el índice: el índice no protege el caso NULL; el contrato quedaría sin garantía verificable.
    - Alternativa descartada — índice parcial `WHERE slug IS NOT NULL`: admite los NULL igual de libre; sólo esconde el problema.

## Risks / Trade-offs

- [Riesgo] Un repositorio nuevo podría forgets el filtro y filtrar datos cruzados → Mitigación: el filtro vive en `BaseRepository` y se aplica solo; el `UnitOfWork` es la única forma de obtener un repositorio, y no expone un constructor público. La excepción global (`tenant`) tiene nombre explícito. Cada módulo nuevo hereda el patrón y C-13 puede verificar que no exista un repo sin scope con un test de arquitectura.
- [Riesgo] El enum de Postgres no se puede quitar un valor fácilmente y agregar un rol exige migración → Mitigación: documentado como consecuencia de la Decisión 3; el enum tiene 3 valores estables desde §03 y ningún flujo exige un rol nuevo (SU-02: el rol "encargado" se crea sólo si la validación lo pide).
- [Riesgo] La desviación `tenant.id` String(64) vs uuid de §04 puede morder más adelante → Mitigación: anotada en `CHANGES.md` y en la KB con owner (C-06/C-07) y criterio de re-evaluación (cuando el volumen de tenants justifique el cambio y en el mismo paso que `turno.tenant_id`).
- [Riesgo] `deleted_at` (borrado lógico) puede hacer que los listados olviden filtrar los borrados y muestren filas que "no existen" → Mitigación: el borrado lógico se aplica **sólo** donde una regla de negocio lo pida; el filtro por defecto de `list` excluye `deleted_at IS NOT NULL`, y cualquier excepción (auditoría del dueño) se pide explícitamente.
- [Riesgo] `roles` como `ARRAY` no se puede indexar para consultar "usuarios con rol X" → Mitigación: la consulta por rol no está en el scope de C-02 (y C-03 no la necesita: el permiso se evalúa sobre el usuario autenticado). Si aparece, se resuelve con un índice GIN en C-03/C-13 o con la tabla puente.
- [Riesgo] El seed del slice archivado (`backend/app/modules/agenda/seed_demo.py`) inserta un tenant **sin `slug`** → con `slug` NOT NULL el seed rompe con `IntegrityError`; con la columna nullable, el contrato de unicidad global queda sin garantía (Postgres admite N NULL en un índice único) → Mitigación: Decisión 13 — C-02 actualiza ese seed o difiere el cambio a C-07 con owner declarado, más un test que falle si algún tenant queda con `slug` nulo.
- [Trade-off] Repositorio tenant-scoped → el patrón del slice archivado (`TurnoRepository(session)` con `tenant_id` explícito) queda distinto al nuevo → Se acepta: C-07 re-integrará el slice sobre el patrón nuevo, que es justamente el valor de C-02. El slice archivado sigue funcionando hasta entonces.
- [Trade-off] Seed por comando → un paso manual en el onboarding → Se compensa con el entrypoint del compose (`docker compose exec api python -m app.seed`) y con `SEED_DEMO` como bandera documentada.
- [Trade-off] Migración que altera en vez de reconstruir → el esquema de `tenant` queda con columnas de dos procedencias (`0001` y `002`) → Se acepta: la historia de migraciones queda explícita y reversible, que es lo que pide R6.

## Migration Plan

1. **Orden de aplicación** (nada de esto se ejecuta en este change: es el plan para quien lo implemente):
   - `002_tenancy_core_models`:
     - `ALTER TABLE tenant ADD COLUMN slug text NULL` (nullable **sólo** durante el backfill), `email_contacto text NULL`, `tz text NOT NULL DEFAULT 'America/Argentina/Buenos_Aires'`, `created_at timestamptz NOT NULL DEFAULT now()`.
     - Backfill determinista: `UPDATE tenant SET slug = <kebab-case derivado de nombre> WHERE slug IS NULL`. Si dos tenants derivan el mismo slug, la migración **falla con un mensaje explícito** en vez de aplicar un índice que no se puede crear, y el operador resuelve el choque a mano.
     - `ALTER TABLE tenant ALTER COLUMN slug SET NOT NULL` — Postgres admite N valores NULL en un índice único, así que la columna tiene que ser NOT NULL para que "slug único global" sea una garantía y no una intención (Decisión 13).
     - `CREATE UNIQUE INDEX ux_tenant_slug ON tenant (slug)`.
     - `ALTER TABLE config ADD COLUMN senia_requerida boolean NOT NULL DEFAULT false`.
     - `CREATE TABLE usuario (id varchar(64) PK, tenant_id varchar(64) NOT NULL REFERENCES tenant(id), nombre text NOT NULL, email text NOT NULL, password_hash text NOT NULL, roles <array enum> NOT NULL, activo boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now())`.
     - `CREATE UNIQUE INDEX ux_usuario_tenant_email ON usuario (tenant_id, email)`.
     - **Upstream obligatorio**: `backend/app/modules/agenda/seed_demo.py` (slice archivado) inserta el tenant demo **sin `slug`**. Con `slug` NOT NULL el seed rompería con `IntegrityError`: este change lo actualiza para fijar `slug = 'demo'`, o difiere el cambio a C-07 con owner declarado (Decisión 13).
   - `downgrade` revierte **exactamente** lo anterior: borra los índices, la tabla `usuario` y las columnas agregadas (R6). La migración `0001` no se toca en ninguna dirección.
2. **Sin downtime**: son `ADD COLUMN` con default, `CREATE TABLE` y `CREATE INDEX`; ninguna operación bloquea escrituras de forma significativa en tablas con el volumen de v1.
3. **Rollback**: `alembic downgrade -1` devuelve el esquema al de `0001`. El código nuevo (repositorios scoped) depende de las columnas nuevas, así que el rollback de código va junto con el de esquema.
4. **Post-aplicación**: `python -m app.seed` crea el tenant `demo` + los 3 usuarios demo; el seed es idempotente y se puede correr las veces que haga falta.
5. **Verificación de reversibilidad**: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head`, contra Postgres 16 real (mismo criterio que C-01 y que el job `backend` del CI).

## Open Questions

- **PA-04** (antelación por prestación vs. una global): afecta a `config` en C-06, no a C-02. Diferible.
- **SU-02** (rol "encargado"): la KB dice que no hay rol intermedio en v1; si la validación lo pide, entra como `ALTER TYPE` en el enum (Decisión 3). Diferible.
- **Volume de tenants**: el `id` como `String(64)` es aceptable mientras los tenants sean consultorios; el cambio a uuid se reevalúa con datos reales (C-13).
- **Consultas por rol**: no hay en v1 una consulta "usuarios con rol X". Si aparece, se resuelve con índice GIN o con la tabla puente (Decisión 3).

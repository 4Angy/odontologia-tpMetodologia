# Explore: C-02 `tenancy-core-models`

- Fecha: 2026-10-19
- Modo: `visual-explore-options` (thinking-partner, NO implementación, NO codigo)
- Change: `C-02 tenancy-core-models` (GATE 1, único, dependencia: C-01 ✓ archivado)
- Governance declarado: **CRITICO** (todo el dominio referencia estos modelos; un bug de filtro expone datos cruzados — DD-04)
- Fuentes leidas **con el MCP `filesystem`** (raíz del proyecto, vía `docs/skills-mcp/tools/mcp-fs.js`): `knowledge-base/04_modelo_de_datos.md`, `knowledge-base/03_actores_y_roles.md`; y de forma nativa `knowledge-base/05_reglas_de_negocio.md` (RN-AU-01, RN-GL-02), `knowledge-base/08_arquitectura_propuesta.md` §Patrones, `knowledge-base/09_decisiones_y_supuestos.md` (DD-04, DD-06), `CHANGES.md` (C-02), `backend/alembic/versions/0001_cancelacion_turno.py`, `backend/app/modules/agenda/models.py`.

---

## 0. Decisiones tomadas (selección del usuario, 2026-10-19)

| Eje | Opción elegida | Consecuencia |
|-----|----------------|--------------|
| 1 — Migración `002` | **A — alterar y completar** | `002` agrega columnas a `tenant`/`config` y crea `usuario`; `0001` no se toca |
| 2 — `roles` | **A — `ARRAY` de enum de Postgres** | 1 columna, 1 fila por usuario, tal como dice la KB (§04) |
| 3 — Aislamiento R1 | **A — repositorio tenant-scoped** | El filtro lo aplica el `UnitOfWork`; la API del repo no pide `tenant_id` |
| 4 — Seed demo | **A — comando explícito** | `python -m app.seed`, idempotente; no corre solo al arrancar |

> **Nota sobre la ficha inicial** (`docs/skills-mcp/investigacion.md` §2): la ficha declaraba `C-01 foundation-setup-decisiones` como change candidato para el punto 7 del TP. Como C-01 fue implementado, verificado y **archivado** durante esta sesión, el ejercicio se realiza sobre **C-02**, el siguiente del roadmap (GATE 1, desbloqueado, camino crítico y desbloquea todo lo demás). El cambio de elección queda justificado acá, como pide la consigna.

---

## 1. Restricciones duras que acotan las opciones

- **R1 / RN-AU-01**: ninguna query de negocio sin `tenant_id` del JWT; sin tenant → **403**, no 404 con fuga.
- **KB §04**: `tenant` (`id` uuid PK, `slug` text unique global kebab-case, `nombre`, `email_contacto`, `tz` default `America/Argentina/Buenos_Aires`, `created_at`); `usuario` (`id`, `tenant_id` FK, `nombre`, `email` unique **por tenant**, `password_hash`, `roles` **array enum** `recepcion/odontologo/dueno`, `activo` bool, `created_at`), índice `(tenant_id, email)`; "toda tabla de negocio lleva `tenant_id` NOT NULL + FK a `tenant`; unicidades y búsquedas siempre compuestas con `tenant_id`".
- **DD-04**: multi-tenant row-level; RLS de Postgres es endurecimiento posterior, **no** día 1.
- **DD-06 / RN-AU-04**: un usuario puede acumular los 3 roles; el permiso efectivo es la unión.
- **RN-GL-02**: toda mutación escribe auditoría mínima (quién/cuándo/qué).
- **R6**: toda migración Alembic con `downgrade` reversible.
- **Estado real del repo**: la migración `0001_cancelacion_turno` (del change archivado) **ya creó** `tenant` (`id` String(64) PK, `nombre`), `config` (`tenant_id` PK+FK, `antelacion_cancel_hs` default 24) y `turno` (`tenant_id` String(64) NOT NULL + FK a `tenant.id`).

## 2. El problema que las opciones resuelven

C-02 es el dueño de `tenant`, `usuario` y `config` según el plan, pero **`0001` ya hizo dos de las tres tablas** con un esquema mínimo, y `turno.tenant_id` referencia `tenant.id` con tipo `String(64)`. Hay que reconciliar el plan con el estado real sin romper R6, sin tirar el slice archivado, y sin que R1 dependa de la disciplina de cada llamada.

---

## 3. Eje 1 — Migración `002` y las tablas que `0001` ya creó

### Opcion A: `002` altera y completa las tablas que ya existen
* **Que es?:** La migración `002` **agrega** columnas a `tenant` y `config` (las de `0001`) y crea `usuario` nueva. `0001` no se toca.
* **Por que y como:** `tenant` queda con `slug` (unique, backfill desde `nombre` para los tenants existentes), `tz`, `email_contacto`, `created_at`; `config` con `senia_requerida`; `usuario` nace con `(tenant_id, email)` unique e índice `(tenant_id, email)`. `downgrade` revierte sólo lo que `002` añadió (R6). Respeta el estado real: el slice archivado y sus tests siguen funcionando.
* **Trade-off:** Pro: no se toca código validado, `0001` sigue siendo el seed documentado / Contra: `tenant.id` queda como `String(64)` en vez del **uuid** que pide la KB (§04) → desviación a documentar
* **Esquema:**
```text
0001 (existente)  tenant(id,nombre)  config(tenant_id,antelacion_cancel_hs)
002  (C-02)       + tenant.slug/tz/email_contacto/created_at
                  + config.senia_requerida
                  + usuario(tenant_id,email,password_hash,roles,activo)
```

### Opcion B: `002` reconstruye `tenant` y `config` desde la KB
* **Que es?:** `002` hace `DROP` de `tenant` y `config` y las recrea **exactas** como las define la KB, más `usuario`.
* **Por que y como:** El esquema queda alineado con §04 en un solo paso. Es seguro ahora porque v1 no salió: lo único que hay es el seed demo, que se regenera.
* **Trade-off:** Pro: schema limpio y fiel a la KB desde el día 1 / Contra: descarta filas existentes (en dev: el seed; en prod: nada todavía), rompe el slice archivado que espera esas tablas → hay que re-integrarlo
* **Esquema:**
```text
0001 (existente)  tenant(min)  config(min)  turno
002  (C-02)       DROP+CREATE tenant/kb + CREATE usuario
                  (turno conserva su FK a tenant)
```

## 4. Eje 2 — `roles`: array enum vs tabla puente

### Opcion A: `roles` como `ARRAY` de enum de Postgres
* **Que es?:** Una columna `roles ARRAY(enum)` en `usuario`, con valores `recepcion|odontologo|dueno`. Una fila por usuario.
* **Por que y como:** Es **literalmente** lo que dice la KB (§04: *"roles (array enum: recepcion/odontologo/dueno)"*, *"embebido como array en v1"*). Se implementa con un `TypeDecorator` de SQLAlchemy sobre `ARRAY(enum)`. La unión de permisos (DD-06) es un `roles ⊇ rol` en memoria.
* **Trade-off:** Pro: 1 tabla menos, 1 fila por usuario, exactamente lo que dice la KB / Contra: no hay catálogo de roles (no se puede listar "qué roles existen" sin hardcodear) y agregar un rol = `ALTER TYPE`
* **Esquema:**
```text
usuario(id, tenant_id, email, password_hash, roles ARRAY(enum), activo)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
         un solo campo, sin tabla puente
```

### Opcion B: `roles` como tabla puente `usuario_rol` + catálogo `rol`
* **Que es?:** Tabla `usuario_rol(usuario_id, rol)` y un catálogo `rol`. N filas por usuario.
* **Por que y como:** Normalizado: permite catálogo de roles consultable, metadatos por rol y permisos configurables a futuro.
* **Trade-off:** Pro: catálogo y extensibilidad / Contra: **contradice la KB** (§04 dice array embebido en v1) → exige actualizar la KB con justificación explícita, y suma 2 tablas a un change CRITICO
* **Esquema:**
```text
usuario(id, tenant_id, email, ...)   rol(nombre)
usuario_rol(usuario_id, rol)  --->  N filas por usuario
```

## 5. Eje 3 — Aislamiento R1 en la capa de repositorio

### Opcion A: Repositorio *tenant-scoped* — el filtro es imposible de omitir
* **Que es?:** El `UnitOfWork` se construye con el `tenant_id` del JWT y expone repositorios que **ya filtran**: la API no acepta `tenant_id`, porque el repositorio lo aplicó solo.
* **Por que y como:** `UnitOfWork(tenant_id, session)` → `uo.usuarios` devuelve un `UsuarioRepository` con `tenant_id` fijo. `BaseRepository[T]` aporta `get_by_id`, `list(cursor, limit)`, `add`, `flush`. **R1 deja de depender de la disciplina**: olvidar el filtro deja de ser una posibilidad sintáctica.
* **Trade-off:** Pro: R1 garantizado por construcción, tests de aislamiento triviales / Contra: un caso cross-tenant legítimo (superadmin futuro) necesita una vía explícita aparte
* **Esquema:**
```text
JWT --(tenant_id)--> UnitOfWork(tenant_id, session)
                        |
                        +--> uo.usuarios.get_by_id(id)   # filtra solo, no se pide
                        +--> uo.tenants.get_by_id(id)   # excepcion: tabla global
```

### Opcion B: `tenant_id` explícito en cada llamada (como hoy)
* **Que es?:** `repo.get_by_id(tenant_id, id)` — el filtro se pide en cada método, igual que hoy en `TurnoRepository`.
* **Por que y como:** No cambia el patrón del slice archivado y hace **visible** en el código de llamada dónde está el filtro.
* **Trade-off:** Pro: explícito, sin cambio de patrón / Contra: cada llamada es una oportunidad de olvido → R1 depende de la disciplina, y el middleware de tenant no alcanza si el repo lo olvida
* **Esquema:**
```text
JWT --(tenant_id)--> endpoint
                       |
                       +--> repo.get_by_id(tenant_id, id)   # hay que acordarse
                       +--> repo.list(tenant_id, ...)        # en todas
```

## 6. Eje 4 — Seed demo

### Opcion A: Seed por comando explícito
* **Que es?:** `python -m app.seed` (idempotente) que crea el tenant `demo` + 3 usuarios demo (uno por rol + uno con los 3 roles, DD-06).
* **Por que y como:** El seed corre **cuando alguien lo pide**, nunca en el arranque. Idempotente por construcción: `INSERT ... ON CONFLICT DO NOTHING` sobre `slug` y `(tenant_id, email)`. `SEED_DEMO` queda como bandera del compose de dev para ejecutarlo en el entrypoint.
* **Trade-off:** Pro: imposible que un deploy de producción siembre datos demo sin querer / Contra: un paso manual en el onboarding (se compensa con un `make seed`)
* **Esquema:**
```text
docker compose exec api python -m app.seed   # idempotente, a pedido
```

### Opcion B: Seed automático al arrancar si `SEED_DEMO=true`
* **Que es?:** El lifespan de la app corre el seed cuando `SEED_DEMO` está activo.
* **Por que y como:** Cero fricción: `docker compose up` deja el tenant demo listo sin pasos extra.
* **Trade-off:** Pro: fricción cero en dev / Contra: si `SEED_DEMO` queda en `true` en un entorno real, se siembran datos demo en producción → depende de la disciplina de configuración
* **Esquema:**
```text
docker compose up  --> lifespan --> seed()  # si SEED_DEMO=true
```

---

## 7. Consecuencias de la selección (A / A / A / A)

1. **Esquema**: `002` altera `tenant` y `config` y crea `usuario`. `tenant.id` permanece `String(64)` — **desviación documentada** respecto de §04 (`id` uuid): el `FK` de `turno.tenant_id` creado en `0001` es `String(64)` y cambiar el tipo de la PK obligaría a re-migrar el slice archivado. Se anota como deuda para C-06/C-07.
2. **`roles`**: `ARRAY(enum)` de Postgres, un solo campo. Sin catálogo de roles en v1 (coherente con §04). Agregar un rol = `ALTER TYPE` → queda como operación de migración, no de dominio.
3. **R1 por construcción**: `UnitOfWork(tenant_id, session)` + repositorios scoped. Única excepción: el repositorio de `tenant`, que es global por naturaleza (el registro de tenants), con nombre explícito para que la excepción sea visible.
4. **Seed**: comando explícito e idempotente, nunca automático al arranque.

## 8. Qué queda diferido (y por qué)

| Deuda | Owner | Motivo |
|---|---|---|
| RLS de Postgres | C-13 | DD-04 la marca como endurecimiento posterior, no día 1 |
| `tenant.id` como uuid | C-06/C-07 | Re-migrar `turno.tenant_id` (FK de `0001`) disruptivo en este change |
| Catálogo de roles | v2 | §04 define roles embebidos en v1 |
| `config.plantillas` y ventanas de recordatorio | C-06 / C-09 | C-06 extiende `config` con las ventanas; C-09 es dueño de la tabla `plantilla` |
| Login y refresh rotation | C-03 | C-02 deja `password_hash` y `activo`; la autenticación es de C-03 |

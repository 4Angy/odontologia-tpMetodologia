# Revisión Crítica — Punto 8 del TP (change `C-02 tenancy-core-models`)

## Proyecto
SaaS multi-tenant de gestión para consultorios odontológicos (Argentina)

## Fecha
2026-10-19

## Change revisado
`C-02 tenancy-core-models` — **preparado para implementar** (0/45 tareas; no implementado, no verificado, no archivado). Artefactos en `openspec/changes/C-02-tenancy-core-models/`.

> Complementa la revisión del mismo punto aplicada a `C-01` (`revision-critica-punto-8.md`), que documenta la evidencia de invocación a nivel de sesión y los defectos D1-D5 de aquella ejecución. Esta revisión se concentra **en los resultados del agente para el change de la consigna** (C-02) y en los defectos que esos resultados contienen.

---

# 1. Evidencia de la invocación de la skill

## 1.1 Solicitud realizada

Herramienta: `skill` (cargador de skills de OpenCode).

```
skill({ id: "visual-explore-options" })
```

La skill estaba cargada en el catálogo de la sesión desde el inicio; en el turno de C-02 se invocó de nuevo y se aplicó su procedimiento completo al change nuevo: contexto del change → restricciones duras → ≥2 alternativas por decisión → esquema ASCII → plantilla exacta → **pausa obligatoria** → (selección del usuario) → `design.md`.

## 1.2 Resultado obtenido

El artefacto producido es `discovery/explore-c02-tenancy-core-models.md`, con la estructura que la skill exige:

| Exigencia de la skill | Evidencia en el artefacto |
|---|---|
| ≥2 alternativas por decisión | 4 ejes × 2 opciones, con alternativas descartadas razonadas en cada una |
| "Por qué y cómo" con tecnología concreta | Ej. eje 3: `UnitOfWork(tenant_id, session)` → repositorios ya scoped, la API no acepta `tenant_id` |
| Trade-off con ventaja y costo | Cada opción declara "Pro:" y "Contra:" |
| Esquema ASCII ≤10 líneas | Un esquema por opción (migraciones, `roles` ARRAY vs tabla puente, repositorio scoped vs explícito, seed) |
| Plantilla exacta | `## Opcion A/B` + `* **Que es?:**` + `* **Por que y como:**` + `* **Trade-off:**` + `* **Esquema:**` |
| Recomendación sin imponer | §7 "Consecuencias de la selección (A / A / A / A)" |
| **Pausa obligatoria** | El agente **no** generó `proposal.md`/`design.md` hasta que el usuario respondió "aplica las opciones que recomendaste" |

**Resultado de la invocación**: 4 decisiones structurantes, cada una con su alternativa descartada, y un §8 de "qué queda diferido y por qué" (con owner por deuda).

## 1.3 Qué aportó al change

1. **Forzó la comparación explícita de alternativas antes de fijar el esquema.** El eje 3 (repositorio tenant-scoped vs. `tenant_id` explícito) es la decisión que convierte R1 —la regla dura #1 del proyecto— en estructura en vez de disciplina. Sin la comparación, el slice archivado (`TurnoRepository(session)` con `tenant_id` explícito) se habría replicado por inercia.
2. **Detectó y cerró la colisión de la migración `002`** con la `0001` ya existente, y dejó por escrito que `0001` no se toca.
3. **Puso en pausa la escritura de código** justo donde hacía falta: el usuario eligió las 4 opciones antes de que existiera un solo archivo de `design.md`.
4. **Dejó la evidencia de por qué NO se tomó cada alternativa**, que es lo que permite que un revisor futuro pueda cuestionar la decisión: por ejemplo, la tabla puente de roles quedó descartada **porque contradice la KB §04**, no por preferencia.

---

# 2. Evidencia de la invocación de la herramienta MCP

## 2.1 Herramienta usada

Servidor MCP **`filesystem`** (`@modelcontextprotocol/server-filesystem`, oficial de Anthropic) — el elegido en la ficha de investigación (§4) y el que la consigna del punto 6 dejó configurado.

El cliente del proyecto (`docs/skills-mcp/tools/mcp-fs.js`) habla **JSON-RPC 2.0 por stdio** contra el server oficial: `initialize` → `tools/list` → `tools/call`. Se usa porque la instancia que abre el cliente de OpenCode queda rooteada en el workspace de la sesión y no en el repositorio, y porque el shim `npx.cmd` de Windows parte el path del workspace al contener un espacio (ver `revision-critica-punto-8.md`, D1).

## 2.2 Solicitud realizada y resultado obtenido

**Solicitud 1** — listar la KB:
```
$ echo '{"path":"C:\\Users\\Cara Palida\\Documents\\projects\\odontologia-tpMetodologia\\knowledge-base"}' \
    | node docs/skills-mcp/tools/mcp-fs.js "<raiz>" list_directory -
```
**Resultado**:
```
[FILE] 01_vision_y_objetivos.md
[FILE] 02_descripcion_general.md
[FILE] 03_actores_y_roles.md
[FILE] 04_modelo_de_datos.md
[FILE] 05_reglas_de_negocio.md
[FILE] 06_funcionalidades.md
[FILE] 07_flujos_principales.md
[FILE] 08_arquitectura_propuesta.md
[FILE] 09_decisiones_y_supuestos.md
[FILE] 10_preguntas_abiertas.md
[FILE] README.md
```

**Solicitud 2** — leer el modelo de datos (la fuente de verdad del dominio):
```
$ echo '{"path":"...\\knowledge-base\\04_modelo_de_datos.md"}' \
    | node docs/skills-mcp/tools/mcp-fs.js "<raiz>" read_text_file -
```
**Resultado**: el contenido íntegro del archivo (6.041 caracteres), del que el agente extrajo:
- `tenant`: `id` (uuid PK), `slug` (text unique, para link público), `nombre`, `email_contacto`, `tz` (default `America/Argentina/Buenos_Aires`), `created_at`; *"Constraints: `slug` kebab-case único global"*; índice `slug`.
- `usuario`: `id`, `tenant_id` FK, `nombre`, `email` (unique por tenant), `password_hash`, `roles` (**array enum** `recepcion/odontologo/dueno`), `activo` (bool), `created_at`; *"Relaciones: \*---\* roles (embebido como array en v1)"*; índice `(tenant_id, email)`.
- *"Toda tabla de negocio lleva `tenant_id` NOT NULL + FK a `tenant`. Unicidades y búsquedas siempre compuestas con `tenant_id`."*
- Seed: *"Un `tenant` demo (`slug: demo`) + 3 usuarios demo (uno por rol y uno con los 3 roles…)"*; y los defaults de `config` (`antelacion_cancel_hs = 24`, `senia_requerida = false`).

**Solicitud 3** — leer actores y roles:
```
$ echo '{"path":"...\\knowledge-base\\03_actores_y_roles.md"}' \
    | node docs/skills-mcp/tools/mcp-fs.js "<raiz>" read_text_file -
```
**Resultado**: 3.022 caracteres; de ahí, *"Roles: `recepcion` · `odontologo` · `dueno`. `dueno` incluye todo. Un usuario puede acumular roles."* y la matriz de permisos.

## 2.3 Qué aportó al change

- **Fijó los atributos de los modelos sin inventar nada**: cada campo de `tenant`, `usuario` y `config` que aparece en el spec y en el design sale literalmente de la lectura por MCP. Donde la KB no llegaba, el change **no inventó**: `config` crece sólo con `senia_requerida` (KB §04 seed + RN-CO-02), y `plantillas`/ventanas de recordatorio quedaron diferidas a C-06/C-09 (Decisión 10).
- **Sustituyó una decisión de dominio por una cita de la KB**: el eje 2 del explore (`roles` como array enum) no salió de una preferencia técnica sino de la línea *"roles (array enum…)"* y *"embebido como array en v1"* de §04. La alternativa (tabla puente) quedó descartada **por contradecir la KB**, que es el criterio que la consigna exige.
- **Hizo auditable el supuesto de la unicidad global**: la línea *"Constraints: `slug` kebab-case único global"* es la que sostiene el requirement 3 del spec.
- **Detectó una inconsistencia interna de la KB** (el ERD lista `config(antelacion_hs, senia_monto, plantillas)` y el seed dice `antelacion_cancel_hs = 24`, `senia_requerida = false`): quedó registrada como desviación con owner en `CHANGES.md` y en el task 1.9, en vez de resolverse por decreto.

---

# 3. Defectos detectados en los resultados del agente (C-02)

## D1 — El spec de C-02 contradice el contrato de error de `foundation/runtime`

**Gravedad: alta.** Es una contradicción entre **dos specs normativos** del proyecto.

**Cómo se detectó:** cruce del spec nuevo contra el spec ya archivado de C-01, `openspec/specs/foundation/runtime/spec.md`. Ese spec (línea 98) dice:

> *"El sistema SHALL responder a todo error con un cuerpo `{code, message, action?}`… **Ningún endpoint SHALL devolver una forma de error distinta de esta**."*

El spec de C-02, en cambio, exigía que el error de slug duplicado "identificara la columna `slug` como causante" — un dato que **no tiene lugar en el envelope**: no existe campo para él. Un implementador que satisfaciera el spec de C-02 rompería el de `foundation/runtime`, y al revés. Los dos son normativos y ambos validados.

**Fuente o regla que permitió corregirla:** el propio requisito de `foundation/runtime` (R9 y el sobre `{code, message, action?}`) y la KB §05, que **no define ningún RN para el slug duplicado** (verificado: los 24 RN de la KB son RN-AG-01..07, RN-AU-01..04, RN-CO-01..05, RN-GL-01..04, RN-PA-01..04; ninguno cubre unicidad de `slug`). Por la regla del propio contrato, corresponde el **código genérico documentado**, no inventar un RN nuevo.

**Antes** (`specs/tenancy/identidad/spec.md`, escenario 3.1):
```
- **THEN** la creación es rechazada por la restricción de unicidad, y el error identifica la columna `slug` como causante
```

**Después**:
```
- **THEN** la creación es rechazada con un error `409` cuyo cuerpo es `{code, message}` —el código genérico
  documentado, porque la base de conocimiento no define una regla de negocio para el slug duplicado— y con un
  mensaje en español-AR que indique que el slug ya está en uso; el detalle técnico de la restricción queda en el
  log y no en la respuesta
```

Se agregó además el **escenario 3.3 (borde)** que cierra el hueco que esta corrección destapa: *"Todo tenant tiene slug"* — ningún tenant puede quedar con `slug` nulo, porque la unicidad global no puede garantizarse sobre nulos.

Y en `design.md` y `tasks.md` quedó explícito que el detalle técnico va al log (nunca a la respuesta, por R9 y por el requisito de no exponer sentencias SQL).

## D2 — La migración `002` dejaba `slug` nullable y rompía el seed del slice archivado

**Gravedad: alta.** Defecto de plan de migración, con impacto en datos y en el código existente.

**Cómo se detectó:** dos verificaciones independientes.

**(a) Experimento sobre Postgres 16 real.** El plan de migración decía `ADD COLUMN slug text NULL` → backfill → `CREATE UNIQUE INDEX`. La premisa implícita es que el índice garantiza la unicidad. Se comprobó en la base de test:

```sql
CREATE TABLE exp_slug (id serial primary key, nombre text, slug text);
INSERT INTO exp_slug (nombre, slug) VALUES ('A', 'a'), ('B', NULL);
CREATE UNIQUE INDEX ux_exp_slug ON exp_slug (slug);
SELECT id, nombre, slug IS NULL FROM exp_slug;
```
```
 id | nombre | slug_es_null
----+--------+--------------
  1 | A      | f
  2 | B      | t          ← el NULL no violó el índice
```
**Postgres admite múltiples valores NULL en un índice único.** Con `slug` nullable, un tenant sin slug no dispara la restricción: dos tenants sin slug pasarían el índice y el contrato "slug único global" quedaría **sin garantía** (y el link público `/r/:slug` no podría resolverlos).

**(b) Cruce con el código existente.** `backend/app/modules/agenda/seed_demo.py:21` inserta el tenant demo **sin `slug`**:
```python
session.add(TenantModel(id=TENANT_DEMO, nombre="Consultorio Demo"))
```
El plan de C-02 no mencionaba ese archivo en ningún punto. Con `slug` nullable, el seed archivado crea un tenant **sin slug**; con `slug` NOT NULL, el seed archivado **rompe** con `IntegrityError`. En los dos casos el plan era incorrecto.

**Fuente o regla que permitió corregirla:** la KB §04 (*"Constraints: `slug` kebab-case único global"*), el contrato de unicidad que el propio spec declara, y la regla dura **R6** (migraciones reversibles y correctas). La corrección no inventa dominio: hace que el esquema cumpla lo que la KB ya dice.

**Antes** (`design.md` §Migration Plan):
```
- `ALTER TABLE tenant ADD COLUMN slug text NULL`, ...
- Backfill: `UPDATE tenant SET slug = <derivado de nombre> WHERE slug IS NULL`.
- `CREATE UNIQUE INDEX ux_tenant_slug ON tenant (slug)`.
```

**Después**:
```
- `ALTER TABLE tenant ADD COLUMN slug text NULL` (nullable **sólo** durante el backfill) ...
- Backfill determinista: ... Si dos tenants derivan el mismo slug, la migración **falla con un mensaje explícito**
  en vez de aplicar un índice que no se puede crear, y el operador resuelve el choque a mano.
- `ALTER TABLE tenant ALTER COLUMN slug SET NOT NULL` — Postgres admite N valores NULL en un índice único, así que
  la columna tiene que ser NOT NULL para que "slug único global" sea una garantía y no una intención (Decisión 13).
- `CREATE UNIQUE INDEX ux_tenant_slug ON tenant (slug)`.
- **Upstream obligatorio**: `backend/app/modules/agenda/seed_demo.py` (slice archivado) inserta el tenant demo
  **sin `slug`**. Con `slug` NOT NULL el seed rompería con `IntegrityError`: este change lo actualiza para fijar
  `slug = 'demo'`, o difiere el cambio a C-07 con owner declarado (Decisión 13).
```

Se agregó la **Decisión 13** al design, un riesgo en §Risks, y tres tareas nuevas (1.10, 1.11, 1.12) con sus verificaciones.

## D3 — El spec filtraba un detalle de implementación

**Gravedad: baja.** Un spec describe comportamiento observable, no mecanismos.

**Cómo se detectó:** relectura del spec contra las reglas de redacción de specs de OpenSpec (*"Avoid in specs: internal class/function names, step-by-step implementation details"*).

**Antes** (escenario 1.1):
```
- **WHEN** el repositorio de usuarios se resuelve para el tenant `A` y se pide el identificador `u-1`
- **THEN** la consulta no devuelve ninguna fila, y la consulta ejecutada incluye la condición de filtro por el
  `tenant_id` del tenant `A`
```
La segunda mitad exige verificar el SQL generado: es un detalle de implementación, y además ata el spec a una forma concreta de escribir la consulta.

**Después**:
```
- **WHEN** el acceso a datos del tenant `A` pide el identificador `u-1`
- **THEN** no devuelve ninguna fila, y el acceso a datos de negocio no puede obtenerse sin un tenant, de modo que
  el filtro por tenant forma parte de la construcción del acceso y no de cada consulta
```
La garantía que importa —el filtro no se puede omitir— queda expresada en términos observables, y la aserción sobre el SQL queda en las **tareas** (2.5), donde sí corresponde.

---

# 4. Prueba de borde para evaluar los límites de la revisión

La consigna pide, cuando no se detectan defectos, "prueben un caso de borde para evaluar sus límites y documenten el resultado **sin inventar un error**". Aquí se detectaron defectos, pero se hizo igual la prueba de borde, porque evalúa un límite distinto: **el del propio mecanismo de validación**.

**Límite evaluado: `openspec validate` valida cada spec por separado.**

Durante la revisión se comprobó que, con el defecto D1 presente, el validador reportaba el change como válido:

```
$ openspec validate C-02-tenancy-core-models --strict
Change 'C-02-tenancy-core-models' is valid
```

Es decir: la **contradicción normativa entre dos specs** (D1) **no la detecta la herramienta**. El validador comprueba la forma de cada delta —headers, escenarios, `SHALL`— pero no cruza el spec nuevo contra los specs ya archivados.

**Resultado del caso de borde, documentado sin inventar errores:**

| Comprobación | Resultado |
|---|---|
| `openspec validate --strict` sobre C-02 con D1 presente | ✅ "is valid" — **el defecto pasó la validación** |
| `openspec validate --all --strict` (specs + changes) | ✅ 3/3 — tampoco lo detecta |
| Cruce manual contra `openspec/specs/foundation/runtime/spec.md` | ❌ **contradicción encontrada** (D1) |
| Experimento de NULLs en índice único sobre Postgres 16 | ❌ **defecto de plan encontrado** (D2) |
| Cruce manual con `backend/app/modules/agenda/seed_demo.py` | ❌ **omisión encontrada** (D2) |

**Conclusión honesta:** la validación automática es **necesaria pero no suficiente**. Sirve para la forma; no sirve para la coherencia entre specs, ni para la corrección del plan de migración frente a la semántica real del motor, ni para el cruce con el código existente. Por eso el task 8.6 (verificación cruzada de specs) queda escrito **como tarea**, y no como confianza en el validador: es una actividad que alguien tiene que hacer, y este change la explicita para que no se pierda.

---

# 5. Cómo reproducir la evidencia

```bash
# 1) Evidencia de la skill: el artefacto de explore con 4 ejes y la pausa
sed -n '1,40p' discovery/explore-c02-tenancy-core-models.md

# 2) Evidencia del MCP: listar y leer la KB por el protocolo MCP
node docs/skills-mcp/tools/mcp-fs.js "<raiz>" list_directory  # argumentos por stdin
node docs/skills-mcp/tools/mcp-fs.js "<raiz>" read_text_file  # -> knowledge-base/04_modelo_de_datos.md

# 3) D2: el experimento de NULLs en índice único (Postgres 16)
docker exec odontologia-test-pg psql -U odontologia -d odontologia_test -c "
  CREATE TABLE exp_slug (id serial primary key, nombre text, slug text);
  INSERT INTO exp_slug (nombre, slug) VALUES ('A','a'), ('B',NULL);
  CREATE UNIQUE INDEX ux_exp_slug ON exp_slug (slug);"   # el NULL no viola el índice

# 4) D2: el seed del slice archivado inserta el tenant sin slug
grep -n "TenantModel(" backend/app/modules/agenda/seed_demo.py

# 5) D1: el contrato de error que el spec nuevo debe respetar
grep -n "Ningún endpoint SHALL devolver una forma de error distinta" openspec/specs/foundation/runtime/spec.md

# 6) Validación (no detecta ninguno de los tres defectos)
openspec validate C-02-tenancy-core-models --strict
```

# 6. Archivos corregidos por esta revisión

| Archivo | Corrección |
|---------|------------|
| `openspec/changes/C-02-tenancy-core-models/specs/tenancy/identidad/spec.md` | D1 (escenario 3.1 reescrito al envelope `{code, message}`; nuevo escenario 3.3) y D3 (escenario 1.1 sin detalle de implementación) |
| `openspec/changes/C-02-tenancy-core-models/design.md` | D2 (Decisión 13, §Migration Plan corregido, riesgo nuevo) |
| `openspec/changes/C-02-tenancy-core-models/tasks.md` | D1 (tarea 4.4), D2 (tareas 1.10, 1.11, 1.12) y D1/D2 (tarea 8.6 de verificación cruzada) |
| `docs/skills-mcp/revision-critica-punto-8-c02.md` | Este documento |

---

**Estado de la revisión**: 3 defectos detectados (D1 contradicción entre specs, D2 plan de migración y seed upstream, D3 detalle de implementación en el spec), **los 3 corregidos** con antes/después y con el razonamiento que permitió corregirlos. El change sigue **preparado para implementar**: 0 tareas hechas, no implementado, no verificado, no archivado.

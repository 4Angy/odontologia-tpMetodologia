# Defectos detectados en los resultados del agente — antes y después

Ocho incidencias detectadas en la ejecución del agente (5 en C-01 (D1 a D5) y 3 en C-02 (D6 a D8)). Todas corregidas y verificadas. Fuentes de las correcciones: el spec como contrato, la KB como autoridad del dominio, el schema de la herramienta y la semántica real del motor.

---

## D1 · El MCP `filesystem` declaraba "OPERATIVO" sin estar conectado
**Gravedad alta** · **Dónde:** ejecución de C-01 · **Cómo se detectó:** `opencode mcp list` mostraba 2 servidores, no 3; el `filesystem` no aparecía, mientras `docs/skills-mcp/mcp-configuracion.md` decía *"Estado: CONFIGURADO Y OPERATIVO"*. Además `aplicacion.md` admitía lo contrario (*"El servidor MCP no se pudo ejecutar realmente"*), o sea que los dos documentos del TP se contradecían.
**Fuente/regla:** la consigna del punto 6 (*"Comprueben la conexión y ejecuten al menos una herramienta real"*) y el punto 8 (*"Mostrar únicamente una lista de herramientas instaladas no acredita su uso"*).

**Antes** — `opencode.jsonc` (archivo que el cliente **no lee**) con `npx`:
```jsonc
"filesystem": { "command": "npx", "args": ["@modelcontextprotocol/server-filesystem", "C:\\Users\\Cara Palida\\..."] }
```
**Después** — `opencode.json` (activo) con `node` y el entry absoluto:
```jsonc
"filesystem": { "type": "local", "command": ["node", "...\\server-filesystem\\dist\\index.js", "C:\\...\\odontologia-tpMetodologia"] }
```
**Causa raíz doble:** (a) la entry estaba en el archivo de config equivocado; (b) el shim `npx.cmd` de Windows parte el argumento cuando el path tiene espacios → `Error: None of the specified directories are accessible`.
**Verificación:** `opencode mcp list` → 3 servidores; handshake JSON-RPC → `INIT secure-filesystem-server 2.0.0`, 14 tools, `READ CHANGES.md -> 34908 chars`. Ver `mcp-filesystem-verificacion.txt`.

---

## D2 · Violación del spec: el secreto temporal de `dev` se generaba sin el aviso exigido
**Gravedad media** · **Dónde:** C-01 · **Cómo se detectó:** en el punto 8 se cruzó cada uno de los 18 escenarios del spec `foundation/runtime` contra los tests que los cubren. El escenario *"en dev arranca con aviso explícito de que usa un secreto temporal"* estaba cubierto por un test que **sólo** verificaba que existiera un secreto. Al leer la implementación, la ausencia era real: `_aplicar_reglas` generaba el secreto y devolvía, sin emitir nada.
**Fuente/regla:** el requisito del spec `foundation/runtime` y la regla dura **R11** (TDD estricto, mínimo 2 casos por comportamiento) aplicada en su versión correctiva.

**Antes** (`backend/app/core/config.py`):
```python
if settings.jwt_secret is None:
    if not settings.es_desarrollo:
        raise ConfigError(...)
    settings = settings.model_copy(update={"jwt_secret": SecretStr(secrets.token_hex(32))})
    return settings
```
**Después**:
```python
if not valor.strip():
    if not settings.es_desarrollo:
        raise ConfigError(...)
    logging.getLogger("odontologia.config").warning(
        "JWT_SECRET no está configurada: se usa un secreto TEMPORAL ..."
    )
    return settings.model_copy(update={"jwt_secret": SecretStr(secrets.token_hex(32))})
```
**Prueba de regresión** (reversible, verificada en rojo sobre el estado previo y en verde sobre el corregido):
```
$ pytest tests/test_settings.py::test_sin_jwt_secret_en_dev_avisa_que_usa_un_secreto_temporal
E  AssertionError: assert 'JWT_SECRET' in 'BEFORE-DEFECTO: ...'      → 1 failed
$ git checkout -- backend/app/core/config.py
$ pytest tests/test_settings.py::test_sin_jwt_secret_en_dev_avisa_que_usa_un_secreto_temporal
1 passed
```

---

## D3 · `design.md` declaraba "Secrets: ninguno" de forma inexacta
**Gravedad baja** · **Dónde:** C-01 · **Cómo se detectó:** contraste entre `design.md` (Decisión 9 — CI: *"Secrets: ninguno."*) y `tasks.md` (Task 6.4 exige correr el ciclo de migraciones **contra Postgres 16 real**, lo que exige credenciales de conexión).
**Fuente/regla:** coherencia documental de `AGENTS.md` §Reglas Duras y **R13** (gobernanza CRITICAL/HIGH).

**Antes:** `Secrets: ninguno.`
**Después:** `Secrets: **ninguno** — el job backend no usa secrets de GitHub: la conexión a Postgres 16 y Redis 7 se hace con las credenciales **de los propios service containers del job**, declaradas como variables de entorno del runner ... y con un JWT_SECRET de CI que no es un secreto real.`

---

## D4 · Contaminación con caracteres CJK en 4 archivos escritos por el agente
**Gravedad baja** · **Dónde:** C-01 · **Cómo se detectó:** barrido explícito `Select-String -Pattern '[\u4e00-\u9fff\u3040-\u30ff]'` sobre todos los archivos escritos. Ningún linter, ni `openspec validate`, ni los tests lo señalan.
**Fuente/regla:** la disciplina de idioma del proyecto (la KB, los ADR y los specs se revisan en español).

| Archivo | Antes | Después |
|---|---|---|
| `backend/app/core/config.py` | `... en entornos no玩具.` | `... en entornos que no son de desarrollo.` |
| `discovery/explore-c01-...md` | `puede **fijar el contrato** de形状.` | `puede **fijar el contrato** de campos.` |
| `docs/adr/ADR-001-...md` | `no incluyen类型 \`service\`` | `no incluyen mensajes de categoría \`service\`` |
| `design.md` | `**Nota de路径**` / `esa接口` | `**Nota de rutas**` / `soportado por la interfaz` |

**Verificación final:** `git grep -I -P "[\x{4e00}-\x{9fff}]" <commit> -- "*.md" "*.py" "*.ts"` → vacío.

---

## D5 · El agente introdujo dos CVE moderados al agregar `react-router-dom` 6.x
**Gravedad media** · **Dónde:** C-01 · **Cómo se detectó:** `npm audit` al cerrar el change. Advisory `GHSA-wrjc-x8rr-h8h6` (open redirect vía backslash en `<Link>` y `useNavigate`) y `GHSA-337j-9hxr-rhxg` (constructor injection en la hidratación SSR, no aplicable a una SPA, pero el paquete figuraba vulnerable).
**Fuente/regla:** el `npm audit` del propio toolchain y la revisión de lo generado por IA (consideración "Criterio profesional" del TP).

**Antes → después** (diff real en `frontend/package.json`):
```diff
-    "react-router-dom": "^6.28.0",
+    "react-router-dom": "^7.18.4",
-    "vitest": "^2.1.8",
+    "vitest": "^5.0.5",
```
`npm audit`: 8 vulnerabilidades (5 moderate, 1 high, 2 critical) → **0 vulnerabilidades**. Con 10 tests, typecheck y build en verde.

---

## D6 · El spec de C-02 contradecía el contrato de error de `foundation/runtime`
**Gravedad alta** · **Dónde:** artefactos de C-02 · **Cómo se detectó:** cruce del spec nuevo contra el spec archivado de C-01, `openspec/specs/foundation/runtime/spec.md:98`: *"El sistema SHALL responder a todo error con un cuerpo `{code, message, action?}`... **Ningún endpoint SHALL devolver una forma de error distinta de esta**."* El spec de C-02 exigía que el error "identificara la columna `slug`" — un dato que **no tiene lugar en el envelope**. Los dos specs son normativos y ambos validaban.
**Fuente/regla:** el propio requisito de `foundation/runtime` (R9) y la KB §05, donde se verificó que **ninguno de los 24 RN** (RN-AG-01..07, RN-AU-01..04, RN-CO-01..05, RN-GL-01..04, RN-PA-01..04) cubre el slug duplicado → corresponde el **código genérico documentado**, no inventar un RN.

**Antes** (escenario 3.1):
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
Se agregó además el escenario 3.3 (*"Todo tenant tiene slug"*), que cierra el hueco que la corrección destapa.

---

## D7 · La migración `002` dejaba `slug` nullable y rompía el seed del slice archivado
**Gravedad alta** · **Dónde:** artefactos de C-02 · **Cómo se detectó:** dos verificaciones independientes. (a) **Experimento sobre Postgres 16 real**: la premisa implícita del plan era que el índice único garantizaba la unicidad, pero `INSERT ... ('B', NULL)` + `CREATE UNIQUE INDEX` **no viola el índice** → con `slug` nullable, "slug único global" quedaba sin garantía. (b) **Cruce con el código existente**: `backend/app/modules/agenda/seed_demo.py:21` inserta el tenant demo **sin `slug`** (`TenantModel(id=TENANT_DEMO, nombre="Consultorio Demo")`) y el plan no mencionaba ese archivo: con la columna nullable crea un tenant sin slug, y con la columna NOT NULL rompe el seed con `IntegrityError`.
**Fuente/regla:** KB §04 (*"Constraints: `slug` kebab-case único global"*), el contrato de unicidad que el propio spec declara y la regla dura **R6** (migraciones reversibles y correctas).

**Antes:**
```
- ALTER TABLE tenant ADD COLUMN slug text NULL
- Backfill: UPDATE tenant SET slug = <derivado de nombre> WHERE slug IS NULL
- CREATE UNIQUE INDEX ux_tenant_slug ON tenant (slug)
```
**Después:**
```
- ALTER TABLE tenant ADD COLUMN slug text NULL (nullable sólo durante el backfill)
- Backfill determinista que falla con mensaje explícito ante colisión
- ALTER TABLE tenant ALTER COLUMN slug SET NOT NULL   <-- Postgres admite N NULL en un índice único
- CREATE UNIQUE INDEX ux_tenant_slug ON tenant (slug)
- Upstream obligatorio: seed_demo.py fija el slug del tenant demo (o se difiere a C-07 con owner)
```
Se agregó la **Decisión 13** al design, un riesgo en §Riesgos y las tareas 1.10, 1.11 y 1.12. Experimento en `experimento-postgres-null-en-unique.txt`.

---

## D8 · El spec filtraba un detalle de implementación
**Gravedad baja** · **Dónde:** artefactos de C-02 · **Cómo se detectó:** relectura contra las reglas de redacción de specs de OpenSpec (*"Avoid in specs: internal class/function names, step-by-step implementation details"*).
**Fuente/regla:** las reglas de redacción del schema `spec-driven`.

**Antes** (exigía verificar el SQL generado):
```
- **THEN** la consulta no devuelve ninguna fila, y la consulta ejecutada incluye la condición de filtro por el
  `tenant_id` del tenant `A`
```
**Después** (garantía observable):
```
- **THEN** no devuelve ninguna fila, y el acceso a datos de negocio no puede obtenerse sin un tenant, de modo que
  el filtro por tenant forma parte de la construcción del acceso y no de cada consulta
```
La aserción sobre la consulta pasó a las tareas (2.5), donde sí corresponde.

---

## Prueba de borde sobre los límites del validador

Con D6 presente, `openspec validate C-02-tenancy-core-models --strict` reportaba **"is valid"**, y `validate --all --strict` también (3/3). El validador comprueba la **forma** de cada delta (encabezados, escenarios, `SHALL`) pero **no** cruza el spec nuevo contra los specs archivados, **no** confronta el plan de migración con la semántica real del motor, y **no** revisa el código existente.

| Comprobación | Resultado |
|---|---|
| `openspec validate --strict` con D6 presente | "is valid" — **el defecto pasó la validación** |
| `openspec validate --all --strict` | 3/3 — tampoco lo detecta |
| Cruce manual contra `foundation/runtime` | **contradicción encontrada** (D6) |
| Experimento de NULLs en índice único sobre Postgres 16 | **defecto de plan encontrado** (D7) |
| Cruce manual con `seed_demo.py` | **omisión encontrada** (D7) |

**Conclusión:** la validación automática es necesaria pero **no suficiente**. Por eso la verificación cruzada quedó escrita como **tarea 8.6** del change, y no como confianza en la herramienta.

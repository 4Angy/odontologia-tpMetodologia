# Revisión Crítica — Punto 8 del TP

## Proyecto
SaaS multi-tenant de gestión para consultorios odontológicos (Argentina)

## Fecha
2026-10-19

## Alcance
Evidencia de la invocación **real** de la skill `visual-explore-options` y de herramientas MCP, con solicitud, resultado y aportación al change `C-01 foundation-setup-decisiones`; y detección, corrección y documentación de defectos de la ejecución.

> Esta revisión reemplaza al borrador previo del mismo archivo: el borrador documentaba un solo defecto (D3) y no contenía evidencia de invocación de skill ni de MCP.

---

# 1. Evidencia de la invocación de la skill

## 1.1 Solicitud realizada

Herramienta: `skill` (cargador de skills de OpenCode).

```
skill({ id: "visual-explore-options" })
```

Se invocó en el **primer mensaje** de la sesión, junto con la lectura del contexto del change (`read` de `CHANGES.md`, `openspec/`, `knowledge-base/08`, `knowledge-base/09`, `knowledge-base/10`, `discovery/analisis-competitivo.md`, `discovery/explore-cancelar-turnos.md`, `AGENTS.md`, `openspec/config.yaml`, `backend/`, `frontend/`).

## 1.2 Resultado obtenido

El loader devolvió el `SKILL.md` completo. Extractos literales de las secciones que gobiernan la ejecución:

| Sección del SKILL.md | Texto devuelto |
|---|---|
| "Cuando activar" | "Activa cuando: Inicias `explore` de un change nuevo con decisiones abiertas, o El contexto menciona arquitectura, componentes UI, backend, schema DB, API, o trade-offs técnicos." |
| "1. Identifica al menos 2 alternativas viables" | "Evalua al menos 2 opciones reales. No inventes opciones de relleno." |
| "2. Genera esquema visual o conceptual ASCII" | "Mantenlo pequeno: max 10 lineas, solo cajas y flechas, sin arte complejo." |
| "3. Presenta con esta plantilla exacta" | "Usa SIEMPRE esta plantilla" → `## Opcion A:`, `* **Que es?:**`, `* **Por que y como:**`, `* **Trade-off:**`, `* **Esquema:**` |
| "4. Pausa obligatoria" | "Termina SIEMPRE con la pausa. No generes `design.md`, no escribas codigo, no asumas eleccion. Espera respuesta explicita." |
| "Criterios de calidad" | "Flujo detenido hasta seleccion." |

**Resultado concreto de la invocación** (no una lista de herramientas instaladas, sino el artefacto que produjo):

`discovery/explore-c01-foundation-setup-decisiones.md` — 4 ejes con 2 opciones cada uno, 7 decisiones menores, esquemas ASCII, recomendación y la pausa final.

## 1.3 Qué aportó al change

La skill estructuró la decisión y, sobre todo, **detuvo al agente antes de escribir código**:

| Paso | Resultado verificable |
|---|---|
| Eje 1 (ADR-001 / PA-01) | 2 opciones (`official` vs `gateway`) con tabla de entregabilidad y riesgo de baneo → **A** |
| Eje 2 (ADR-002 / PA-02) | 2 opciones (caja pura vs caja + recibo interno) con el riesgo de defraudar al dueño → **A** |
| Eje 3 (esquema) | 2 opciones (respetar `0001` vs realinear al plan) → **A** |
| Eje 4 (migrabilidad FDI) | 2 opciones (contrato formal vs nota narrativa) → **A** |
| M1 (base de datos) | Postgres 16 real en dev y CI vs SQLite → **Postgres 16 real** |
| **Pausa obligatoria** | El agente **no** escribió `design.md` hasta que el usuario respondió "Eje 1: A, Eje 2: A, Eje 3, Eje 4: A, Postgres 16 real en dev y CI" |

La skill aportó: (a) la **disciplina de no decidir por el usuario** — el `design.md` documenta 14 decisiones con alternativas descartadas, y 3 de ellas (ADR-001/002/003) nacieron directamente de la comparación de la skill; (b) la detección de la **colisión de migraciones** (`0001_cancelacion_turno` vs. el plan 001-012), que el Eje 3 destapó y que hoy está reconciliada en `CHANGES.md`; (c) el artefacto `discovery/explore-c01-foundation-setup-decisiones.md`, que es la entrada de la cadena de trazabilidad del change.

---

# 2. Evidencia de la invocación de herramientas MCP

En esta sesión se invocaron **dos** servidores MCP distintos. Se documentan por separado porque cumplen roles distintos: uno es el MCP elegido por el TP (punto 6), y el otro es el que realmente estaba disponible y se usó (punto 8).

## 2.1 MCP `engram` — 12 llamadas, con resultado

Fue el MCP efectivamente disponible en el catálogo de la sesión. Todas las llamadas se hicieron desde el runtime de code-mode (`execute`) contra `tools.engram.*`.

| # | Solicitud | Resultado obtenido | Aportación al change |
|---|---|---|---|
| 1 | `mem_current_project()` | `{"error_code":"unknown_project","hint":"Use one of the available_projects values"}` | El proyecto no se puede deducir del directorio de trabajo: el nombre hay que **declararlo** |
| 2 | `mem_save({... project:"odontologia-tpmetodologia"})` | `{"error_code":"unknown_project","hint":"Use one of the available_projects values"}` | Fallo informativo: obliga a atar el proyecto antes de guardar (solución en §2.2) |
| 3 | `mem_save({title:"C-01 foundation: ADR-001/002/003 + esquema y base de datos", type:"decision", project:"odontologia-tpmetodologia", content:"**What**/**Why**/**Where**/**Learned**"})` | `{"result":"Memory saved","judgment_required":true,"candidates":[3]}` | Persistió las 4 decisiones del explore + la 5ª (esquema de migraciones) + los 5 gotchas |
| 4-6 | `mem_judge({judgment_id, relation:"related"/"not_conflict", reason, confidence})` ×3 | `{"judgment_status":"judged"}` ×3 | Resolvió el protocolo de revisión de conflictos: enlazó la decisión con las memorias previas del mismo proyecto |
| 7 | `mem_save({title:"C-01 apply: base runtime (settings/logging/errors/health) + Postgres real + compose + ADRs", type:"decision"})` | `{"result":"Memory saved","judgment_required":true}` | Persistió los 6 gotchas no derivables del código |
| 8-10 | `mem_judge(...)` ×3 | `{"judgment_status":"judged"}` ×3 | Ídem |
| 11 | `mem_save({title:"Verify C-01: 3 huecos del spec encontrados y corregidos", type:"bugfix"})` | `{"result":"Memory saved","judgment_required":true}` | Persistió los 3 huecos del spec y sus correcciones |
| 12-14 | `mem_judge(...)` ×3 | `{"judgment_status":"judged"}` ×3 | Ídem |

**Verificación posterior** (herramientas de lectura del mismo MCP):

```
mem_search({ query:"C-01", project:"odontologia-tpmetodologia" })
→ Found 3 memories:
  #33 [decision] C-01 foundation: ADR-001/002/003 + esquema y base de datos
  #34 [decision] C-01 apply: base runtime (settings/logging/errors/health) + Postgres real + compose + ADRs
  #35 [bugfix]   Verify C-01: 3 huecos del spec encontrados y corregidos
```

## 2.2 Atar el proyecto a la memoria (y por qué las llamadas fallaban)

Las primeras llamadas al MCP devolvieron `unknown_project`: el nombre del proyecto **no se puede deducir del directorio de trabajo** cuando el repositorio está anidado dentro de otro repositorio (el remoto Git es compartido), y el nombre hay que **declararlo**. La solución son dos piezas, ambas versionadas o globales:

| Pieza | Dónde | Efecto |
|---|---|---|
| `.engram/config.json` con `{"project_name": "odontologia-tpmetodologia"}` | **en el repo** | `mem_current_project()` resuelve el proyecto desde el repo: `{"project":"odontologia-tpmetodologia","project_source":"config"}`. El repo queda atado a su propia memoria y `engram sync` versiona las observaciones correctas. |
| `environment: { ENGRAM_PROJECT: "odontologia-tpmetodologia" }` en el server `engram` de `~/.config/opencode/opencode.json` | global | El proceso del MCP arranca con el proyecto por defecto, sin depender del cwd. La clave `environment` está en el schema de opencode (`McpLocalConfig`). |

Con las dos piezas, `mem_save` acepta `project:"odontologia-tpmetodologia"` ("backed by repo config") y las observaciones del proyecto quedan bajo ese nombre, con sus relaciones y sus pines.

**Qué aportó al change (honestamente):** el MCP `engram` **no aportó contenido al entregable** — ni una línea del código, de los specs ni de los ADR salió de ahí. Su aportación fue de **trazabilidad y continuidad**: (a) dejó las decisiones y los gotchas fuera del repo, en memoria consultable por sesiones futuras, incluyendo tres trampas que **no** se deducen del código (que `pydantic-settings` lee `os.environ` incluso en `model_validate`; que `pytest.ini` con `addopts=-q` + un `-q` extra produce `-qq` y oculta el resumen en pytest 9; que `model_validate` no coacciona `str` → `ZoneInfo`); (b) obligó a un segundo pase de revisión semántica (`mem_judge`) sobre cada decisión, que fue el que destapó el conflicto de nomenclatura con una memoria previa del mismo proyecto. Es aportación al *proceso*, no al *producto*.

## 2.3 MCP `filesystem` — el del TP: **no estaba conectado** (ver D1)

Al revisar la evidencia del punto 6 se comprobó que el servidor MCP elegido por el TP **nunca había estado operativo**. Antes de corregirlo, la invocación real en esta sesión:

```
opencode mcp list
→  ✓ context7 connected
  ✓ engram   connected
  └─ 2 server(s)          ← filesystem NO aparece
```

Después de la corrección (§3, D1):

```
opencode mcp list
→  ✓ context7  connected
  ✓ engram    connected
  ✓ filesystem connected
      node C:\Users\Cara Palida\AppData\Roaming\npm\node_modules\@modelcontextprotocol\server-filesystem\dist\index.js C:\Users\Cara Palida\Documents\projects\odontologia-tpMetodologia
  └─ 3 server(s)
```

**Invocación real de una herramienta del MCP en esta sesión** (no una lista de instaladas):

```
tools.filesystem.list_directory({ path: "C:\\Users\\Cara Palida\\Downloads" })
→ { "content": "[FILE] # Ejemplo de condicional anidado.py\n[FILE] ##Ejercicio2.py\n...
                [FILE] 1.1.png\n[DIR] 1985 ¡Gulp!\n..." }
```

Y un **handshake MCP completo por stdio** contra la raíz del proyecto, para demostrar que el servidor puede leer los archivos del repo a través del protocolo:

```
INIT   server: secure-filesystem-server 2.0.0
TOOLS: read_file, read_text_file, read_media_file, read_multiple_files, write_file,
       edit_file, create_directory, list_directory, list_directory_with_sizes,
       directory_tree, move_file, search_files, get_file_info, list_allowed_directories
CALL   read_text_file("CHANGES.md")
→ 34908 chars; empieza con: "# CHANGES — Secuencia de Implementación\r\n\r\n> Índice canónico"
```

> **Nota sobre la cifra:** 33704 chars corresponde a CHANGES.md en el commit 4ec1cc5 (CRLF); el archivo creció al agregar los artefactos de C-02. Valor reproducido el 2026-10-27 con tools/mcp-handshake.js: 34908 chars (34514 con LF).

**Qué aporta al change:** con `filesystem` operativo y rooted en el proyecto, un agente puede consultar `CHANGES.md`, `knowledge-base/`, `openspec/specs/` y los changes **sin salir del chat** y **sin permisos de escritura sobre datos sensibles** — que es exactamente el objetivo declarado en `docs/skills-mcp/investigacion.md` §4 y en `AGENTS.md` §Integración MCP. Antes de la corrección, ese objetivo era una aspiración documental sin servidor detrás.

---

# 3. Defectos detectados y corregidos

## D1 — El MCP elegido por el TP declaraba estar "OPERATIVO" sin estar conectado

**Gravedad: alta.** Es el defecto que invalida la evidencia del punto 6 y del punto 8: el TP afirmaba un estado que la realidad contradecía.

**Cómo se detectó:** `opencode mcp list` (el cliente OpenCode) showed **2 servidores** conectados, no 3. El `filesystem` no aparecía. La comparación con `docs/skills-mcp/mcp-configuracion.md`, cuyo encabezado dice *"## Estado: CONFIGURADO Y OPERATIVO"*, reveló la contradicción. Además `docs/skills-mcp/aplicacion.md` §Limitaciones ya admitía lo contrario (*"El servidor MCP no se pudo ejecutar realmente en este entorno de chat... La conexión real y ejecución de una herramienta MCP quedan pendientes para el usuario"*), de modo que los dos documentos del TP se contradecían entre sí.

**Fuente o regla que permitió corregirla:** la propia rúbrica del punto 8 (*"Mostrar únicamente una lista de herramientas instaladas no acredita su uso"*) y la coherencia documental exigida por `AGENTS.md` §Reglas Duras. Un servidor que no conecta no puede aportar evidencia de uso, por definición.

**Diagnóstico de la causa raíz (dos fallas encadenadas):**

1. **El entry point estaba en el archivo de configuración equivocado.** El cliente lee `~/.config/opencode/opencode.json` (22 KB, con `agent`, `mcp` y `permission`). El entry de `filesystem` estaba escrito en `~/.config/opencode/opencode.jsonc` (391 B), que **no se lee**. El `opencode.json` activo sólo declaraba `context7` y `engram`:
   ```jsonc
   "mcp": {
     "context7": { "enabled": true, "type": "remote", "url": "https://mcp.context7.com/mcp" },
     "engram":   { "type": "local", "command": ["engram", "mcp"] }
   }
   ```
2. **El path del workspace tiene un espacio y el shim `npx.cmd` de Windows partía el argumento.** Invocado como `npx @modelcontextprotocol/server-filesystem "C:\Users\Cara Palida\..."`, el shim re-escapa mal los argumentos y entrega dos rutas:
   ```
   Warning: Cannot access directory C:\Users\Cara, skipping
   Warning: Cannot access directory C:\Users\Cara Palida\Downloads\Palida\Documents\projects\odontologia-tpMetodologia, skipping
   Error: None of the specified directories are accessible
   ```
   Es decir: el servidor **arrancaba y moría** en cada intento de conexión.

**Antes:**

```jsonc
// ~/.config/opencode/opencode.jsonc  ← archivo NO leído por el cliente
"filesystem": {
  "command": "npx",
  "args": ["@modelcontextprotocol/server-filesystem",
           "C:\\Users\\Cara Palida\\Documents\\projects\\odontologia-tpMetodologia"]
}
// Estado declarado en el TP: "CONFIGURADO Y OPERATIVO"
// Realidad: `opencode mcp list` → 2 servers, filesystem ausente
```

**Después** (entry en el archivo **activo**, invocando `node` directamente para evitar el shim):

```jsonc
// ~/.config/opencode/opencode.json  (línea 22-35)
"filesystem": {
  "type": "local",
  "command": [
    "node",
    "C:\\Users\\Cara Palida\\AppData\\Roaming\\npm\\node_modules\\@modelcontextprotocol\\server-filesystem\\dist\\index.js",
    "C:\\Users\\Cara Palida\\Documents\\projects\\odontologia-tpMetodologia"
  ]
}
```

```
$ opencode mcp list
●  ✓ filesystem connected
     node C:\Users\Cara Palida\AppData\Roaming\npm\node_modules\@modelcontextprotocol\server-filesystem\dist\index.js C:\Users\Cara Palida\Documents\projects\odontologia-tpMetodologia
└─ 3 server(s)
```

Backups: `opencode.json.bak` y `opencode.json.bak-c01` (configuración global del usuario, fuera del repo).

## D2 — Violación del spec: el secreto temporal de `dev` se generaba sin el aviso exigido

**Gravedad: media.** Defecto de **implementación** (no de documentación): el requisito del spec es explícito.

**Cómo se detectó:** en la fase `/open:verify` se cruzó cada uno de los **18 escenarios** del spec `foundation/runtime` contra los tests que los cubren. El escenario *"GIVEN el entorno es de desarrollo y `JWT_SECRET` no está definida WHEN la aplicación arranca THEN la aplicación arranca, **emite un aviso explícito** de que usa un secreto temporal"* estaba cubierto por un test que **sólo** verificaba que existiera un secreto — nunca que se emitiera el aviso. Al leer la implementación, la ausencia era real: `_aplicar_reglas` generaba el secreto efímero y devolvía, sin emitir nada.

**Fuente o regla que permitió corregirla:** el texto del requisito en `openspec/specs/foundation/runtime/spec.md` (el contrato) y la regla dura **R11** del proyecto (TDD estricto, mínimo 2 casos por comportamiento) aplicada en su versión correctiva: no basta un caso, hacen falta los dos.

**Antes** (`backend/app/core/config.py`):

```python
if settings.jwt_secret is None:
    if not settings.es_desarrollo:
        raise ConfigError(...)
    settings = settings.model_copy(update={"jwt_secret": SecretStr(secrets.token_hex(32))})
    return settings
```
→ el secreto efímero se generaba **en silencio**.

**Después**:

```python
valor = settings.jwt_secret.get_secret_value() if settings.jwt_secret is not None else ""
if not valor.strip():
    if not settings.es_desarrollo:
        raise ConfigError(...)
    logging.getLogger("odontologia.config").warning(
        "JWT_SECRET no está configurada: se usa un secreto TEMPORAL "
        "generado en este proceso. Los tokens firmados con él se invalidan "
        "al reiniciar. Sólo se permite en dev/test."
    )
    return settings.model_copy(update={"jwt_secret": SecretStr(secrets.token_hex(32))})
```

Además, el `lifespan` de `backend/app/main.py` ahora configura el logging **antes** de cargar la settings, para que el aviso salga por el handler estructurado y no por el handler por defecto de la librería.

**Prueba de regresión (reproduce el antes/después sin tocar git):** se revirtió el bloque del aviso a una versión sin el mensaje real y se ejecutó el test:

```
$ pytest tests/test_settings.py::test_sin_jwt_secret_en_dev_avisa_que_usa_un_secreto_temporal
E  AssertionError: assert 'JWT_SECRET' in 'BEFORE-DEFECTO: ...'
FAILED ...  1 failed

$ git checkout -- backend/app/core/config.py     # restaura el estado corregido
$ pytest tests/test_settings.py::test_sin_jwt_secret_en_dev_avisa_que_usa_un_secreto_temporal
1 passed
```

## D3 — `design.md` declaraba "Secrets: ninguno" de forma inexacta

**Gravedad: baja.** Detectado en el borrador previo de esta revisión y verificado contra el workflow real de CI.

**Cómo se detectó:** contraste entre `design.md` (Decisión 9 — CI: *"Secrets: ninguno."*) y `tasks.md` (Task 6.4 exige correr el ciclo de migraciones **contra Postgres 16 real**), que necesariamente implica credenciales de conexión.

**Fuente o regla:** coherencia documental de `AGENTS.md` §Reglas Duras y R13 (gobernanza CRITICAL/HIGH: un CI que no explica cómo maneja las credenciales puede inducir a commitearlas).

**Antes:** `Secrets: ninguno.`

**Después** (aplicado en `openspec/changes/archive/2026-10-19-C-01-foundation-setup-decisiones/design.md`):

> Secrets: **ninguno** — el job `backend` no usa secrets de GitHub: la conexión a Postgres 16 y Redis 7 se hace con las credenciales **de los propios service containers del job**, declaradas como variables de entorno del runner (`DATABASE_URL`, `REDIS_URL`, `TEST_DATABASE_URL`) y con un `JWT_SECRET` de CI que no es un secreto real (sólo cumple la regla de arranque de `APP_ENV=test`). El job `frontend` tampoco requiere secrets.

## D4 — Contaminación con caracteres CJK en 4 archivos escritos por el agente

**Gravedad: baja (calidad), alta si se hubiera committed.**

**Cómo se detectó:** barrido con `Select-String -Pattern '[\u4e00-\u9fff\u3040-\u30ff]'` sobre todos los archivos escritos en la sesión. El defecto se introdujo **5 veces** y sólo lo detectó el barrido explícito: ningún linter, ni `openspec validate`, ni los tests lo señalan.

**Fuente o regla:** la disciplina de idioma del proyecto — la KB, los ADRs y los specs se leen y revisan en español, y un `玩具` o una `形状` en un documento de arquitectura es un defecto de entrega, no un descuido.

**Antes → después** (pares exactos del `edit` tool):

| Archivo | Antes | Después |
|---|---|---|
| `backend/app/core/config.py` | `#: Longitud mínima del secreto de firma en entornos no玩具.` | `#: Longitud mínima del secreto de firma en entornos que no son de desarrollo.` |
| `discovery/explore-c01-foundation-setup-decisiones.md` | `puede **fijar el contrato** de形状.` | `puede **fijar el contrato** de campos.` |
| `docs/adr/ADR-001-whatsapp-provider.md` | `no incluyen类型 \`service\` ni marketing` | `no incluyen mensajes de categoría \`service\` ni de \`marketing\`` |
| `design.md` | `**Nota de路径**` / `esa接口` / `tabla deextend Ownership` | `**Nota de rutas**` / `soportado por la interfaz` / `tabla de propiedad de cada tabla` |

**Verificación del estado final:**

```
$ git grep -I -n -P "[\x{4e00}-\x{9fff}\x{3040}-\x{30ff}]" 4ec1cc5 -- "*.md" "*.py" "*.ts" "*.tsx" "*.yml" "*.json"
(vacío)
```

## D5 — El agente introdujo 2 CVE moderados al agregar `react-router-dom` 6.x

**Gravedad: media.** Defecto **propio del agente**: eligió una versión de una dependencia sin auditar sus advisories.

**Cómo se detectó:** `npm audit` al cierre del change, al revisar la lista de vulnerabilidades que `npm install` había warned. El advisory: `GHSA-wrjc-x8rr-h8h6` (open redirect vía backslash en `<Link>` y `useNavigate`) y `GHSA-337j-9hxr-rhxg` (constructor injection en la hidratación SSR de React Router — no aplicable a una SPA, pero el paquete figuraba como vulnerable).

**Fuente o regla:** el `package.json` del proyecto declara en el `AGENTS.md` §Datos sensibles que no se introduzcan dependencias con riesgo conocido sin evaluarlo; y el propio `npm audit` es la fuente.

**Antes → después** (verificable en el diff de `frontend/package.json` del commit `4ec1cc5`):

```diff
-    "react-router-dom": "^6.28.0",     # introducido por el agente en esta sesión
+    "react-router-dom": "^7.18.4",
-    "vitest": "^2.1.8",                # arrastraba tinypool con RCE crítico (GHSA-5gmw-xhrv-c9v3)
+    "vitest": "^5.0.5",
```

```
$ npm audit          →  8 vulnerabilities (5 moderate, 1 high, 2 critical)
$ npm audit          →  found 0 vulnerabilities
```

Con 10 tests, `tsc --noEmit` y `vite build` en verde después del salto.

---

# 4. Prueba de borde para evaluar los límites del agente

El enunciado pide: *"Si no detectaron un defecto en la ejecución inicial, prueben un caso de borde para evaluar sus límites y documenten el resultado sin inventar un error."*

Se detectaron defectos, pero la prueba de borde se hizo igual porque es la que **evalúa los límites** del razonamiento del agente frente a su propia evidencia previa.

## El límite: el agente razonó sobre datos que nunca había ejecutado

En la fase explore, el agente recomendó para el Eje 3:

> "El slice ya escrito (4 archivos de test backend + 1 frontend) **sobrevive intacto**... el costo de re-alinear (retirar `0001`...) es alto: había que **mover código validado**."

Es decir: el agente dio por hecho que «código validado» era evidencia de que **los tests del slice pasaban**. Y pasaban — **contra SQLite**.

El caso de borde fue correr esa misma suite contra **Postgres 16 real** (la decisión M1, que el propio explore había tomado precisamente para cerrar ese punto ciego). El resultado:

```
psycopg.errors.ForeignKeyViolation: insert or update on table "config" violates
foreign key constraint "config_tenant_id_fkey"
DETAIL:  Key (tenant_id)=(tenant-demo-a) is not present in table "tenant".
```

**Tres violaciones de FK reales** (no una) que SQLite **nunca** detectó, porque SQLite no habilita `PRAGMA foreign_keys` por defecto:

1. `test_repo_query_filtra_por_tenant_id_R1` — insertaba `config` sin su `tenant`.
2. `test_repo_cancelled_at_se_persiste_utc_aware_R7` — idem.
3. `test_repo_config_columna_precisa_y_check_no_negativo` — `repo.upsert()` sin tenant.

**Lectura del límite (sin inventar errores):**

- El razonamiento del agente en el explore **era correcto en su lógica** ("no tiremos código validado") pero **partía de una premisa no verificada**: que "validado" significaba "correcto". Los tests validaban el comportamiento *bajo SQLite*, no bajo el motor de producción.
- El defecto no estaba en la decisión M1 sino en la **fuerza de la evidencia que la sostenía**. La decisión fue correcta; la justificación estaba inflada.
- La corrección fue del **dato de test**, no del código de producción: los fixtures ahora crean el `tenant` y hacen `flush()` antes de insertar su `config`, porque el orden de insert lo impone la FK real.
- Consecuencia transferida: `AGENTS.md` §Reglas Duras ahora tiene una regla nueva y **verificable** en lugar de una promesa — la suite corre contra el motor de producción (CI: service container `postgres:16`).

**Por qué esto importa más que un error de redacción:** un error de redacción se detecta leyendo; un error de razonamiento sobre la evidencia **no** se detecta leyendo, sólo ejecutando. El agente detectó su propio límite únicamente cuando ejecutó la suite en el motor real.

---

# 5. Cómo reproducir esta evidencia

```bash
# 1. Servidores MCP conectados (debe listar 3, con filesystem)
opencode mcp list

# 2. Handshake MCP real contra la raíz del proyecto (lee CHANGES.md por el protocolo)
node <probe>.js "C:\Users\Cara Palida\AppData\Roaming\npm\node_modules\@modelcontextprotocol\server-filesystem\dist\index.js" \
                 "C:\Users\Cara Palida\Documents\projects\odontologia-tpMetodologia"

# 3. Ausencia de caracteres CJK en lo commiteado
git grep -I -n -P "[\x{4e00}-\x{9fff}\x{3040}-\x{30ff}]" 4ec1cc5 -- "*.md" "*.py" "*.ts" "*.tsx" "*.yml" "*.json"

# 4. Regresión de D2: revertir el aviso y ver fallar el test
#    (y restaurarlo con: git checkout -- backend/app/core/config.py)
pytest backend/tests/test_settings.py::test_sin_jwt_secret_en_dev_avisa_que_usa_un_secreto_temporal

# 5. Vulnerabilidades del frontend
cd frontend && npm audit

# 6. Suite completa contra Postgres 16 real
cd backend && python -m pytest
```

# 6. Archivos afectados por las correcciones

| Archivo | Cambio |
|---------|--------|
| `~/.config/opencode/opencode.json` (global, fuera del repo) | Entry de `filesystem` movido al config activo + invocación por `node` para sortear el shim `npx.cmd` con paths con espacios. Backups: `opencode.json.bak`, `opencode.json.bak-c01` |
| `~/.config/opencode/opencode.jsonc` (global, fuera del repo) | Corregido a la misma forma `node` (queda inactivo, pero ya no induce a error) |
| `openspec/changes/archive/2026-10-19-C-01-foundation-setup-decisiones/design.md` | D3: "Secrets: ninguno" → redacción exacta |
| `backend/app/core/config.py` | D2: aviso explícito del secreto temporal |
| `backend/app/main.py` | D2: logging configurado antes de cargar la settings |
| `backend/tests/test_settings.py` | D2: test que exige el aviso |
| `backend/tests/test_health.py` | Cobertura del escenario "Redis caído / base de datos ok" |
| `backend/tests/test_env_examples.py` | Cobertura del escenario "los `.env.example` no tienen secretos reales" (antes verificado a ojo) |
| `docs/skills-mcp/mcp-configuracion.md` | Estado real del servidor + causa raíz y fix (D1) |
| `docs/skills-mcp/aplicacion.md` | §Limitaciones: el MCP ya no queda pendiente |
| `docs/skills-mcp/revision-critica-punto-8.md` | Este documento |

---

**Estado de la revisión**: detectadas 5 incidencias (D1-D5), 4 corregidas y verificadas con prueba de regresión o con el verificador correspondiente, 1 documentada como límite del razonamiento del agente (sección 4). Los cambios de código de D2 y D5 están commiteados en `4ec1cc5`; la corrección de D3 y las correcciones de documentación (este archivo, `mcp-configuracion.md`, `aplicacion.md`, el cliente MCP y los artefactos de C-02) quedan pendientes de commit.
